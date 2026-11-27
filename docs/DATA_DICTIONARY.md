# Dicionário de Dados — Online Retail Customer Analytics V2

## 1. Base Bruta (`Online Retail.xlsx`)

Granularidade: **uma linha por lançamento de item em fatura** (sem chave única de linha `LineItemID`).

| Coluna original | Tipo no Excel / Pandas | Nulos permitidos? | Descrição e observações de auditoria |
|---|---|---|---|
| `InvoiceNo` | Misto (`int` e `str`) / `object` | Não (`0` nulos) | Código da fatura (6 dígitos para faturas padrão; prefixo `C` para cancelamentos; prefixo `A` para 3 ajustes contábeis `Adjust bad debt`). **Não é chave única de linha.** |
| `StockCode` | Misto (`int` e `str`) / `object` | Não (`0` nulos) | Código do item/produto. Possui 110 variações de caixa (`85123A`/`85123a`, `M`/`m`) e códigos operacionais não-mercadoria (`DOT`, `POST`, `M`, `AMAZONFEE`, `B`, `C2`, `BANK CHARGES`, `S`, `PADS`, `CRUK`, `D`, `gift_0001_*`). |
| `Description` | Texto / `object` | Sim (`1.454` nulos) | Descrição textual do item ou anotação operacional (`damaged`, `check`, `?`). `220` códigos de produto possuem mais de uma descrição na base positiva. |
| `Quantity` | Inteiro / `int64` | Não (`0` nulos) | Quantidade de unidades na linha. Positiva em vendas; negativa em cancelamentos (`C`) e em `1.336` ajustes de estoque sem prefixo `C` (todos com `UnitPrice == 0`). |
| `InvoiceDate` | Data/hora / `datetime64` | Não (`0` nulos) | Timestamp da fatura (`2010-12-01 08:26:00` a `2011-12-09 12:50:00`). `42` pedidos válidos possuem 2 timestamps com 60s de diferença no mesmo dia. |
| `UnitPrice` | Numérico / `float64` | Não (`0` nulos) | Preço unitário em libras esterlinas (`GBP`). Contém `4` registros com `0.001` (3 casas decimais), valores `0.00` e `2` negativos em ajustes `A`. |
| `CustomerID` | Numérico / `float64` | Sim (`135.080` nulos — `24,93%`) | Identificador inteiro do cliente (armazenado como float pelo Pandas devido aos nulos; `0` valores com parte fracionária). Padronizado como texto inteiro sem `.0` na V2. |
| `Country` | Texto / `str` | Não (`0` nulos) | País associado ao pedido (`38` países distintos na base V2). `8` clientes compraram em 2 países diferentes. |

---

## 2. Base Transacional Limpa V2 (`df_sales_v2`)

Granularidade: **uma linha por item de venda positivo válido, após remoção de duplicatas exatas** (`524.877` linhas).

| Coluna derivada | Tipo | Fórmula / Regra |
|---|---|---|
| `invoice_no` | `str` | `InvoiceNo` sem espaços e em maiúsculas (`str.strip().upper()`). |
| `stock_code_original` | `str` | `StockCode` sem espaços preservando caixa original. |
| `stock_code` | `str` | `StockCode` sem espaços em maiúsculas (chave de produto na V2). |
| `description` | `str \| None` | `Description` sem espaços nas extremidades. |
| `quantity` | `int` | Quantidade inteira estritamente positiva (`> 0`). |
| `unit_price` | `float` | Preço unitário estritamente positivo (`> 0`). |
| `customer_id` | `str \| None` | `CustomerID` padronizado como texto inteiro (`"14646"`) ou `None` quando ausente. |
| `country` | `str` | País limpo. |
| `is_non_merchandise_code` | `bool` | `True` se `stock_code` pertence à lista de códigos operacionais (`NON_MERCHANDISE_STOCK_CODES`). |
| `valor_linha` | `float` | `quantity * unit_price`. |
| `valor_linha_decimal` | `Decimal` | `Decimal(str(quantity)) * Decimal(str(unit_price))` (sem arredondamento antecipado). |
| `ano_mes` | `str` | `InvoiceDate` formatado como `YYYY-MM`. |
| `categoria_registro` | `str` | Categoria mutuamente exclusiva atribuída na triagem (`venda_positiva_valida`). |

---

## 3. Base de Pedidos (`df_orders_v2`)

Granularidade: **uma linha por pedido válido (`invoice_no`)** (`19.959` pedidos).

| Coluna | Descrição |
|---|---|
| `invoice_no` | Chave única do pedido. |
| `customer_id` | Cliente do pedido (após validar 0 conflitos no mesmo `invoice_no`); `None` quando não identificado. |
| `country` | País do pedido (após validar 0 conflitos no mesmo `invoice_no`). |
| `data_pedido` | `min(invoice_date)` do pedido (horário de abertura determinístico). |
| `data_pedido_fim` | `max(invoice_date)` do pedido. |
| `timestamps_distintos` | Quantidade de timestamps distintos dentro do mesmo `invoice_no`. |
| `faturamento_pedido` / `faturamento_pedido_decimal` | Soma dos valores das linhas do pedido em `float` e `Decimal`. |
| `quantidade_unidades` | Soma das quantidades do pedido. |
| `produtos_distintos` | Contagem de `stock_code` distintos no pedido (`nunique`). |
| `linhas_transacao` | Quantidade de linhas de transação pertencentes ao pedido. |
| `ano_mes` | Mês de referência do pedido (`YYYY-MM`). |
| `cliente_identificado` | Booleano indicando presença de `customer_id`. |

---

## 4. Base de Clientes e RFM (`resumo_clientes.csv` / `segmentacao_rfm.csv`)

Granularidade: **uma linha por cliente identificado (`customer_id`)** (`4.338` clientes).

| Coluna | Descrição |
|---|---|
| `customer_id` | Identificador único do cliente. |
| `pais_principal` | País com maior número de pedidos do cliente (desempate por faturamento e ordem alfabética). |
| `paises_distintos` | Quantidade de países em que o cliente comprou (`> 1` para 8 clientes). |
| `faturamento_acumulado_decimal` / `valor_monetario` | Receita bruta acumulada do cliente em vendas válidas V2 (`M` do RFM). |
| `pedidos_distintos` / `frequencia` | Quantidade de `invoice_no` distintos do cliente (`F` do RFM). |
| `quantidade_unidades` | Soma de unidades compradas pelo cliente. |
| `produtos_distintos` | Quantidade de `stock_code` distintos comprados pelo cliente. |
| `ticket_medio` | `faturamento_acumulado / pedidos_distintos`. |
| `primeira_compra` | Data mínima observada na base para o cliente (não necessariamente a primeira compra da vida). |
| `ultima_compra` | Data máxima observada na base para o cliente. |
| `recencia_dias` | Dias corridos entre `2011-12-10` e a data normalizada de `ultima_compra` (`R` do RFM). |
| `dias_desde_primeira_compra` | Dias entre `2011-12-10` e `primeira_compra` (contexto da janela de observação). |
| `cliente_recorrente` | `True` se `frequencia >= 2`. |
| `segmento_rfm` | Rótulo único dentre os 5 segmentos mutuamente exclusivos. |

---

## 5. Arquivos CSV Exportados em `reports/`

| Arquivo | Granularidade | Escopo / Observação |
|---|---|---|
| `kpis_executivos.csv` | 1 linha por indicador | 26 KPIs consolidados da V2 com comparação à V1. |
| `resumo_clientes.csv` | 1 linha por cliente (4.338) | Visão completa da base de clientes (reproduzível via `main.py`; amostra top-50 em `reports/samples/`). |
| `segmentacao_rfm.csv` | 1 linha por cliente (4.338) | Foco nas dimensões R, F, M e segmento atribuído (amostra top-50 em `reports/samples/`). |
| `resumo_segmentos.csv` | 1 linha por segmento (5) | Volume, participação, receita, ticket médio ponderado, médias e medianas por segmento. |
| `analise_paises.csv` | 1 linha por país (38) | Desempenho geográfico, porte amostral, recorrência interpretável e alerta de baixa amostra. |
| `ranking_produtos.csv` | 1 linha por `stock_code` padronizado | Ranking de produtos com contagem de conflitos de descrição e flag operacional (amostra top-50 em `reports/samples/`). |
| `ranking_clientes.csv` | 1 linha por cliente (4.338) | Ranking decrescente por faturamento com participação acumulada (amostra top-50 em `reports/samples/`). |
| `evolucao_mensal.csv` | 1 linha por mês `YYYY-MM` (13) | Série temporal com flag `periodo_incompleto` para `2011-12`. |
| `analise_cancelamentos.csv` | 1 linha por país | Vendas positivas V2 vs cancelamentos `C` vs saldo monetário observado por país. |
| `analise_sensibilidade.csv` | 1 linha por cenário (6) | Comparação quantitativa das escolhas metodológicas da V1 e V2. |
