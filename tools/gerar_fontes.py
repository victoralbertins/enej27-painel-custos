#!/usr/bin/env python3
"""
Gera FONTES.csv e FONTES.md — a procedência de cada número do painel.

    python tools/gerar_fontes.py

Os dois saem do MESMO dado que alimenta o painel (data/cotacoes-enej27.json),
então não têm como divergir dos números publicados. O CSV abre direto no Excel,
Google Sheets ou LibreOffice; o MD é a versão legível no GitHub.

Ambos são GERADOS: não edite à mão, edite a fonte e rode o script.

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
SAIDA_CSV = RAIZ / "FONTES.csv"
SAIDA_MD = RAIZ / "FONTES.md"

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


def linhas_airbnb(dados):
    """Uma linha por cenário, a partir do bloco airbnb do próprio payload."""
    for t in dados["tiers"]:
        ab = t.get("airbnb")
        if not ab:
            continue
        yield [
            "Hospedagem (Airbnb)",
            f"{t['name']} — {ab['listing']}",
            ab["night"],
            "BRL por noite (apartamento inteiro)",
            "dado real",
            ab["fonte"],
            ab["url"],
            ab["conferido_em"],
            f"capacidade {ab['capacity']} pessoas; o painel divide pelo tamanho do grupo "
            f"(R$ {round(ab['night']/ab['capacity'])}/pessoa se lotado)",
        ]


def tabela_md(cabecalho, linhas):
    out = ["| " + " | ".join(cabecalho) + " |",
           "|" + "|".join("---" for _ in cabecalho) + "|"]
    for l in linhas:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in l) + " |")
    return "\n".join(out)


def escrever_md(dados, linhas_voo, anac_rt, media_rt):
    voos = sorted((v for v in dados["voos"] if not v["host"]),
                  key=lambda v: v["mid"])
    cal = dados["meta"]["calibracao"]

    br = lambda n: f"{n:,}".replace(",", ".")
    rotas = [[
        v["uf"],
        v["capital"],
        br(v["low"]) + "–" + br(v["high"]),
        "**" + br(v["mid"]) + "**",
        br(v["barato"]),
        "datada" if v["origem"] == "datado" else "12 meses",
        f"[↗]({v['fonte_url']})" if v.get("fonte_url") else "—",
    ] for v in voos]

    # Descasamento entre a media observada e o meio da faixa. Calculado, nao
    # fixado no texto, para nao divergir quando os dados mudarem.
    stats = [v for v in voos if v["origem"] == "observado"]
    pior = max(stats, key=lambda v: (v["low"] + v["high"]) / 2 - v["mid"])
    meio = round((pior["low"] + pior["high"]) / 2)
    desvio = (meio - pior["mid"]) / pior["mid"] * 100

    soma_mid = sum(v["mid"] for v in stats)
    soma_meio = sum((v["low"] + v["high"]) / 2 for v in stats)
    agregado = (soma_meio - soma_mid) / soma_mid * 100

    exemplo = (f"a maior distância está em {pior['capital']}: média de "
               f"R$ {br(pior['mid'])} contra R$ {br(meio)} no meio da faixa, "
               f"{desvio:+.0f}%. No agregado das {len(stats)} rotas, o meio da faixa "
               f"fica **{agregado:+.0f}%** acima da média observada")

    airbnb = list(linhas_airbnb(dados))
    com_fonte = [o for o in OUTROS if o[4] in ("dado real", "cotação datada")
                 and o[0] != "Evento"]
    sem_fonte = [o for o in OUTROS if o[4] == "estimativa"]

    md = f"""# Fontes dos valores do painel

> **Arquivo gerado.** Sai de `data/cotacoes-enej27.json` via
> `python tools/gerar_fontes.py`. Não edite à mão — edite a fonte e rode o script.
> Versão em planilha: [FONTES.csv](FONTES.csv) (separador `;`, abre no Excel).

Levantamento em **15 de setembro de 2026**.

A regra de leitura: **dado real** tem cotação por trás; **estimativa** não tem, e o
painel marca esses casos em âmbar.

---

## 1. Passagens aéreas — {cal['rotas_com_dado']} de {cal['rotas_com_dado']} rotas com dado real

Levantadas nas páginas de rota do Kayak, uma por origem. Cada página publica a
estatística observada dos últimos 12 meses. Valores de **ida e volta em R$**, ordenados
do mais barato ao mais caro.

{tabela_md(["UF", "Origem", "Faixa típica", "Média (usada)", "Menor achado", "Base", "Fonte"], rotas)}

A coluna **Base** diz de onde vem a linha: `12 meses` é a estatística da rota;
`datada` é uma cotação para as datas exatas do evento, que tem precedência quando existe.

**A média é o valor que o painel usa**, não o meio da faixa típica. Os dois não
coincidem, e a diferença varia de rota para rota: {exemplo}. É por isso que o campo `mid`
vem explícito no JSON — calcular `(low+high)/2` inflaria a conta do congressista.

Não são cotações para as datas exatas do evento: são a estatística da rota. Quando o
[pipeline da Amadeus](README.md#cotações-automáticas) estiver ligado, ele sobrepõe estes
valores com preço datado, e a linha passa a exibir *cotação datada*.

---

## 2. Hospedagem via Airbnb

O Airbnb entra como **alternativa** ao hotel/hostel, selecionável no painel. A lógica é
diferente: o apartamento tem preço fixo por noite até a capacidade, então o custo por
pessoa cai conforme a delegação cresce.

{tabela_md(["Cenário", "Anúncio", "Diária", "Capacidade", "Por pessoa se lotado"],
           [[a[1].split(" — ")[0], a[1].split(" — ")[1], f"R$ {a[2]}",
             a[8].split(" ")[1] + " pessoas",
             "R$ " + a[8].split("R$ ")[1].split("/")[0]] for a in airbnb])}

Fonte: [{airbnb[0][5]}]({airbnb[0][6]}), consultado em {airbnb[0][7]}.

> **Ressalva sobre a fonte.** O Airbnb não publica preço sem uma busca com datas, então
> não é indexável. Os valores vêm do cozycozy, agregador que lista aluguel por temporada de
> várias plataformas — os anúncios podem estar no Airbnb, no Booking ou em ambos. São
> preços reais de anúncios reais, mas não saíram da API do Airbnb. O painel leva ao
> Airbnb com as datas e o tamanho do grupo já preenchidos, para conferir.

---

## 3. Demais valores com fonte

{tabela_md(["Categoria", "Item", "Valor", "Fonte", "Onde conferir"],
           [[o[0], o[1], o[2], o[5], f"[↗]({o[6]})" if o[6] else "—"] for o in com_fonte])}

---

## 4. Sem fonte — use com ceticismo

Estes números **não** foram verificados. São julgamento de mercado, e o painel os marca
como estimativa.

{tabela_md(["Categoria", "Item", "Valor", "Por que não tem fonte"],
           [[o[0], o[1], o[2], o[8] or "sem índice publicado"] for o in sem_fonte])}

---

## 5. Hipóteses de trabalho

| Item | Adotado | Situação |
|---|---|---|
| Datas do ENEJ 27 | 25 a 30/08/2027 | **Não divulgadas.** O [site oficial](https://enej.brasiljunior.org.br/) ainda mostra o ENEJ'26. A janela de agosto replica a do ENEJ 26. |
| Sede | 4 candidatas simuláveis | Não definida — por isso é um seletor. |
| Estadia | 5 pernoites / 6 dias | Herdado do painel do ENEJ 26. |
| Ingresso | fora do cálculo | Lotes não divulgados. |
| Sazonalidade (8+ semanas, até +80%) | mantida | Herdada do código do ENEJ 26, não verificada por mim. |

---

## 6. Aferição

A média de ida e volta da tabela está em **R$ {media_rt:,.0f}**, ou **{media_rt/anac_rt*100-100:+.0f}%**
sobre a média nacional da ANAC de R$ {anac_rt:,.0f} (2 × R$ {anac_rt/2:,.2f} por trecho, mai/2026).
Coerente: todas as rotas terminam em Recife, mais distante que a média dos pares nacionais.

**Correção de método, para registro.** As duas versões anteriores partiam de um modelo
estimado por distância e o corrigiam por um fator. A primeira calibrava pela razão de uma
única rota (São Paulo), o que superestimava — SP–REC é rota-tronco e custa *menos* que a
média nacional, então o fator dela não descrevia as outras. A segunda ancorou o nível na
ANAC, o que melhorou mas seguia sendo estimativa. Esta versão **elimina o modelo**: cada
rota tem o seu próprio dado observado.

**Achado que o dado real expôs:** voar de João Pessoa custa em média **mais** que de São
Paulo (R$ 1.162 contra R$ 1.085) para 120 km de distância. Por isso o painel alerta,
nessa origem, que o ônibus custa a partir de R$ 27 por trecho.

---

## 7. O que fecharia as lacunas

- **Passagens com data e hotéis:** o [pipeline da Amadeus](README.md#cotações-automáticas)
  — falta cadastrar as credenciais.
- **Alimentação e transporte intraurbano:** não existe API. O que resolve é alguém que
  more em Recife conferir. A FEJEPE é a fonte certa.
- **Distâncias das sedes:** medir no Google Maps quando a sede for definida.
"""
    SAIDA_MD.write_text(md, encoding="utf-8", newline="\n")


def main():
    dados = json.loads(ENTRADA.read_text(encoding="utf-8"))
    linhas_voo = list(linhas_voos(dados))
    linhas = linhas_voo + list(linhas_airbnb(dados)) + [list(o) for o in OUTROS]

    with open(SAIDA_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(CABECALHO)
        w.writerows(linhas)

    voos = [v for v in dados["voos"] if not v["host"]]
    media_rt = sum(v["mid"] for v in voos) / len(voos)
    anac_rt = 632.53 * 2
    escrever_md(dados, linhas_voo, anac_rt, media_rt)

    reais = sum(1 for l in linhas if l[4] in ("dado real", "cotação datada"))
    print(f"{SAIDA_CSV.name}: {len(linhas)} linhas "
          f"({reais} com fonte, {len(linhas) - reais} sem)")
    print(f"{SAIDA_MD.name}: gerado a partir do mesmo dado")


if __name__ == "__main__":
    main()
