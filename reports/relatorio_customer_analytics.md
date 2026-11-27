# Relatório de Customer Analytics — RFM, Recorrência e Concentração

## 1. Cobertura de Identificação de Clientes

Os registros válidos sem `CustomerID` foram preservados nas análises comerciais gerais e excluídos exclusivamente das etapas que exigem identificação individual:

| Métrica | Clientes identificados | Sem `CustomerID` | Total Base V2 |
|---|---:|---:|---:|
| Linhas de transação | 392.692 | 132.185 | 524.877 |
| Pedidos distintos | 18.532 | 1.427 | 19.959 |
| Faturamento observado (GBP) | £ 8.887.208,89 (83,60%) | £ 1.743.839,85 (16,40%) | £ 10.631.048,74 (100,00%) |

- **Clientes identificados distintos:** 4.338
- **Clientes presentes em mais de um país:** 8 (`12370, 12394, 12417, 12422, 12429, 12431, 12455, 12457`)

## 2. Metodologia RFM e Regras Transparentes de Segmentação

- **Data de referência RFM utilizada nesta execução:** `2011-12-10` (última compra válida observada na entrada: `2011-12-09 12:50:00`; sem uso de `datetime.now()`).
- **Recency (Recência):** dias corridos entre `2011-12-10` e a data normalizada da última compra válida observada.
- **Frequency (Frequência):** quantidade de pedidos de venda distintos (`InvoiceNo`) do cliente no período.
- **Monetary (Valor Monetário):** faturamento bruto acumulado das vendas válidas observadas (não equivale a lucro nem a Customer Lifetime Value preditivo).

### Ordem de Prioridade dos Segmentos (Mutuamente Exclusivos)

1. **Alto valor e recorrentes:** `frequência >= 5`, `valor monetário >= £ 1.500,00` e `recência <= 90 dias`.
2. **Recorrentes recentes:** `frequência >= 2` e `recência <= 90 dias`.
3. **Compra única recente:** `frequência == 1` e `recência <= 90 dias`.
4. **Recorrentes há mais tempo sem compras:** `frequência >= 2` e `recência > 90 dias`.
5. **Compra única há mais tempo sem compras:** `frequência == 1` e `recência > 90 dias`.

> **Justificativa e ressalva metodológica:** os cortes foram ancorados na distribuição observada dos 4.338 clientes do dataset oficial UCI (quartil superior próximo de 5 pedidos e £ 1.660,60; janela trimestral de 90 dias) e **não devem ser interpretados como padrões universais de mercado**. Além disso, estar há mais de 90 dias sem compras observadas **não comprova** que o cliente foi definitivamente perdido, especialmente em perfis atacadistas ou sazonais.

## 3. Desempenho por Segmento RFM

| Segmento RFM | Clientes | % Clientes | Faturamento | % Receita Ident. | Ticket Médio | Freq. Média | Recência Média |
|---|---:|---:|---:|---:|---:|---:|---:|
| Alto valor e recorrentes | 840 | 19,36% | £ 5.954.738,26 | 67,00% | £ 564,54 | 12.56 | 20.4 dias |
| Recorrentes recentes | 1.403 | 32,34% | £ 1.642.178,58 | 18,48% | £ 353,16 | 3.31 | 33.2 dias |
| Compra única recente | 646 | 14,89% | £ 257.749,76 | 2,90% | £ 398,99 | 1.00 | 46.0 dias |
| Recorrentes há mais tempo sem compras | 602 | 13,88% | £ 676.302,49 | 7,61% | £ 367,36 | 3.06 | 174.8 dias |
| Compra única há mais tempo sem compras | 847 | 19,53% | £ 356.239,80 | 4,01% | £ 420,59 | 1.00 | 242.1 dias |

## 4. Recorrência Observada no Período e Efeito de Janela

- **Clientes com 1 pedido:** 1.493 (34,42%) — faturamento de £ 613.989,56.
- **Clientes recorrentes (>= 2 pedidos):** 2.845 (**65,58%**) — faturamento de £ 8.273.219,33.
- **Cuidado com a janela de observação:** 968 clientes tiveram sua primeira compra observada nos últimos 90 dias em relação a `2011-12-10` (dos quais 646 ainda possuem 1 pedido). Como tiveram menos tempo disponível para recomprar, **recorrência observada no recorte não equivale a retenção de longo prazo**, e a primeira compra presente na base não corresponde necessariamente à primeira compra histórica da vida do cliente.

### Distribuição de Frequência

| Faixa de frequência | Clientes | % Clientes | Faturamento | % Receita Identificada |
|---|---:|---:|---:|---:|
| 1 pedido | 1.493 | 34,42% | £ 613.989,56 | 6,91% |
| 2 pedidos | 835 | 19,25% | £ 737.463,75 | 8,30% |
| 3 a 4 pedidos | 896 | 20,65% | £ 1.203.286,27 | 13,54% |
| 5 a 9 pedidos | 723 | 16,67% | £ 1.772.167,53 | 19,94% |
| 10 ou mais pedidos | 391 | 9,01% | £ 4.560.301,78 | 51,31% |

## 5. Concentração Comercial

- **Top 10 clientes:** £ 1.537.659,21 (17,30% da receita identificada | 14,46% da receita total V2).
- **Top 50 clientes:** £ 2.959.341,54 (33,30% da receita identificada | 27,84% da receita total V2).
- **Top 100 clientes:** £ 3.608.854,55 (40,61% da receita identificada | 33,95% da receita total V2).
- **Top 10 produtos por faturamento:** £ 1.153.320,83 (10,85% da receita total V2).
- **País líder (`United Kingdom`):** £ 8.990.682,03 (84,57% da receita total V2); Top 5 países somam 94,04%.

## 6. Top 10 Clientes por Faturamento Acumulado

| Rank | CustomerID | País Principal | Segmento RFM | Pedidos | Unidades | Faturamento | Ticket Médio | Recência |
|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | `14646` | Netherlands | Alto valor e recorrentes | 73 | 196.915 | £ 280.206,02 | £ 3.838,44 | 2 d |
| 2 | `18102` | United Kingdom | Alto valor e recorrentes | 60 | 64.124 | £ 259.657,30 | £ 4.327,62 | 1 d |
| 3 | `17450` | United Kingdom | Alto valor e recorrentes | 46 | 69.973 | £ 194.390,79 | £ 4.225,89 | 9 d |
| 4 | `16446` | United Kingdom | Recorrentes recentes | 2 | 80.997 | £ 168.472,50 | £ 84.236,25 | 1 d |
| 5 | `14911` | EIRE | Alto valor e recorrentes | 201 | 80.240 | £ 143.711,17 | £ 714,98 | 2 d |
| 6 | `12415` | Australia | Alto valor e recorrentes | 21 | 77.374 | £ 124.914,53 | £ 5.948,31 | 25 d |
| 7 | `14156` | EIRE | Alto valor e recorrentes | 55 | 57.768 | £ 117.210,08 | £ 2.131,09 | 10 d |
| 8 | `17511` | United Kingdom | Alto valor e recorrentes | 31 | 64.549 | £ 91.062,38 | £ 2.937,50 | 3 d |
| 9 | `16029` | United Kingdom | Alto valor e recorrentes | 63 | 40.108 | £ 80.850,84 | £ 1.283,35 | 39 d |
| 10 | `12346` | United Kingdom | Compra única há mais tempo sem compras | 1 | 74.215 | £ 77.183,60 | £ 77.183,60 | 326 d |

> **Nota de auditoria sobre casos atípicos no Top 10:** os clientes `16446` (pedido `581483`) e `12346` (pedido `541431`) figuram no Top 10 devido a pedidos atípicos de altíssimo volume com notas de cancelamento compatíveis emitidas minutos depois. Veja o impacto completo no `relatorio_sensibilidade.md`.

## 7. Hipóteses Comerciais para Investigação

As frentes abaixo são **hipóteses para investigação comercial**, e não resultados comprovados ou promessas de retorno:

1. **Gestão de contas-chave (`Alto valor e recorrentes`):** investigar padrões de reposição, condições de atendimento e dependência de receita dos maiores clientes recorrentes (sempre considerando a sensibilidade a eventuais pedidos atípicos).
2. **Estímulo à segunda compra (`Compra única recente`):** investigar o intervalo típico entre 1º e 2º pedido entre clientes que entraram recentemente e testar comunicações de acompanhamento pós-compra.
3. **Diagnóstico de reativação (`Recorrentes há mais tempo sem compras`):** investigar se a ausência de compras nos últimos 90 dias decorre de sazonalidade, ruptura de portfólio ou perda real de relacionamento.
4. **Qualidade do cadastro (16,40% da receita sem `CustomerID`):** investigar por que parte do faturamento ocorre sem identificação de cliente (ex.: canal guest/PDV) para avaliar o ganho de visibilidade analítica.
