# Relatório Executivo — Online Retail Customer Analytics V2

- **Escopo:** Dataset oficial UCI Online Retail (SHA-256 verificado) | **Data de referência RFM:** `2011-12-10`

## 1. Panorama Geral e Comparação V1 vs V2

| Indicador | Regra V1 (reproduzida) | Base Principal V2 | Observação |
|---|---:|---:|---|
| Faturamento de vendas positivas | £ 10.642.110,80 (`10642110.804`) | **£ 10.631.048,74** (`10631048.744`) | V2 exclui o lançamento contábil `A563185` (`Adjust bad debt`, £ 11.062,06) |
| Pedidos válidos distintos | 19.960 | **19.959** | 0 conflitos de cliente ou país por pedido |
| Ticket médio geral | £ 533,17 (ref. histórica V1 UCI: £ 533,17) | **£ 532,64** | Calculado como `faturamento total / pedidos distintos` |
| Unidades vendidas | 5.572.420 | **5.572.419** | Preservado outlier `581483`, avaliado em sensibilidade |
| Clientes identificados | 4.338 | **4.338** | 100% classificados em 5 segmentos RFM mutuamente exclusivos |
| Reconciliação matemática | Não existia na V1 | **18/18 aprovadas** | 0 divergências entre camadas |

## 2. Respostas às Perguntas de Negócio (Execução Atual)

1. **Clientes de maior valor histórico:** líder absoluto é o cliente `14646` (Netherlands), com £ 280.206,02 em 73 pedido(s). Os 10 maiores clientes concentram **17,30%** da receita identificada e os 50 maiores concentram **33,30%**.
2. **Recorrência observada:** **2.845** clientes (65,58%) realizaram 2 ou mais pedidos no período, respondendo por £ 8.273.219,33, enquanto 1.493 (34,42%) realizaram apenas 1 pedido.
3. **Atividade recente vs afastamento:** considerando a data de referência RFM `2011-12-10`, o segmento **Alto valor e recorrentes** reúne 840 clientes (19,36%) que concentram **67,00%** da receita identificada. Já os grupos sem compras nos últimos 90 dias somam 1.449 clientes (não classificados automaticamente como perdidos definitivos).
4. **Receita sem identificação de cliente:** £ 1.743.839,85 (16,40% da receita V2) correspondem a 1.427 pedido(s) sem `CustomerID`, mantidos nas visões gerais.
5. **Países com maior volume comercial:** **United Kingdom** lidera com 84,57% da receita total; os 5 maiores mercados concentram 94,04%.
6. **Alerta de amostra pequena em ticket médio por país:** países como `Singapore, Lebanon, Brazil, Israel, RSA, Greece` apresentam ticket médio elevado com menos de 10 pedidos (ex.: `Singapore` tem £ 3.039,90 em apenas 7 pedido(s) — além de £ -12.158,90 em cancelamentos), inviabilizando comparação direta com mercados robustos.
7. **Produtos de maior demanda e influência de outliers:** os maiores itens em receita nesta execução são `DOT` (`DOTCOM POSTAGE`, £ 206.248,77), `22423` (`REGENCY CAKESTAND 3 TIER`, £ 174.156,54), `23843` (`PAPER CRAFT , LITTLE BIRDIE`, £ 168.469,60). Na sensibilidade, remover `581483` e `541431` altera a receita em £ -245.653,20 (-2,31%) e desloca o topo de volume consolidado por `StockCode` para `22197 - POPCORN HOLDER` (56.898 un.).
8. **Influência dos cancelamentos:** foram identificadas 3.836 nota(s) com prefixo `C`, somando **£ -893.979,73** (deduplicado), equivalente a **8,41%** das vendas positivas V2. O **saldo monetário observado** é de **£ 9.737.069,01** (valor descritivo que **não** equivale a faturamento líquido contábil certificado).
9. **Ações comerciais para investigação:** detalhadas na seção 7 abaixo, sempre como hipóteses analíticas e nunca como retorno financeiro comprovado.

## 3. Top 10 Países por Faturamento

| País | Pedidos | Clientes Ident. | Faturamento | % Receita | Ticket Médio | Porte Amostral |
|---|---:|---:|---:|---:|---:|---|
| United Kingdom | 18.018 | 3.920 | £ 8.990.682,03 | 84,57% | £ 498,98 | Amostra robusta (>= 50 pedidos) |
| Netherlands | 94 | 9 | £ 285.446,34 | 2,69% | £ 3.036,66 | Amostra robusta (>= 50 pedidos) |
| EIRE | 288 | 3 | £ 283.140,52 | 2,66% | £ 983,13 | Amostra robusta (>= 50 pedidos) |
| Germany | 457 | 94 | £ 228.678,40 | 2,15% | £ 500,39 | Amostra robusta (>= 50 pedidos) |
| France | 392 | 87 | £ 209.625,37 | 1,97% | £ 534,76 | Amostra robusta (>= 50 pedidos) |
| Australia | 57 | 9 | £ 138.453,81 | 1,30% | £ 2.429,01 | Amostra robusta (>= 50 pedidos) |
| Spain | 90 | 30 | £ 61.558,56 | 0,58% | £ 683,98 | Amostra robusta (>= 50 pedidos) |
| Switzerland | 54 | 21 | £ 57.067,60 | 0,54% | £ 1.056,81 | Amostra robusta (>= 50 pedidos) |
| Belgium | 98 | 25 | £ 41.196,34 | 0,39% | £ 420,37 | Amostra robusta (>= 50 pedidos) |
| Sweden | 36 | 8 | £ 38.367,83 | 0,36% | £ 1.065,77 | Amostra moderada (10 a 49 pedidos) |

> **Atenção:** a soma de `Clientes Ident.` por país (4.346) frente ao total global (4.338) reflete 8 cliente(s) que compraram em mais de um país.

## 4. Top 10 Produtos/Códigos por Faturamento

| Rank | StockCode | Descrição Principal | Unidades | Faturamento | Pedidos | Tipo |
|---:|---|---|---:|---:|---:|---|
| 1 | `DOT` | DOTCOM POSTAGE | 706 | £ 206.248,77 | 706 | Operacional |
| 2 | `22423` | REGENCY CAKESTAND 3 TIER | 13.851 | £ 174.156,54 | 1.988 | Mercadoria |
| 3 | `23843` | PAPER CRAFT , LITTLE BIRDIE | 80.995 | £ 168.469,60 | 1 | Mercadoria |
| 4 | `85123A` | WHITE HANGING HEART T-LIGHT HOLDER | 37.933 | £ 106.415,23 | 2.265 | Mercadoria |
| 5 | `47566` | PARTY BUNTING | 18.283 | £ 99.445,23 | 1.685 | Mercadoria |
| 6 | `85099B` | JUMBO BAG RED RETROSPOT | 48.371 | £ 94.159,81 | 2.089 | Mercadoria |
| 7 | `23166` | MEDIUM CERAMIC TOP STORAGE JAR | 78.033 | £ 81.700,92 | 247 | Mercadoria |
| 8 | `POST` | POSTAGE | 3.150 | £ 78.101,88 | 1.126 | Operacional |
| 9 | `M` | Manual | 6.985 | £ 77.752,82 | 290 | Operacional |
| 10 | `23084` | RABBIT NIGHT LIGHT | 30.739 | £ 66.870,03 | 994 | Mercadoria |

## 5. Evolução Mensal

| Mês (`YYYY-MM`) | Período Incompleto? | Pedidos | Unidades | Faturamento | Ticket Médio |
|---|---|---:|---:|---:|---:|
| `2010-12` | Não | 1.559 | 358.019 | £ 821.452,73 | £ 526,91 |
| `2011-01` | Não | 1.086 | 387.099 | £ 689.811,61 | £ 635,19 |
| `2011-02` | Não | 1.100 | 282.934 | £ 522.545,56 | £ 475,04 |
| `2011-03` | Não | 1.454 | 376.599 | £ 716.215,26 | £ 492,58 |
| `2011-04` | Não | 1.246 | 307.953 | £ 536.968,49 | £ 430,95 |
| `2011-05` | Não | 1.681 | 395.001 | £ 769.296,61 | £ 457,64 |
| `2011-06` | Não | 1.533 | 388.511 | £ 760.547,01 | £ 496,12 |
| `2011-07` | Não | 1.475 | 399.693 | £ 718.076,12 | £ 486,83 |
| `2011-08` | Não | 1.360 | 421.019 | £ 746.779,32 | £ 549,10 |
| `2011-09` | Não | 1.837 | 569.573 | £ 1.056.435,19 | £ 575,09 |
| `2011-10` | Não | 2.040 | 621.029 | £ 1.151.263,73 | £ 564,34 |
| `2011-11` | Não | 2.769 | 751.377 | £ 1.503.866,78 | £ 543,11 |
| `2011-12` | Sim (parcial) | 819 | 313.612 | £ 637.790,33 | £ 778,74 |

> **Contexto temporal obrigatório:** `2011-12` cobre apenas 9 dia(s) (`2011-12-01 08:33:00` até `2011-12-09 12:50:00`) e **não deve ser comparado diretamente** a meses completos sem normalização de janela.

## 6. Top 5 Códigos em Valor Absoluto de Cancelamentos (Deduplicados)

| StockCode | Descrição Principal | Notas `C` | Unidades Canceladas | Valor Cancelado |
|---|---|---:|---:|---:|
| `AMAZONFEE` | AMAZON FEE | 32 | -32 | £ -235.281,59 |
| `23843` | PAPER CRAFT , LITTLE BIRDIE | 1 | -80.995 | £ -168.469,60 |
| `M` | Manual | 223 | -4.066 | £ -146.784,46 |
| `23166` | MEDIUM CERAMIC TOP STORAGE JAR | 10 | -74.494 | £ -77.479,64 |
| `POST` | POSTAGE | 124 | -147 | £ -11.871,24 |

## 7. Limitações e Frentes de Investigação Comercial

- **Limitações da fonte:** ausência de custos (impede cálculo de margem ou lucro), ausência de chave de vínculo entre notas `C` e pedidos originais, ausência de `LineItemID`, 24,93% das linhas brutas sem `CustomerID` e `2011-12` incompleto.
- **Frentes sugeridas para investigação (não comprovadas em produção):**
  1. Revisão operacional de grandes pedidos e principais códigos cancelados nesta entrada (`AMAZONFEE`, `23843`, `M`, `23166`).
  2. Programas de acompanhamento de contas recorrentes de alto valor e entendimento de ciclo de recompra de clientes com compra única recente.
  3. Investigação da causa de vendas sem `CustomerID` para ampliar cobertura futura de CRM (quando aplicável).
