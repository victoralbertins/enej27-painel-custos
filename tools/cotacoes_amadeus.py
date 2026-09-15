#!/usr/bin/env python3
"""
Busca cotações REAIS na API da Amadeus e grava em data/observacoes.json.

    export AMADEUS_CLIENT_ID=...
    export AMADEUS_CLIENT_SECRET=...
    python tools/cotacoes_amadeus.py

Roda sozinho no GitHub Actions (.github/workflows/atualizar-cotacoes.yml), com
as credenciais em secrets do repositório. A chave NUNCA vai para o painel: a
busca acontece no CI, e o navegador só lê o JSON já pronto.

-------------------------------------------------------------------------------
POR QUE AMADEUS

É a única API de cotação aérea com tier gratuito que não exige contrato de
parceria (Skyscanner e Google Flights não têm API pública). Cadastro em
https://developers.amadeus.com -> Self-Service -> crie um app -> copie
API Key e API Secret.

Ambiente de teste (padrão, gratuito): dados reais porém com cobertura parcial
de rotas. Para cobertura total troque AMADEUS_HOST para o host de produção.
-------------------------------------------------------------------------------

O QUE ACONTECE QUANDO A BUSCA NÃO ACHA NADA

Voo para agosto de 2027 está no limite do horizonte de publicação das
companhias (~11 meses), então algumas rotas voltam vazias. Nesse caso a rota
simplesmente não entra em observacoes.json, e gerar_cotacoes.py mantém a
estimativa calibrada para ela — marcada como "estimado" no painel. Nada quebra.
"""

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "data" / "observacoes.json"

# Ambiente de teste. Produção: https://api.amadeus.com
AMADEUS_HOST = os.environ.get("AMADEUS_HOST", "https://test.api.amadeus.com")

DESTINO = "REC"
IDA = "2027-08-25"
VOLTA = "2027-08-30"

# Origens a consultar. Códigos metropolitanos onde existem (SAO, RIO), porque
# cobrem todos os aeroportos da cidade e trazem a tarifa mais baixa.
ORIGENS = {
    "AC": "RBR", "AP": "MCP", "AM": "MAO", "PA": "BEL", "RO": "PVH",
    "RR": "BVB", "TO": "PMW",
    "AL": "MCZ", "BA": "SSA", "CE": "FOR", "MA": "SLZ", "PB": "JPA",
    "PI": "THE", "RN": "NAT", "SE": "AJU",
    "DF": "BSB", "GO": "GYN", "MT": "CGB", "MS": "CGR",
    "ES": "VIX", "MG": "CNF", "RJ": "RIO", "SP": "SAO",
    "PR": "CWB", "SC": "FLN", "RS": "POA",
}

# Hotéis em Boa Viagem por categoria, para revisar a diária de cada cenário.
HOTEIS = {
    "econ": {"ratings": None, "label": "hostel / econômico"},
    "inter": {"ratings": "3", "label": "3 estrelas"},
    "conforto": {"ratings": "4", "label": "4 estrelas"},
}
CIDADE_HOTEL = "REC"

PAUSA = 0.4  # segundos entre chamadas, para respeitar o rate limit


def _get(url, headers, tentativas=3):
    """GET com retry em erro transitório. Devolve dict ou None."""
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and n < tentativas - 1:
                time.sleep(2 ** n)
                continue
            corpo = e.read().decode("utf-8", "replace")[:200]
            print(f"    HTTP {e.code}: {corpo}")
            return None
        except Exception as e:
            if n < tentativas - 1:
                time.sleep(2 ** n)
                continue
            print(f"    falhou: {e}")
            return None
    return None


def autenticar():
    """OAuth2 client_credentials. Devolve o access token."""
    cid = os.environ.get("AMADEUS_CLIENT_ID")
    secret = os.environ.get("AMADEUS_CLIENT_SECRET")
    if not cid or not secret:
        print("AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET não definidos.")
        print("Cadastre-se em https://developers.amadeus.com e exporte as duas variáveis.")
        return None

    dados = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": cid,
        "client_secret": secret,
    }).encode()

    req = urllib.request.Request(
        f"{AMADEUS_HOST}/v1/security/oauth2/token",
        data=dados,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))["access_token"]
    except urllib.error.HTTPError as e:
        print(f"autenticação falhou: HTTP {e.code} {e.read().decode('utf-8','replace')[:200]}")
        return None


def cotar_voo(token, origem):
    """Menor preço ida e volta origem -> REC nas datas do evento."""
    params = urllib.parse.urlencode({
        "originLocationCode": origem,
        "destinationLocationCode": DESTINO,
        "departureDate": IDA,
        "returnDate": VOLTA,
        "adults": 1,
        "currencyCode": "BRL",
        "max": 20,
        "nonStop": "false",
    })
    dados = _get(f"{AMADEUS_HOST}/v2/shopping/flight-offers?{params}",
                 {"Authorization": f"Bearer {token}"})
    if not dados or not dados.get("data"):
        return None

    precos = []
    for oferta in dados["data"]:
        try:
            precos.append(float(oferta["price"]["grandTotal"]))
        except (KeyError, TypeError, ValueError):
            continue
    return round(min(precos)) if precos else None


def cotar_hotel(token, ratings):
    """Mediana da diária em Recife para uma categoria de hotel."""
    p = {"cityCode": CIDADE_HOTEL}
    if ratings:
        p["ratings"] = ratings
    lista = _get(f"{AMADEUS_HOST}/v1/reference-data/locations/hotels/by-city?"
                 + urllib.parse.urlencode(p),
                 {"Authorization": f"Bearer {token}"})
    if not lista or not lista.get("data"):
        return None

    ids = [h["hotelId"] for h in lista["data"][:20] if h.get("hotelId")]
    if not ids:
        return None

    params = urllib.parse.urlencode({
        "hotelIds": ",".join(ids),
        "checkInDate": IDA,
        "checkOutDate": VOLTA,
        "adults": 1,
        "currency": "BRL",
    })
    ofertas = _get(f"{AMADEUS_HOST}/v3/shopping/hotel-offers?{params}",
                   {"Authorization": f"Bearer {token}"})
    if not ofertas or not ofertas.get("data"):
        return None

    noites = (date.fromisoformat(VOLTA) - date.fromisoformat(IDA)).days
    diarias = []
    for h in ofertas["data"]:
        for o in h.get("offers", []):
            try:
                diarias.append(float(o["price"]["total"]) / noites)
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
    if not diarias:
        return None

    diarias.sort()
    return round(diarias[len(diarias) // 2])


def main():
    token = autenticar()
    if not token:
        print("\nSem credenciais: observacoes.json não foi alterado.")
        print("gerar_cotacoes.py segue com as estimativas calibradas.")
        return 1

    agora = datetime.now(timezone.utc).date().isoformat()
    voos, hoteis = {}, {}

    print(f"consultando {len(ORIGENS)} origens -> {DESTINO} ({IDA} / {VOLTA})")
    for uf, iata in sorted(ORIGENS.items()):
        preco = cotar_voo(token, iata)
        if preco:
            voos[uf] = {"preco": preco, "fonte": "Amadeus",
                        "origem_iata": iata, "conferido_em": agora}
            print(f"  {uf} {iata}: R$ {preco}")
        else:
            print(f"  {uf} {iata}: sem oferta (mantém estimativa)")
        time.sleep(PAUSA)

    print("consultando diárias em Recife")
    for chave, cfg in HOTEIS.items():
        diaria = cotar_hotel(token, cfg["ratings"])
        if diaria:
            hoteis[chave] = {"diaria": diaria, "fonte": "Amadeus",
                             "categoria": cfg["label"], "conferido_em": agora}
            print(f"  {chave} ({cfg['label']}): R$ {diaria}/noite")
        else:
            print(f"  {chave}: sem oferta (mantém estimativa)")
        time.sleep(PAUSA)

    if not voos and not hoteis:
        print("\nNenhuma cotação obtida: observacoes.json não foi alterado.")
        return 1

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        json.dump({
            "atualizado_em": agora,
            "fonte": "Amadeus Self-Service API",
            "ambiente": "teste" if "test." in AMADEUS_HOST else "producao",
            "janela": {"ida": IDA, "volta": VOLTA, "destino": DESTINO},
            "voos": voos,
            "hoteis": hoteis,
        }, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\n{SAIDA.name}: {len(voos)} voos, {len(hoteis)} categorias de hotel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
