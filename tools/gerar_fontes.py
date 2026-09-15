#!/usr/bin/env python3
"""
Gera FONTES.csv — a planilha de procedência de cada número do painel.

    python tools/gerar_fontes.py

A planilha sai do MESMO dado que alimenta o painel (data/cotacoes-enej27.json),
então ela não tem como divergir dos números publicados. Abre direto no Excel,
Google Sheets ou LibreOffice.

Colunas:
    categoria      Passagem aérea / Hospedagem / Alimentação / ...
    item           o que o número representa
    valor          o número usado no painel
    unidade        BRL ida e volta, BRL/noite, BRL/dia, km...
    procedencia    dado real | cotação datada | estimativa
    fonte          quem publicou
    url            onde conferir
    consultado_em  data do levantamento
    observacao     ressalva relevante
"""

import csv
import json
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "cotacoes-enej27.json"
SAIDA = RAIZ / "FONTES.csv"

CABECALHO = ["categoria", "item", "valor", "unidade", "procedencia",
             "fonte", "url", "consultado_em", "observacao"]

PROCEDENCIA = {
    "datado": "cotação datada",
    "observado": "dado real",
    "estimado": "estimativa",
    "anfitriã": "não se aplica",
}

# Itens que não vêm do JSON de rotas: fontes levantadas manualmente.
OUTROS = [
    ("Referência", "Tarifa aérea doméstica média (nacional, mai/2026)", "632,53",
     "BRL por trecho", "dado real", "ANAC — dados tarifários mensais",
     "https://www.gov.br/anac/pt-br/noticias/2026/anac-publica-dados-tarifarios-do-mes-de-maio-de-2026",
     "2026-09-15", "Usada só como aferição de sanidade da média da tabela"),

    ("Transporte interno", "Tarifa de ônibus urbano (Anel A)", "4,50", "BRL por embarque",
     "dado real", "Grande Recife Consórcio, via Folha PE",
     "https://www.folhape.com.br/noticias/aumento-da-passagem-de-onibus-no-grande-recife-e-homologado-e-anel-a/463122/",
     "2026-09-15", "Homologado; vigente desde 01/02/2026"),

    ("Transporte interno", "Uber aeroporto REC <-> Boa Viagem", "23", "BRL por corrida",
     "dado real", "Uber — página oficial de estimativa da rota",
     "https://www.uber.com/global/en/r/routes/recife-pe-br-to-rec/",
     "2026-09-15", "5,71 km, ~19 min; media de corridas UberX no ultimo ano"),

    ("Transporte interno", "Corrida de Uber intraurbana", "7 / 24 / 34", "BRL por corrida",
     "estimativa", "extrapolação da tarifa oficial REC<->Boa Viagem", "",
     "2026-09-15", "Ancorada em dado real, mas extrapolada para outros trajetos"),

    ("Alimentação", "Prato feito (almoço)", "30 a 31,90", "BRL por refeição",
     "dado real", "Abrasel, via Mercado&Consumo",
     "https://mercadoeconsumo.com.br/07/05/2026/foodservice/alimentacao-fora-de-casa-fica-mais-cara-e-prato-feito-atinge-media-de-r-3027/",
     "2026-09-15", "Media nacional jun/2026; Nordeste ~R$ 30"),

    ("Alimentação", "Café da manhã", "12 / 18 / 30", "BRL por refeição",
     "estimativa", "", "", "2026-09-15", "Não há índice publicado por refeição isolada"),

    ("Alimentação", "Jantar", "24 / 36 / 65", "BRL por refeição",
     "estimativa", "", "", "2026-09-15", "Idem; só o almoço tem índice Abrasel"),

    ("Hospedagem", "Diária média em Recife (quarto duplo)", "280", "BRL por diária",
     "dado real", "Dicas de Viagem / Viaje na Viagem",
     "https://www.dicasdeviagem.com/hoteis-em-recife/",
     "2026-09-15", "Base da diária do cenário Intermediário (R$ 140 por pessoa)"),

    ("Hospedagem", "Tendência da diária média em Recife", "+17,1% jan/26; +10,1% jun/26",
     "variação anual", "dado real", "FOHB / InFOHB, via Panrotas",
     "https://www.panrotas.com.br/hotelaria/mercado/2026/02/hotelaria-cresce-em-janeiro-e-revpar-avanca-105-no-brasil_226015.html",
     "2026-09-15", "Indica pressão de alta sobre as diárias"),

    ("Hospedagem", "Diária de hostel (cama compartilhada)", "85", "BRL por diária",
     "estimativa", "", "", "2026-09-15",
     "Hostelworld e Booking só exibem preço após consulta com datas"),

    ("Hospedagem", "Diária 4 estrelas na orla", "200", "BRL por pessoa",
     "estimativa", "", "", "2026-09-15", "Derivada do padrão de mercado, sem cotação"),

    ("Sede", "Geraldão — endereço e capacidade", "Av. Mascarenhas de Moraes, 13 mil lugares",
     "-", "dado real", "Prefeitura do Recife",
     "https://www2.recife.pe.gov.br/pagina/ginasio-de-esportes-geraldo-magalhaes-geraldao",
     "2026-09-15", ""),

    ("Sede", "Cecon — distância do aeroporto", "12", "km", "dado real",
     "Centro de Convenções de Pernambuco", "http://www.cecon.pe.gov.br/o-cecon-pe/",
     "2026-09-15", ""),

    ("Sede", "Recife Expo Center — localização", "~20 min do aeroporto e de Boa Viagem",
     "-", "dado real", "Recife Expo Center", "https://recifeexpocenter.com.br/",
     "2026-09-15", ""),

    ("Sede", "Distâncias Boa Viagem -> sedes", "6 / 13 / 13 / 14", "km",
     "estimativa", "", "", "2026-09-15", "Aproximações; medir quando a sede for definida"),

    ("Sede", "Fator de deslocamento da sede", "1 + (km/6 - 1) x 0,30", "multiplicador",
     "estimativa", "", "", "2026-09-15", "Heurística; o amortecimento 0,30 não tem base empírica"),

    ("Rodoviário", "Ônibus João Pessoa -> Recife", "a partir de 27", "BRL por trecho",
     "dado real", "ClickBus", "https://www.clickbus.com.br/onibus/joao-pessoa-pb",
     "2026-09-15", "120 km, ~2h"),

    ("Rodoviário", "Ônibus Recife -> Natal", "a partir de 74", "BRL por trecho",
     "dado real", "CheckMyBus", "https://www.checkmybus.com/recife/natal",
     "2026-09-15", "300 km, ~4h30"),

    ("Rodoviário", "Ônibus Recife -> Maceió", "a partir de 99,90", "BRL por trecho",
     "dado real", "CheckMyBus", "https://www.checkmybus.com/joao-pessoa/maceio",
     "2026-09-15", "260 km, ~4h"),

    ("Evento", "Datas do ENEJ 27", "25 a 30/08/2027", "-", "estimativa",
     "hipótese de trabalho", "https://enej.brasiljunior.org.br/",
     "2026-09-15", "Não divulgadas; site oficial ainda mostra o ENEJ'26"),

    ("Evento", "Sede do ENEJ 27", "4 candidatas", "-", "estimativa",
     "hipótese de trabalho", "", "2026-09-15", "Não definida; por isso é um seletor"),

    ("Evento", "Ingresso", "0", "BRL", "não se aplica", "", "",
     "2026-09-15", "Lotes não divulgados; fora da interface e do cálculo"),

    ("Evento", "Regra de sazonalidade (8+ semanas, até +80%)", "-", "-", "estimativa",
     "herdado do código do ENEJ 26", "", "2026-09-15", "Não verificado"),
]


def linhas_voos(dados):
    for v in dados["voos"]:
        if v["host"]:
            continue
        yield [
            "Passagem aérea",
            f"{v['capital']} ({v['iata']}) -> Recife (REC), ida e volta",
            v["mid"],
            "BRL ida e volta",
            PROCEDENCIA.get(v["origem"], v["origem"]),
            v["conferido"].split(",")[0].strip(),
            v.get("fonte_url", ""),
            v["conferido"].split(",")[-1].strip(),
            f"faixa típica {v['low']}-{v['high']}; menor achado {v['barato']}",
        ]


def main():
    dados = json.loads(ENTRADA.read_text(encoding="utf-8"))

    with open(SAIDA, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(CABECALHO)
        linhas = list(linhas_voos(dados)) + [list(o) for o in OUTROS]
        w.writerows(linhas)

    reais = sum(1 for l in linhas if l[4] in ("dado real", "cotação datada"))
    print(f"{SAIDA.name}: {len(linhas)} linhas "
          f"({reais} com fonte, {len(linhas) - reais} sem)")


if __name__ == "__main__":
    main()
