#!/usr/bin/env python3
"""
Gera data/cotacoes-enej27.json — o payload que o painel consome via fetch().

Este script é a PONTE para o seu backend: a estrutura de saída é exatamente a
que o painel espera. Para plugar o BigQuery, troque as constantes VOOS e
CENARIOS por uma query e mantenha o mesmo shape de saída.

    python tools/gerar_cotacoes.py

Fluxo com BigQuery ficaria assim:

    from google.cloud import bigquery
    client = bigquery.Client()
    rows = client.query(SQL_COTACOES).result()
    voos = [dict(r) for r in rows]

E o resto do script (montagem do JSON) segue igual.
"""

import json
import pathlib
from datetime import date

SAIDA = pathlib.Path(__file__).resolve().parent.parent / "data" / "cotacoes-enej27.json"

DESTINO = "REC"  # Aeroporto Internacional dos Guararapes, Recife

# ---------------------------------------------------------------------------
# PASSAGENS
# Faixa de ida e volta em BRL até REC, para compra com 8+ semanas de
# antecedência. O painel usa a média da faixa e aplica a sazonalidade.
#
# searchIata: código usado nos links de busca. Difere do iata quando a cidade
# tem código metropolitano (SAO cobre GRU+CGH, RIO cobre GIG+SDU), o que traz
# resultados melhores no Google Flights e no Kayak.
# ---------------------------------------------------------------------------
VOOS = [
    # (uf, capital,          iata,  regiao,         low,  high, searchIata)
    ("AC", "Rio Branco",     "RBR", "Norte",        1500, 2100, None),
    ("AP", "Macapá",         "MCP", "Norte",        1100, 1500, None),
    ("AM", "Manaus",         "MAO", "Norte",        1150, 1600, None),
    ("PA", "Belém",          "BEL", "Norte",         750, 1050, None),
    ("RO", "Porto Velho",    "PVH", "Norte",        1350, 1850, None),
    ("RR", "Boa Vista",      "BVB", "Norte",        1450, 1950, None),
    ("TO", "Palmas",         "PMW", "Norte",         900, 1250, None),

    ("AL", "Maceió",         "MCZ", "Nordeste",      380,  620, None),
    ("BA", "Salvador",       "SSA", "Nordeste",      480,  760, None),
    ("CE", "Fortaleza",      "FOR", "Nordeste",      450,  720, None),
    ("MA", "São Luís",       "SLZ", "Nordeste",      620,  900, None),
    ("PB", "João Pessoa",    "JPA", "Nordeste",      350,  580, None),
    ("PE", "Recife",         "REC", "Nordeste",        0,    0, None),  # anfitriã
    ("PI", "Teresina",       "THE", "Nordeste",      560,  840, None),
    ("RN", "Natal",          "NAT", "Nordeste",      380,  620, None),
    ("SE", "Aracaju",        "AJU", "Nordeste",      430,  680, None),

    ("DF", "Brasília",       "BSB", "Centro-Oeste",  650,  950, None),
    ("GO", "Goiânia",        "GYN", "Centro-Oeste",  780, 1100, None),
    ("MT", "Cuiabá",         "CGB", "Centro-Oeste",  950, 1350, None),
    ("MS", "Campo Grande",   "CGR", "Centro-Oeste",  980, 1400, None),

    ("ES", "Vitória",        "VIX", "Sudeste",       700, 1000, None),
    ("MG", "Belo Horizonte", "CNF", "Sudeste",       650,  980, None),
    ("RJ", "Rio de Janeiro", "GIG", "Sudeste",       620,  950, "RIO"),
    ("SP", "São Paulo",      "GRU", "Sudeste",       600,  920, "SAO"),

    ("PR", "Curitiba",       "CWB", "Sul",           800, 1150, None),
    ("SC", "Florianópolis",  "FLN", "Sul",           850, 1220, None),
    ("RS", "Porto Alegre",   "POA", "Sul",           900, 1300, None),
]

# ---------------------------------------------------------------------------
# CENÁRIOS DE GASTO
# Descritos por VALOR UNITÁRIO — quem fecha a conta é o painel, multiplicando
# pelas noites/dias do evento. Assim a memória de cálculo na tela é a mesma
# operação que gerou o número.
#
# transit:
#   busRides/busFare       embarques de ônibus ou metrô por dia
#   uberRides/uberFare     corridas de Uber/99 por dia (entram no fator da sede)
#   airportRides/airportFare  traslado do aeroporto, ida e volta — cobrado uma
#                             vez na viagem e NÃO multiplicado pelo fator da
#                             sede, porque o trajeto REC -> Boa Viagem é o mesmo
#                             independente de onde o evento acontecer.
# ---------------------------------------------------------------------------
CENARIOS = [
    {
        "key": "econ",
        "name": "Econômico",
        "desc": "Hostel compartilhado em Boa Viagem, prato feito e ônibus/metrô.",
        "hospNight": 70,
        "hospWhat": "cama em quarto compartilhado",
        "hotelFilter": "ht_id%3D203",  # Booking: tipo hostel
        "meals": {"cafe": 12, "almoco": 25, "jantar": 23},
        "mealsWhat": "padaria, prato feito e lanche à noite",
        "transit": {
            "busRides": 4, "busFare": 4.90,
            "uberRides": 1, "uberFare": 7.00,
            "airportRides": 2, "airportFare": 22.00,
        },
        "transitWhat": "4 embarques de ônibus/metrô + 1 Uber noturno dividido entre 4",
    },
    {
        "key": "inter",
        "name": "Intermediário",
        "desc": "Hotel 3 estrelas em quarto duplo, self-service e mix de ônibus e Uber.",
        "hospNight": 130,
        "hospWhat": "quarto duplo, valor por pessoa",
        "hotelFilter": "class%3D3",
        "meals": {"cafe": 18, "almoco": 42, "jantar": 35},
        "mealsWhat": "café do hotel, self-service por quilo e jantar simples",
        "transit": {
            "busRides": 2, "busFare": 4.90,
            "uberRides": 1, "uberFare": 24.00,
            "airportRides": 2, "airportFare": 22.00,
        },
        "transitWhat": "2 embarques de ônibus + 1 corrida de Uber por dia",
    },
    {
        "key": "conforto",
        "name": "Conforto",
        "desc": "Hotel 4 estrelas na orla, restaurantes à la carte e Uber em todos os trajetos.",
        "hospNight": 250,
        "hospWhat": "apartamento na orla de Boa Viagem",
        "hotelFilter": "class%3D4",
        "meals": {"cafe": 30, "almoco": 65, "jantar": 65},
        "mealsWhat": "restaurantes à la carte no almoço e no jantar",
        "transit": {
            "busRides": 0, "busFare": 0,
            "uberRides": 2, "uberFare": 34.00,
            "airportRides": 2, "airportFare": 26.00,
        },
        "transitWhat": "2 corridas de Uber por dia, sem transporte público",
    },
]


def montar_payload():
    voos = []
    for uf, capital, iata, regiao, low, high, search in VOOS:
        voos.append({
            "uf": uf,
            "capital": capital,
            "iata": iata,
            "searchIata": search or iata,
            "regiao": regiao,
            "low": low,
            "high": high,
            "host": uf == "PE",
        })

    return {
        "meta": {
            "moeda": "BRL",
            "destino": DESTINO,
            "evento": "ENEJ 27",
            "atualizado_em": date.today().isoformat(),
            "fonte": "tools/gerar_cotacoes.py",
        },
        "voos": voos,
        "tiers": CENARIOS,
    }


def main():
    payload = montar_payload()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{SAIDA.relative_to(SAIDA.parent.parent)}: "
          f"{len(payload['voos'])} origens, {len(payload['tiers'])} cenários")


if __name__ == "__main__":
    main()
