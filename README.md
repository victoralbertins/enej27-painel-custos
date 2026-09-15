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

## Plugando o backend (Python / BigQuery)

As tarifas não são mais estáticas. Toda a camada de dados fica em `loadDynamicData()`:

1. **Endpoint** — troque a constante no topo do `<script>`:
   ```js
   const API_ENDPOINT = "https://api.exemplo.com/cotacoes-enej27"; // <<< TROQUE AQUI
   ```
2. **Autenticação** — headers em `API_HEADERS`. Como o arquivo é público, não coloque
   chave secreta aqui: use uma API pública de leitura ou um proxy que injete a credencial.
3. **CORS** — o backend precisa responder com `Access-Control-Allow-Origin` para o domínio
   onde o painel estiver hospedado.
4. **Timeout** — `API_TIMEOUT_MS` (6s) aborta a chamada via `AbortController`.

Enquanto a API não existir, `loadDynamicData()` cai automaticamente no payload de
`simulatedPayload()` e o painel continua funcionando. O selo no rodapé mostra qual fonte
está em uso (`API` ou `payload simulado`).

### Contrato do JSON

Sua query no BigQuery deve devolver exatamente este shape:

```json
{
  "meta":  { "moeda": "BRL", "atualizado_em": "2026-09-14", "fonte": "bigquery", "destino": "REC" },
  "voos":  [
    { "uf": "SP", "capital": "São Paulo", "iata": "GRU", "regiao": "Sudeste",
      "low": 600, "high": 920, "host": false }
  ],
  "tiers": [
    { "key": "econ", "name": "Econômico", "desc": "...",
      "hosp": 350, "alim": 360, "interno": 100 }
  ]
}
```

- `low` / `high`: faixa da passagem **ida e volta** em BRL, com 8+ semanas de antecedência.
- `host: true`: federação anfitriã (PE) — zera o custo aéreo.
- `hosp`: 5 pernoites · `alim` e `interno`: 6 dias. O `interno` ainda é multiplicado pelo
  fator da sede escolhida.
- As chaves são ASCII de propósito (`regiao`, `hosp`, `alim`) para facilitar a serialização.

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
