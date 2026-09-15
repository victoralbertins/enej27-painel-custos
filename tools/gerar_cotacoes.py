#!/usr/bin/env python3
"""
Gera data/cotacoes-enej27.json e injeta o mesmo payload no index.html como
fallback, para as duas fontes nunca divergirem.

    python tools/gerar_cotacoes.py

-------------------------------------------------------------------------------
COMO AS PASSAGENS SÃO CALIBRADAS

O modelo base (BASE_VOO) é uma estimativa por distância/mercado. Sozinho ele
erra — e erra para baixo, como ficou claro quando a primeira cotação real foi
conferida (São Paulo, Kayak: R$ 1.154 contra R$ 760 estimados).

Por isso existe OBSERVACOES_VOO: cada linha é uma cotação conferida na fonte,
com data. A partir dela o script faz duas coisas:

  1. a rota observada passa a valer o número REAL, não a estimativa;
  2. todas as outras rotas são multiplicadas pelo fator médio entre o que foi
     observado e o que o modelo previa — hoje 1,52.

Confira mais rotas, adicione aqui e rode de novo: cada cotação nova melhora a
tabela inteira, e as rotas observadas param de ser chute.

PARA PLUGAR O BIGQUERY: troque BASE_VOO por uma query e mantenha o shape de
saída. A calibração deixa de ser necessária quando os preços vierem de uma
fonte real de cotação.
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
# MODELO BASE — estimativa central (ida e volta) antes da calibração.
# searchIata: código usado nos links de busca. Difere do iata quando a cidade
# tem código metropolitano (SAO cobre GRU+CGH, RIO cobre GIG+SDU).
# nota: alerta exibido no painel quando voar não é a opção óbvia.
# ---------------------------------------------------------------------------
BASE_VOO = [
    # (uf, capital,          iata,  regiao,         base, searchIata, nota)
    ("AC", "Rio Branco",     "RBR", "Norte",        1800, None, None),
    ("AP", "Macapá",         "MCP", "Norte",        1300, None, None),
    ("AM", "Manaus",         "MAO", "Norte",        1375, None, None),
    ("PA", "Belém",          "BEL", "Norte",         900, None, None),
    ("RO", "Porto Velho",    "PVH", "Norte",        1600, None, None),
    ("RR", "Boa Vista",      "BVB", "Norte",        1700, None, None),
    ("TO", "Palmas",         "PMW", "Norte",        1075, None, None),

    ("AL", "Maceió",         "MCZ", "Nordeste",      500, None,
     "Maceió fica a 260 km: ônibus leva ~4h, a partir de R$ 100 por trecho (~R$ 200 ida e volta)."),
    ("BA", "Salvador",       "SSA", "Nordeste",      620, None, None),
    ("CE", "Fortaleza",      "FOR", "Nordeste",      585, None, None),
    ("MA", "São Luís",       "SLZ", "Nordeste",      760, None, None),
    ("PB", "João Pessoa",    "JPA", "Nordeste",      465, None,
     "João Pessoa fica a 120 km: ônibus leva ~2h, a partir de R$ 27 por trecho (~R$ 60 ida e volta). Voar raramente compensa."),
    ("PE", "Recife",         "REC", "Nordeste",        0, None, None),  # anfitriã
    ("PI", "Teresina",       "THE", "Nordeste",      700, None, None),
    ("RN", "Natal",          "NAT", "Nordeste",      500, None,
     "Natal fica a 300 km: ônibus leva ~4h30, a partir de R$ 74 por trecho (~R$ 150 ida e volta)."),
    ("SE", "Aracaju",        "AJU", "Nordeste",      555, None, None),

    ("DF", "Brasília",       "BSB", "Centro-Oeste",  800, None, None),
    ("GO", "Goiânia",        "GYN", "Centro-Oeste",  940, None, None),
    ("MT", "Cuiabá",         "CGB", "Centro-Oeste", 1150, None, None),
    ("MS", "Campo Grande",   "CGR", "Centro-Oeste", 1190, None, None),

    ("ES", "Vitória",        "VIX", "Sudeste",       850, None, None),
    ("MG", "Belo Horizonte", "CNF", "Sudeste",       815, None, None),
    ("RJ", "Rio de Janeiro", "GIG", "Sudeste",       785, "RIO", None),
    ("SP", "São Paulo",      "GRU", "Sudeste",       760, "SAO", None),

    ("PR", "Curitiba",       "CWB", "Sul",           975, None, None),
    ("SC", "Florianópolis",  "FLN", "Sul",          1035, None, None),
    ("RS", "Porto Alegre",   "POA", "Sul",          1100, None, None),
]

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
# Serve de âncora de NÍVEL enquanto não há observação suficiente por rota.
ANAC_TARIFA_MEDIA_TRECHO = 632.53
OBSERVACOES_MINIMAS = 5  # a partir daqui as observações substituem a âncora


def fator_calibracao(observacoes):
    """Quanto o modelo base precisa ser multiplicado para bater com a realidade.

    Dois regimes, e o segundo é melhor:

    1. POUCAS OBSERVAÇÕES -> ancora o nível na média oficial da ANAC. Calibrar
       a tabela inteira pela razão de uma única rota superestima: uma rota-tronco
       como SP-REC é mais barata que a média nacional, então o fator dela não
       descreve as outras. Foi o erro da primeira versão (fator 1,52, que jogava
       a tabela 20% acima da ANAC).

    2. OBSERVACOES_MINIMAS OU MAIS -> usa a razão média observada/modelo, que a
       essa altura já descreve o mercado melhor que a média nacional.

    Em qualquer regime, rota observada vale o preço real, não o calibrado.
    """
    base = {uf: b for uf, _, _, _, b, _, _ in BASE_VOO}

    razoes = [obs["preco"] / base[uf]
              for uf, obs in observacoes.items()
              if base.get(uf)]

    if len(razoes) >= OBSERVACOES_MINIMAS:
        return sum(razoes) / len(razoes)

    # Âncora ANAC: a média ida e volta da tabela deve bater com a média nacional.
    precos = [b for b in base.values() if b]
    media_base = sum(precos) / len(precos)
    alvo = ANAC_TARIFA_MEDIA_TRECHO * 2
    return alvo / media_base if media_base else 1.0


def montar_voos(fator, observacoes):
    voos = []
    for uf, capital, iata, regiao, base, search, nota in BASE_VOO:
        obs = observacoes.get(uf)

        if base == 0:                 # federação anfitriã
            centro, origem = 0, "anfitriã"
        elif obs:                     # cotação real conferida
            centro, origem = obs["preco"], "observado"
        else:                         # estimativa calibrada
            centro, origem = base * fator, "estimado"

        voos.append({
            "uf": uf,
            "capital": capital,
            "iata": iata,
            "searchIata": search or iata,
            "regiao": regiao,
            "low": round(centro * FAIXA_MIN),
            "high": round(centro * FAIXA_MAX),
            "origem": origem,
            "host": uf == "PE",
            **({"nota": nota} if nota else {}),
            **({"conferido": f"{obs['fonte']}, {obs['conferido_em']}"} if obs else {}),
        })
    return voos


def montar_cenarios(hoteis):
    """Aplica a diária real do Booking/Amadeus quando existe cotação."""
    cenarios = []
    for c in CENARIOS:
        c = {**c, "meals": dict(c["meals"]), "transit": dict(c["transit"])}
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
    fator = fator_calibracao(observacoes)
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
                "fator": round(fator, 4),
                "observacoes": len(conferidas),
                "ufs": conferidas,
                "hospedagem_conferida": bool(hoteis),
            },
        },
        "voos": montar_voos(fator, observacoes),
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
    print(f"  calibracao: fator {cal['fator']} a partir de "
          f"{cal['observacoes']} cotacao(oes) real(is): {', '.join(cal['ufs'])}")
    injetar_fallback(payload)

    sp = next(v for v in payload["voos"] if v["uf"] == "SP")
    print(f"  SP: R$ {sp['low']}-{sp['high']} ({sp['origem']})")


if __name__ == "__main__":
    main()
