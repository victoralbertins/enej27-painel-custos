# Fontes dos valores do painel

Inventário completo de cada número do painel: o que tem lastro verificável, o que é
estimativa, e o que é hipótese de trabalho. Pesquisa feita em **15 de setembro de 2026**.

A regra: **se não está na primeira tabela, é estimativa.** O painel marca esses casos em
âmbar; o que tem cotação real aparece em verde.

---

## 1. Números com fonte verificável

| Valor no painel | Número | Fonte | Consultado |
|---|---|---|---|
| Passagem SP → REC (ida e volta) | R$ 1.154 | [Kayak](https://www.kayak.com.br/flights/SAO-REC/2027-08-25/2027-08-30) — conferido por Victor | 14/09/2026 |
| Âncora de nível das demais rotas | R$ 632,53 por trecho (mai/2026) | [ANAC — dados tarifários mensais](https://www.gov.br/anac/pt-br/noticias/2026/anac-publica-dados-tarifarios-do-mes-de-maio-de-2026) | 15/09/2026 |
| Tarifa de ônibus urbano (Anel A) | R$ 4,50 | [Grande Recife Consórcio, via Folha PE](https://www.folhape.com.br/noticias/aumento-da-passagem-de-onibus-no-grande-recife-e-homologado-e-anel-a/463122/) — homologado, vigente desde 01/02/2026 | 15/09/2026 |
| Uber REC ↔ Boa Viagem | R$ 23 (5,71 km, ~19 min) | [Uber — página oficial de estimativa da rota](https://www.uber.com/global/en/r/routes/recife-pe-br-to-rec/) | 15/09/2026 |
| Prato feito (almoço econômico) | R$ 30–31,90 | [Abrasel, via Mercado&Consumo](https://mercadoeconsumo.com.br/07/05/2026/foodservice/alimentacao-fora-de-casa-fica-mais-cara-e-prato-feito-atinge-media-de-r-3027/) — Nordeste ~R$ 30 | 15/09/2026 |
| Diária média em Recife | R$ 280 o quarto duplo | [Dicas de Viagem](https://www.dicasdeviagem.com/hoteis-em-recife/) e [Viaje na Viagem](https://www.viajenaviagem.com/destino/recife/onde-ficar/) | 15/09/2026 |
| Ônibus João Pessoa → Recife | a partir de R$ 27/trecho | [ClickBus](https://www.clickbus.com.br/onibus/joao-pessoa-pb) | 15/09/2026 |
| Ônibus Recife → Natal | a partir de R$ 74/trecho | [CheckMyBus](https://www.checkmybus.com/recife/natal) | 15/09/2026 |
| Ônibus Recife → Maceió | a partir de R$ 99,90/trecho | [CheckMyBus](https://www.checkmybus.com/joao-pessoa/maceio) | 15/09/2026 |
| Endereço do Geraldão | Av. Mascarenhas de Moraes, Imbiribeira | [Prefeitura do Recife](https://www2.recife.pe.gov.br/pagina/ginasio-de-esportes-geraldo-magalhaes-geraldao) — capacidade 13 mil | 15/09/2026 |
| Cecon — distância do aeroporto | 12 km | [Centro de Convenções de Pernambuco](http://www.cecon.pe.gov.br/o-cecon-pe/) | 15/09/2026 |
| Recife Expo Center — localização | ~20 min do aeroporto e de Boa Viagem | [Recife Expo Center](https://recifeexpocenter.com.br/) | 15/09/2026 |
| Tendência da hotelaria em Recife | diária média +17,1% (jan/26), +10,1% (jun/26) | [FOHB / InFOHB, via Panrotas](https://www.panrotas.com.br/hotelaria/mercado/2026/02/hotelaria-cresce-em-janeiro-e-revpar-avanca-105-no-brasil_226015.html) e [Revista Hotéis](https://revistahoteis.com.br/infohb-apresenta-dados-da-hotelaria-referentes-ao-mes-de-junho/) | 15/09/2026 |

---

## 2. Estimativas sem fonte — use com ceticismo

Estes números **não** foram verificados. São julgamento de mercado, e o painel os marca
como estimativa.

| Valor | Quanto | Por que não tem fonte |
|---|---|---|
| Tabela base das 25 rotas não observadas | R$ 493 a R$ 3.099 | Não existe cotação pública por rota para agosto de 2027. O nível está ancorado na ANAC, mas a **posição relativa entre rotas** é julgamento meu. |
| Diária de hostel | R$ 85 | Hostelworld e Booking só mostram preço após consulta com datas; não é indexável. |
| Diária 4★ na orla | R$ 200 | Derivado do padrão de mercado, não de cotação. |
| Café da manhã | R$ 12 / 18 / 30 | Não há índice publicado por refeição isolada. |
| Jantar | R$ 24 / 36 / 65 | Idem. Só o almoço (prato feito) tem índice Abrasel. |
| Corrida de Uber intraurbana | R$ 7 / 24 / 34 | Ancorada na tarifa real REC↔Boa Viagem (R$ 23 para 5,71 km), mas extrapolada para outros trajetos. |
| Distâncias Boa Viagem → sedes | 6, 13, 13, 14 km | Aproximações. Só o Cecon tem distância publicada (12 km do aeroporto). |
| Fator de deslocamento da sede | `1 + (km÷6−1) × 0,30` | Heurística minha. O amortecimento de 0,30 não tem base empírica. |
| Número de deslocamentos por dia | 4 / 3 / 2 | Premissa de comportamento, não medição. |

---

## 3. Hipóteses de trabalho

| Item | Adotado | Situação |
|---|---|---|
| Datas do ENEJ 27 | 25–30/08/2027 | **Não divulgadas.** O [site oficial](https://enej.brasiljunior.org.br/) ainda mostra o ENEJ'26. A janela de agosto replica a do ENEJ 26. |
| Sede | 4 candidatas simuláveis | Não definida — por isso é um seletor. |
| Estadia | 5 pernoites / 6 dias | Herdado do painel do ENEJ 26. |
| Ingresso | fora do cálculo | Lotes não divulgados. |

Herdado do código original do ENEJ 26, não verificado por mim: a regra de sazonalidade
(8+ semanas = tarifa de referência, até +80% na véspera).

---

## 4. Como a calibração das passagens funciona

O modelo base é estimativa. Duas âncoras o corrigem:

**Hoje (menos de 5 observações):** o nível da tabela é ancorado na média oficial da ANAC.
A média ida e volta da tabela fica em R$ 1.334, ou **+5% sobre a média nacional** de
R$ 1.265 (2 × R$ 632,53) — coerente, já que todas as rotas terminam em Recife, mais
distante que a média dos pares nacionais.

**Uma correção de método:** a primeira versão calibrava a tabela inteira pela razão de uma
única rota (SP: 1154 ÷ 760 = 1,52). Isso superestimava — SP-REC é rota-tronco e custa
*menos* que a média nacional (−9%), então o fator dela não descreve as outras. Com a
âncora da ANAC, o fator caiu para **1,32** e a tabela deixou de ficar 20% acima do mercado.

**A partir de 5 cotações reais,** a calibração troca a âncora da ANAC pela razão média
observada, que a essa altura descreve melhor que a média nacional. É o que o pipeline da
Amadeus alimenta semanalmente.

Rota com cotação real sempre vale o preço real, em qualquer regime.

---

## 5. O que fecharia as lacunas

- **Passagens e hotéis:** o [pipeline da Amadeus](README.md#cotações-automáticas) —
  falta você cadastrar as credenciais.
- **Alimentação e transporte intraurbano:** não existe API. O que resolve é alguém que
  more em Recife conferir. A FEJEPE é a fonte certa.
- **Distâncias das sedes:** medir no Google Maps quando a sede for definida.
