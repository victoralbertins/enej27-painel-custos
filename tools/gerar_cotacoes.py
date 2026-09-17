#!/usr/bin/env python3
"""
Gera data/cotacoes-enej27.json e injeta o mesmo payload no index.html como
fallback, para as duas fontes nunca divergirem.

    python tools/gerar_cotacoes.py

-------------------------------------------------------------------------------
DE ONDE VÊM OS PREÇOS

Não há modelo estimado nas passagens. COTACOES traz, para cada uma das 26
origens, a estatística real da rota publicada pelo Kayak (faixa típica, média e
menor preço dos últimos 12 meses), levantada em 15/09/2026.

Precedência, da melhor fonte para a pior:

  1. cotação DATADA para as datas do evento — vem de OBSERVACOES_MANUAIS ou da
     busca automática da Amadeus (data/observacoes.json);
  2. estatística de 12 meses da rota — o padrão.

PARA PLUGAR O BIGQUERY: troque COTACOES por uma query e mantenha o shape de
saída. O painel não precisa saber de onde veio.
-------------------------------------------------------------------------------
"""

import json
import pathlib
import re
from datetime import date

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA_JSON = RAIZ / "data" / "cotacoes-enej27.json"
SAIDA_HTML = RAIZ / "index.html"

DESTINO = "REC"

# Espalhamento da faixa em torno da cotação central. Tarifa aérea é assimétrica:
# cai pouco abaixo do piso promocional e sobe muito acima dele.
FAIXA_MIN, FAIXA_MAX = 0.80, 1.30

# ---------------------------------------------------------------------------
# COTAÇÕES REAIS CONFERIDAS NA FONTE
# preco = ida e volta, em BRL, para as datas do evento.
# ---------------------------------------------------------------------------
OBSERVACOES_MANUAIS = {
    "SP": {"preco": 1154, "fonte": "Kayak", "conferido_em": "2026-09-14"},
    # Adicione outras conforme conferir na mão, ex.:
    # "BA": {"preco": 980, "fonte": "Google Flights", "conferido_em": "2026-09-20"},
}

# Cotações buscadas automaticamente por tools/cotacoes_amadeus.py.
# O arquivo é reescrito pelo workflow atualizar-cotacoes.yml; se não existir,
# valem só as observações manuais acima.
ARQUIVO_OBSERVACOES = RAIZ_OBS = pathlib.Path(__file__).resolve().parent.parent / "data" / "observacoes.json"


def carregar_observacoes():
    """Funde as cotações automáticas com as manuais.

    A busca automática vence: ela roda semanalmente e reflete o mercado de
    hoje, enquanto a manual é um ponto fixo no tempo."""
    voos = dict(OBSERVACOES_MANUAIS)
    hoteis = {}

    if ARQUIVO_OBSERVACOES.exists():
        try:
            dados = json.loads(ARQUIVO_OBSERVACOES.read_text(encoding="utf-8"))
            voos.update(dados.get("voos", {}))
            hoteis = dados.get("hoteis", {})
        except (json.JSONDecodeError, OSError) as e:
            print(f"  aviso: observacoes.json ilegível ({e}); usando só as manuais")

    return voos, hoteis

# ---------------------------------------------------------------------------
# FONTES
# Cada número que tem lastro verificável está aqui, com a URL e a data da
# consulta. O que NÃO aparece nesta lista é estimativa — e o painel marca
# esses casos em âmbar. Ver FONTES.md para o inventário completo.
# ---------------------------------------------------------------------------
FONTES = [
    {"item": "Tarifa de ônibus urbano (Anel A, R$ 4,50)",
     "fonte": "Grande Recife Consórcio de Transporte / Folha PE",
     "url": "https://www.folhape.com.br/noticias/aumento-da-passagem-de-onibus-no-grande-recife-e-homologado-e-anel-a/463122/",
     "consultado_em": "2026-09-15"},
    {"item": "Uber aeroporto REC <-> Boa Viagem (R$ 23, 5,71 km)",
     "fonte": "Uber (página oficial de estimativa da rota)",
     "url": "https://www.uber.com/global/en/r/routes/recife-pe-br-to-rec/",
     "consultado_em": "2026-09-15"},
    {"item": "Prato feito (R$ 30-31,90)",
     "fonte": "Abrasel, via Mercado&Consumo",
     "url": "https://mercadoeconsumo.com.br/07/05/2026/foodservice/alimentacao-fora-de-casa-fica-mais-cara-e-prato-feito-atinge-media-de-r-3027/",
     "consultado_em": "2026-09-15"},
    {"item": "Diária média em Recife (R$ 280 o quarto duplo)",
     "fonte": "Dicas de Viagem / Viaje na Viagem (levantamento de mercado)",
     "url": "https://www.dicasdeviagem.com/hoteis-em-recife/",
     "consultado_em": "2026-09-15"},
    {"item": "Tarifa aérea doméstica média (R$ 632,53 por trecho, mai/2026)",
     "fonte": "ANAC — dados tarifários mensais",
     "url": "https://www.gov.br/anac/pt-br/noticias/2026/anac-publica-dados-tarifarios-do-mes-de-maio-de-2026",
     "consultado_em": "2026-09-15"},
    {"item": "Passagem rodoviária João Pessoa / Natal / Maceió",
     "fonte": "ClickBus e CheckMyBus",
     "url": "https://www.clickbus.com.br/onibus/joao-pessoa-pb",
     "consultado_em": "2026-09-15"},
    {"item": "Cotação real SP -> REC ida e volta (R$ 1.154)",
     "fonte": "Kayak, conferida pelo usuário",
     "url": "https://www.kayak.com.br/flights/SAO-REC/2027-08-25/2027-08-30",
     "consultado_em": "2026-09-14"},
]

# ---------------------------------------------------------------------------
# COTAÇÕES POR ROTA — DADOS REAIS
# Levantados nas páginas de rota do Kayak em 15/09/2026, uma por origem.
# Cada página publica estatística observada dos últimos 12 meses:
#
#   barato  = menor ida e volta encontrada recentemente
#   tip_min / tip_max = faixa de tarifas típicas
#   media   = média de ida e volta dos últimos 12 meses  <- usada como centro
#
# Fonte de cada linha: https://www.kayak.com.br/flight-routes/<Cidade-CODE>/Recife-REC
# O inventário com a URL exata de cada rota está em FONTES.csv.
#
# NÃO são cotações para as datas exatas do evento — são a estatística da rota.
# A busca da Amadeus (tools/cotacoes_amadeus.py) sobrepõe estes valores com
# preço datado quando a rota estiver disponível.
# ---------------------------------------------------------------------------
COTACOES = [
    # (uf, capital,          iata,  regiao,        search, barato, tip_min, tip_max, media, nota)
    ("AC", "Rio Branco",     "RBR", "Norte",        None,  1475, 1919, 2744, 2488, None),
    ("AP", "Macapá",         "MCP", "Norte",        None,  1207, 1171, 2233, 1763, None),
    ("AM", "Manaus",         "MAO", "Norte",        None,  1147, 1313, 2014, 1577, None),
    ("PA", "Belém",          "BEL", "Norte",        None,   789,  871, 1410, 1131, None),
    ("RO", "Porto Velho",    "PVH", "Norte",        None,  1578, 2030, 2953, 2428, None),
    ("RR", "Boa Vista",      "BVB", "Norte",        None,  1836, 1969, 2783, 2289, None),
    ("TO", "Palmas",         "PMW", "Norte",        None,   998, 1175, 1748, 1449, None),

    ("AL", "Maceió",         "MCZ", "Nordeste",     None,   388,  509,  898,  654,
     "Maceió fica a 260 km: ônibus leva ~4h a partir de R$ 100 por trecho. Compare com o voo."),
    ("BA", "Salvador",       "SSA", "Nordeste",     None,   440,  543,  910,  685, None),
    ("CE", "Fortaleza",      "FOR", "Nordeste",     None,   464,  672, 1107,  843, None),
    ("MA", "São Luís",       "SLZ", "Nordeste",     None,   835,  805, 1287, 1011, None),
    ("PB", "João Pessoa",    "JPA", "Nordeste",     None,   824,  738, 1582, 1162,
     "Atenção: voar de João Pessoa custa em média MAIS que de São Paulo (R$ 1.162 x R$ 1.085). "
     "São 120 km — o ônibus leva ~2h a partir de R$ 27 por trecho."),
    ("PE", "Recife",         "REC", "Nordeste",     None,     0,    0,    0,    0, None),  # anfitriã
    ("PI", "Teresina",       "THE", "Nordeste",     None,   797,  683, 1312,  917, None),
    ("RN", "Natal",          "NAT", "Nordeste",     None,   455,  435,  895,  656,
     "Natal fica a 300 km: ônibus leva ~4h30 a partir de R$ 74 por trecho."),
    ("SE", "Aracaju",        "AJU", "Nordeste",     None,   594,  836, 1333,  996, None),

    ("DF", "Brasília",       "BSB", "Centro-Oeste", None,   642,  825, 1403, 1067, None),
    ("GO", "Goiânia",        "GYN", "Centro-Oeste", None,   841,  996, 1623, 1254, None),
    ("MT", "Cuiabá",         "CGB", "Centro-Oeste", None,   968, 1110, 1726, 1380, None),
    ("MS", "Campo Grande",   "CGR", "Centro-Oeste", None,  1070, 1075, 1717, 1348, None),

    ("ES", "Vitória",        "VIX", "Sudeste",      None,   730,  858, 1415, 1072, None),
    ("MG", "Belo Horizonte", "CNF", "Sudeste",      "BHZ",  766,  949, 1538, 1193, None),
    ("RJ", "Rio de Janeiro", "GIG", "Sudeste",      "RIO",  922,  896, 1529, 1143, None),
    ("SP", "São Paulo",      "GRU", "Sudeste",      "SAO",  758,  873, 1513, 1085, None),

    ("PR", "Curitiba",       "CWB", "Sul",          None,  1009,  927, 1704, 1273, None),
    ("SC", "Florianópolis",  "FLN", "Sul",          None,  1295, 1134, 1727, 1368, None),
    ("RS", "Porto Alegre",   "POA", "Sul",          None,   937, 1208, 1894, 1488, None),
]

KAYAK_SLUGS = {
    "AC": "Rio-Branco-RBR", "AP": "Macapa-MCP", "AM": "Manaus-MAO", "PA": "Belem-BEL",
    "RO": "Porto-Velho-PVH", "RR": "Boa-Vista-BVB", "TO": "Palmas-PMW",
    "AL": "Maceio-MCZ", "BA": "Salvador-SSA", "CE": "Fortaleza-FOR", "MA": "Sao-Luis-SLZ",
    "PB": "Joao-Pessoa-JPA", "PI": "Teresina-THE", "RN": "Natal-NAT", "SE": "Aracaju-AJU",
    "DF": "Brasilia-BSB", "GO": "Goiania-GYN", "MT": "Cuiaba-CGB", "MS": "Campo-Grande-CGR",
    "ES": "Vitoria-VIX", "MG": "Belo-Horizonte-BHZ", "RJ": "Rio-de-Janeiro-RIO",
    "SP": "Sao-Paulo-SAO", "PR": "Curitiba-CWB", "SC": "Florianopolis-FLN", "RS": "Porto-Alegre-POA",
}
LEVANTADO_EM = "2026-09-15"


def url_kayak_rota(uf):
    slug = KAYAK_SLUGS.get(uf)
    return f"https://www.kayak.com.br/flight-routes/{slug}/Recife-REC" if slug else ""


# ---------------------------------------------------------------------------
# AIRBNB — anúncios reais em Boa Viagem, levantados no cozycozy em 17/09/2026.
#
# A lógica é diferente da do hotel: o apartamento tem um preço por noite
# INDEPENDENTE de quantas pessoas dormem nele, até a capacidade. Então o custo
# por pessoa cai conforme a delegação cresce — e é o painel que faz essa conta,
# usando o tamanho do grupo:
#
#     por pessoa = diaria / min(tamanho do grupo, capacidade)
#
# Por isso guardamos diaria + capacidade, e não um valor por pessoa.
# ---------------------------------------------------------------------------
AIRBNB = {
    "econ": {
        "night": 200, "capacity": 6,
        "listing": "Golden Shopping Home Service Apt 608 (27 m², até 6 pessoas)",
        "what": "apartamento simples dividido entre a delegação",
    },
    "inter": {
        "night": 302, "capacity": 4,
        "listing": "Flat Perto do Mar de Boa Viagem (1 quarto, até 4 pessoas)",
        "what": "flat perto da praia dividido entre a delegação",
    },
    "conforto": {
        "night": 378, "capacity": 2,
        "listing": "Comfortable Studio in Boa Viagem (2 hóspedes)",
        "what": "studio para dois, mais espaço por pessoa",
    },
}
AIRBNB_FONTE = "cozycozy (agregador de aluguel por temporada)"
AIRBNB_URL = "https://www.cozycozy.com/br/aluguel-temporada-boa-viagem"
AIRBNB_EM = "2026-09-17"

# ---------------------------------------------------------------------------
# CENÁRIOS DE GASTO — valores unitários; o painel fecha os totais.
#
# hospNight revisado para Boa Viagem em agosto. ATENÇÃO: diferente das
# passagens, aqui ainda NÃO há cotação real conferida — são estimativas de
# mercado. Confira no Booking (o link está em cada cenário no painel) e ajuste
# hospNight abaixo; o mesmo mecanismo de observação vale.
#
# transit:
#   busRides/busFare          embarques de ônibus ou metrô por dia
#   uberRides/uberFare        corridas de Uber/99 por dia (entram no fator da sede)
#   airportRides/airportFare  traslado do aeroporto, ida e volta — cobrado uma
#                             vez na viagem e NÃO multiplicado pelo fator da
#                             sede, porque REC -> Boa Viagem é o mesmo trajeto
#                             independente de onde o evento acontecer.
# ---------------------------------------------------------------------------
CENARIOS = [
    {
        "key": "econ",
        "name": "Econômico",
        "desc": "Hostel compartilhado em Boa Viagem, prato feito e ônibus/metrô.",
        "hospNight": 85,
        "hospWhat": "cama em quarto compartilhado",
        "hotelFilter": "ht_id%3D203",  # Booking: tipo hostel
        "meals": {"cafe": 12, "almoco": 30, "jantar": 24},
        "mealsWhat": "padaria, prato feito e lanche à noite",
        "transit": {
            "busRides": 4, "busFare": 4.50,
            "uberRides": 1, "uberFare": 7.00,
            "airportRides": 2, "airportFare": 23.00,
        },
        "transitWhat": "4 embarques de ônibus/metrô + 1 Uber noturno dividido entre 4",
    },
    {
        "key": "inter",
        "name": "Intermediário",
        "desc": "Hotel 3 estrelas em quarto duplo, self-service e mix de ônibus e Uber.",
        "hospNight": 140,
        "hospWhat": "quarto duplo (~R$ 280 a diária), valor por pessoa",
        "hotelFilter": "class%3D3",
        "meals": {"cafe": 18, "almoco": 45, "jantar": 36},
        "mealsWhat": "café do hotel, self-service por quilo e jantar simples",
        "transit": {
            "busRides": 2, "busFare": 4.50,
            "uberRides": 1, "uberFare": 24.00,
            "airportRides": 2, "airportFare": 23.00,
        },
        "transitWhat": "2 embarques de ônibus + 1 corrida de Uber por dia",
    },
    {
        "key": "conforto",
        "name": "Conforto",
        "desc": "Hotel 4 estrelas na orla, restaurantes à la carte e Uber em todos os trajetos.",
        "hospNight": 200,
        "hospWhat": "4 estrelas na orla (~R$ 400 a diária), valor por pessoa",
        "hotelFilter": "class%3D4",
        "meals": {"cafe": 30, "almoco": 65, "jantar": 65},
        "mealsWhat": "restaurantes à la carte no almoço e no jantar",
        "transit": {
            "busRides": 0, "busFare": 0,
            "uberRides": 2, "uberFare": 34.00,
            "airportRides": 2, "airportFare": 23.00,
        },
        "transitWhat": "2 corridas de Uber por dia, sem transporte público",
    },
]


# Tarifa aérea doméstica média por trecho — ANAC, maio de 2026.
# Não entra mais no cálculo: serve só de referência de sanidade no relatório,
# já que agora todas as rotas têm estatística observada.
ANAC_TARIFA_MEDIA_TRECHO = 632.53


def montar_voos(observacoes):
    """Monta as rotas. Precedência da fonte, da melhor para a pior:

    1. cotação datada (Amadeus ou conferida na mão) para as datas do evento;
    2. estatística de 12 meses da rota, do Kayak — o padrão hoje.

    Não há mais estimativa sem lastro: toda origem tem dado observado.
    """
    voos = []
    for uf, capital, iata, regiao, search, barato, tmin, tmax, media, nota in COTACOES:
        obs = observacoes.get(uf)

        if media == 0:                       # federação anfitriã
            low = high = mid = 0
            origem, conferido = "anfitriã", ""
        elif obs:                            # cotação datada vence
            mid = obs["preco"]
            low, high = round(mid * 0.80), round(mid * 1.30)
            origem = "datado"
            conferido = f"{obs['fonte']}, {obs['conferido_em']}"
        else:                                # estatística da rota
            low, high, mid = tmin, tmax, media
            origem = "observado"
            conferido = f"Kayak (12 meses), {LEVANTADO_EM}"

        voos.append({
            "uf": uf, "capital": capital, "iata": iata,
            "searchIata": search or iata, "regiao": regiao,
            "low": low, "high": high, "mid": mid,
            "barato": barato,
            "origem": origem, "conferido": conferido,
            "fonte_url": url_kayak_rota(uf),
            "host": uf == "PE",
            **({"nota": nota} if nota else {}),
        })
    return voos


def montar_cenarios(hoteis):
    """Aplica a diária real do Booking/Amadeus quando existe cotação."""
    cenarios = []
    for c in CENARIOS:
        c = {**c, "meals": dict(c["meals"]), "transit": dict(c["transit"])}
        ab = AIRBNB.get(c["key"])
        if ab:
            c["airbnb"] = {
                **ab,
                "fonte": AIRBNB_FONTE,
                "url": AIRBNB_URL,
                "conferido_em": AIRBNB_EM,
            }

        obs = hoteis.get(c["key"])
        if obs and obs.get("diaria"):
            c["hospNight"] = obs["diaria"]
            c["hospOrigem"] = "observado"
            c["hospConferido"] = f"{obs['fonte']}, {obs['conferido_em']}"
            c["hospWhat"] = obs.get("categoria", c["hospWhat"])
        else:
            c["hospOrigem"] = "estimado"
        cenarios.append(c)
    return cenarios


def montar_payload():
    observacoes, hoteis = carregar_observacoes()
    conferidas = sorted(observacoes)

    return {
        "meta": {
            "moeda": "BRL",
            "destino": DESTINO,
            "evento": "ENEJ 27",
            "atualizado_em": date.today().isoformat(),
            "fonte": "tools/gerar_cotacoes.py",
            "fontes": FONTES,
            "calibracao": {
                "metodo": "estatistica observada por rota (Kayak, 12 meses)",
                "levantado_em": LEVANTADO_EM,
                "rotas_com_dado": len(COTACOES) - 1,   # exclui a anfitriã
                "cotacoes_datadas": len(conferidas),
                "ufs_datadas": conferidas,
                "hospedagem_conferida": bool(hoteis),
                "anac_referencia_trecho": ANAC_TARIFA_MEDIA_TRECHO,
            },
        },
        "voos": montar_voos(observacoes),
        "tiers": montar_cenarios(hoteis),
    }


INICIO = "/* >>> FALLBACK-INICIO"
FIM = "/* <<< FALLBACK-FIM */"


def injetar_fallback(payload):
    """Reescreve o payload de fallback dentro do index.html.

    Mantém as duas fontes idênticas: o JSON servido pela API e a cópia embutida
    que o painel usa quando a chamada falha."""
    html = SAIDA_HTML.read_text(encoding="utf-8")
    if INICIO not in html:
        print("  aviso: marcadores de fallback não encontrados no index.html")
        return

    bloco = (
        INICIO + " — gerado por tools/gerar_cotacoes.py, não edite à mão */\n"
        "const FALLBACK_PAYLOAD = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + ";\n" + FIM
    )
    novo = re.sub(
        re.escape(INICIO) + r".*?" + re.escape(FIM),
        lambda _: bloco,
        html,
        flags=re.S,
    )
    SAIDA_HTML.write_text(novo, encoding="utf-8", newline="\n")
    print(f"  fallback injetado em {SAIDA_HTML.name}")


def main():
    payload = montar_payload()

    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    cal = payload["meta"]["calibracao"]
    print(f"{SAIDA_JSON.name}: {len(payload['voos'])} origens, "
          f"{len(payload['tiers'])} cenarios")
    print(f"  {cal['rotas_com_dado']} rotas com estatistica observada; "
          f"{cal['cotacoes_datadas']} com cotacao datada")

    voos = [v for v in payload["voos"] if not v["host"]]
    media = sum(v["mid"] for v in voos) / len(voos)
    anac_rt = ANAC_TARIFA_MEDIA_TRECHO * 2
    print(f"  media ida e volta: R$ {media:.0f} "
          f"({media/anac_rt*100-100:+.0f}% vs media nacional da ANAC)")
    injetar_fallback(payload)


if __name__ == "__main__":
    main()
