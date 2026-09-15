# Painel de Custos do Congressista — ENEJ 27 · Recife

Simulador de custo de participação no **ENEJ 27**, em Recife/PE. O congressista escolhe o
estado de origem, a sede candidata e o tamanho da delegação, e o painel estima passagem
aérea, hospedagem, alimentação e transporte interno em três cenários de gasto.

Refatoração do painel do ENEJ 26 (Belo Horizonte) para a identidade e o contexto do ENEJ 27.

## O que mudou em relação ao painel do ENEJ 26

| | ENEJ 26 | ENEJ 27 |
|---|---|---|
| Paleta | marrom, vermelho, laranja | azul escuro, azul claro, amarelo, verde (edital ENEJ 27) |
| Destino | Belo Horizonte — MG | **Recife — PE** (REC) |
| Sede | fixa (Mineirão) | **seletor** com 4 candidatas, que ajusta o transporte interno |
| Ingresso | R$ 530,72 somados ao total | **removido** da interface e do cálculo (lotes não divulgados) |
| Tarifas | tabela estática no JS | `fetch()` assíncrono + estado de carregamento + fallback simulado |

## Sedes candidatas

O seletor cobre as quatro opções em estudo. Cada uma tem um **fator de deslocamento**
aplicado ao custo de transporte interno, proporcional à distância até a rede hoteleira de
Boa Viagem:

| Sede | Localização | ~km de Boa Viagem | Fator |
|---|---|---|---|
| Geraldão | Imbiribeira, Recife | 6 | 1,00 |
| Recife Expo Center | Salgadinho, Olinda | 13 | 1,18 |
| Centro de Convenções (Cecon) | Salgadinho, Olinda | 13 | 1,20 |
| Classic Hall | Salgadinho, Olinda | 14 | 1,25 |

## A API (já funcionando)

O painel faz um `fetch()` real. O endpoint ativo é o próprio GitHub Pages deste
repositório, que serve o JSON do contrato e responde com `Access-Control-Allow-Origin: *`
— então a chamada funciona de qualquer domínio:

```
https://victoralbertins.github.io/enej27-painel-custos/data/cotacoes-enej27.json
```

Esse arquivo é gerado por [`tools/gerar_cotacoes.py`](tools/gerar_cotacoes.py):

```bash
python tools/gerar_cotacoes.py
```

O script é a **ponte para o BigQuery**: a estrutura de saída é exatamente a que o painel
espera, então trocar as constantes `VOOS`/`CENARIOS` por uma query preserva o contrato.

```python
from google.cloud import bigquery
client = bigquery.Client()
voos = [dict(r) for r in client.query(SQL_COTACOES).result()]
# o resto do script segue igual
```

## Cotações automáticas

O painel não busca preço direto do navegador — Kayak e Google Flights bloqueiam por CORS e
por ToS, e qualquer chave de API numa página estática pública ficaria exposta. A busca
acontece **fora do navegador**:

```
GitHub Actions (semanal)
  └─ tools/cotacoes_amadeus.py   busca preços reais na Amadeus  ──► data/observacoes.json
       └─ tools/gerar_cotacoes.py   funde e publica             ──► data/cotacoes-enej27.json
            └─ o painel lê esse JSON já pronto
```

A chave fica em secrets do repositório e nunca chega ao cliente.

### Ligando (uma vez)

1. Crie uma conta em [developers.amadeus.com](https://developers.amadeus.com) → **Self-Service**
   → novo app. Copie a **API Key** e a **API Secret**. O tier gratuito cobre folgadamente o
   uso deste painel.
2. No repositório: **Settings → Secrets and variables → Actions → New repository secret**,
   crie `AMADEUS_CLIENT_ID` e `AMADEUS_CLIENT_SECRET`.
3. **Settings → Actions → General → Workflow permissions** → marque **Read and write
   permissions** (o workflow precisa commitar o JSON atualizado).
4. **Actions → Atualizar cotações → Run workflow** para rodar na hora. Depois roda sozinho
   toda segunda.

Sem os secrets, o workflow não quebra: o passo de busca é pulado e o painel segue com a
estatística de 12 meses de cada rota.

### Procedência dos preços

Não há mais estimativa nas passagens: **as 26 origens têm dado real**, levantado nas
páginas de rota do Kayak (estatística observada de 12 meses). O inventário com a URL de
cada rota está em [FONTES.md](FONTES.md) e [FONTES.csv](FONTES.csv).

O painel classifica cada número em três regimes, com selo próprio:

| Selo | Significa |
|---|---|
| **cotação datada** (verde) | preço para as datas exatas do evento — o melhor dado |
| **dado real** (azul) | estatística observada da rota nos últimos 12 meses |
| **estimativa** (âmbar) | sem cotação por trás |

A precedência é essa ordem: quando a busca da Amadeus traz preço datado para uma rota, ele
sobrepõe a estatística de 12 meses.

**Aferição:** a média de ida e volta da tabela fica em R$ 1.300, ou +3% sobre a média
nacional da ANAC (2 × R$ 632,53 por trecho, mai/2026) — coerente com rotas que terminam no
Nordeste.

Alimentação, transporte intraurbano e diárias de hostel seguem como estimativa; a seção 3
do [FONTES.md](FONTES.md) lista cada uma e por quê.

> **Limite honesto:** o ambiente de teste da Amadeus é gratuito mas tem cobertura parcial
> de rotas. Para cobertura total, troque `AMADEUS_HOST` para o host de produção. Os links
> de cada cenário sempre levam à cotação real na fonte.

## Plugando o seu backend (Python / BigQuery)

Toda a camada de dados fica em `loadDynamicData()`:

1. **Endpoint** — troque a constante no topo do `<script>`:
   ```js
   const API_ENDPOINT = "https://enej27-api.suaempresa.com/v1/cotacoes"; // <<< TROQUE AQUI
   ```
2. **Autenticação** — headers em `API_HEADERS`. Como o arquivo é público, não coloque
   chave secreta aqui: use uma API pública de leitura ou um proxy que injete a credencial.
3. **CORS** — o backend precisa responder com `Access-Control-Allow-Origin` para o domínio
   onde o painel estiver hospedado.
4. **Timeout** — `API_TIMEOUT_MS` (6s) aborta a chamada via `AbortController`.

Enquanto a API não existir, `loadDynamicData()` cai automaticamente no payload de
`simulatedPayload()` e o painel continua funcionando. O selo no rodapé mostra qual fonte
está em uso.

### Contrato do JSON

Sua query no BigQuery deve devolver exatamente este shape:

```json
{
  "meta": {
    "moeda": "BRL", "destino": "REC", "atualizado_em": "2026-09-15", "fonte": "bigquery",
    "calibracao": { "rotas_com_dado": 26, "cotacoes_datadas": 1, "levantado_em": "2026-09-15" }
  },
  "voos": [
    { "uf": "SP", "capital": "São Paulo", "iata": "GRU", "searchIata": "SAO",
      "regiao": "Sudeste", "low": 873, "high": 1513, "mid": 1085, "barato": 758,
      "origem": "observado", "conferido": "Kayak (12 meses), 2026-09-15",
      "fonte_url": "https://www.kayak.com.br/flight-routes/Sao-Paulo-SAO/Recife-REC",
      "host": false }
  ],
  "tiers": [
    { "key": "econ", "name": "Econômico", "desc": "...",
      "hospNight": 85, "hospWhat": "cama em quarto compartilhado",
      "hotelFilter": "ht_id%3D203", "hospOrigem": "estimado",
      "meals": { "cafe": 12, "almoco": 30, "jantar": 24 },
      "mealsWhat": "padaria, prato feito e lanche à noite",
      "transit": { "busRides": 4, "busFare": 4.50, "uberRides": 1, "uberFare": 7.00,
                   "airportRides": 2, "airportFare": 23.00 },
      "transitWhat": "4 embarques de ônibus/metrô + 1 Uber noturno dividido entre 4" }
  ]
}
```

- `low` / `high`: faixa típica da passagem **ida e volta** em BRL.
- `mid`: o valor que o painel usa. **Obrigatório** — não é o meio da faixa, e calcular
  `(low+high)/2` inflaria a conta.
- `barato`: menor preço já encontrado na rota, exibido no bilhete.
- `origem`: `datado` (preço para as datas do evento) · `observado` (estatística da rota) ·
  `estimado` (sem lastro). Define o selo de procedência na interface.
- `searchIata`: código usado nos links de busca — metropolitano onde existe (SAO, RIO, BHZ).
- `host: true`: federação anfitriã (PE) — zera o custo aéreo.
- Os cenários são descritos por **valor unitário**, não por total fechado. `normalize()`
  multiplica pelas noites/dias do `EVENT`, e é isso que permite mostrar a memória de
  cálculo na tela. Se você mandar `hosp`, `alim` ou `interno` já fechados, eles vencem.
- As chaves são ASCII de propósito (`regiao`, `hosp`, `alim`) para facilitar a serialização.

## Como os custos são calculados

**Passagem e hospedagem** vêm de busca externa, e cada linha do cenário traz o link já
preenchido com origem, destino e datas: Google Flights e Kayak para o voo, Booking para a
hospedagem (filtrado por `hotelFilter` — hostel, 3★ ou 4★).

**Alimentação** — três refeições por dia, sem desconto por grupo:

```
alimentação = (café + almoço + jantar) × 6 dias
```

| Cenário | Café | Almoço | Jantar | Por dia | Total |
|---|---|---|---|---|---|
| Econômico | 12 | 30 | 24 | 66 | 396 |
| Intermediário | 18 | 45 | 36 | 99 | 594 |
| Conforto | 30 | 65 | 65 | 160 | 960 |

O almoço vem do índice Abrasel do prato feito; café e jantar são estimativa.

**Transporte interno** — deslocamentos diários entre Boa Viagem e a sede:

```
transporte = (ônibus × tarifa + Uber × preço) × 6 dias × fator da sede
            + traslado do aeroporto (ida e volta)
```

O **traslado do aeroporto** (REC ↔ Boa Viagem, R$ 23 por corrida) é cobrado uma vez na
viagem e fica **fora** do fator da sede: esse trajeto é o mesmo independente de onde o
evento aconteça.

| Cenário | Composição diária | Por dia | Traslado | Total (Geraldão) |
|---|---|---|---|---|
| Econômico | 4 × R$ 4,50 (ônibus) + 1 × R$ 7 (Uber dividido) | 25,00 | 46 | 196 |
| Intermediário | 2 × R$ 4,50 (ônibus) + 1 × R$ 24 (Uber) | 33,00 | 46 | 244 |
| Conforto | 2 × R$ 34 (Uber) | 68,00 | 46 | 454 |

O **fator da sede** sai de `1 + (km ÷ 6 − 1) × 0,30`, com o Geraldão (~6 km) como
referência. O amortecimento de 0,30 existe porque dobrar a distância não dobra o gasto:
parte do trajeto é a mesma tarifa de ônibus, e a corrida de app cresce menos que
proporcionalmente à distância.

## Regra de sazonalidade

Com **8 semanas ou mais** de antecedência, aplica-se a tarifa de referência. Abaixo disso,
incide um acréscimo progressivo que chega a **+80%** na véspera (`fareMultiplier()`).

## Datas do evento

As datas oficiais do ENEJ 27 ainda não foram divulgadas. O painel usa uma **hipótese de
trabalho** (25 a 30 de agosto de 2027, mesma janela do ENEJ 26), centralizada na constante
`EVENT`. Ajuste ali quando o edital sair e a interface inteira acompanha — contagem
regressiva, rótulos e cenários.

## Reativando o ingresso

Quando os lotes forem divulgados:

```js
const TICKET = { enabled: true, price: 530.72, installments: 12 };
```

Isso reinsere a linha do ingresso em todos os cenários e no total por pessoa.

## Rodando localmente

É um arquivo único, sem build e sem dependências:

```bash
python -m http.server 8000
# abra http://localhost:8000
```

Abrir o `index.html` direto pelo `file://` também funciona — a chamada à API falha por CORS
e o painel cai no payload simulado, que é o comportamento esperado.

## Stack

HTML + CSS + JavaScript puro, arquivo único. Tipografia: Outfit (display), IBM Plex Sans
(corpo) e IBM Plex Mono (valores e códigos IATA). Tema claro e escuro automáticos.
