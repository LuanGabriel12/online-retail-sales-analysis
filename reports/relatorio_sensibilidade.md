# Relatório de Outliers e Análise de Sensibilidade Metodológica

## 1. Princípio Metodológico

Nenhum registro de valor elevado é removido automaticamente da Base Principal V2. Em vez disso, preservamos a base principal transparente e isolamos em cenários paralelos o impacto de cada escolha metodológica (regra V1, duplicatas exatas, pedidos atípicos investigados e códigos operacionais não-mercadoria).

## 2. Investigação dos Pedidos Atípicos de Referência

### Caso 1 — PAPER CRAFT , LITTLE BIRDIE (StockCode 23843 / Pedido 581483)

- **Pedido (`InvoiceNo`):** `581483` | **Data:** `2011-12-09 09:15:00`
- **Produto (`StockCode`):** `23843` — `PAPER CRAFT , LITTLE BIRDIE`
- **Cliente (`CustomerID`):** `16446` | **País:** `United Kingdom`
- **Quantidade:** 80.995 unidades | **Preço unitário:** £ 2,08 | **Valor monetário:** £ 168.469,60
- **Participação no volume total do produto na base V2:** 100,00% (total de 1 pedido(s) do produto na base V2)
- **Contexto do cliente:** possui 1 outro(s) pedido(s) válido(s) somando £ 2,90.
- **Notas de cancelamento potencialmente relacionadas:**
  - Nota `C581484` em `2011-12-09 09:27:00` (+12 min): quantidade `-80.995`, preço unitário £ 2,08, valor £ -168.469,60.
- **Ressalva metodológica:** A base da UCI não possui chave estrangeira vinculando notas de cancelamento ao pedido original; a correspondência por produto, cliente, quantidade oposta e proximidade temporal constitui forte indício operacional, mas não prova documental definitiva.


### Caso 2 — MEDIUM CERAMIC TOP STORAGE JAR (StockCode 23166 / Pedido 541431)

- **Pedido (`InvoiceNo`):** `541431` | **Data:** `2011-01-18 10:01:00`
- **Produto (`StockCode`):** `23166` — `MEDIUM CERAMIC TOP STORAGE JAR`
- **Cliente (`CustomerID`):** `12346` | **País:** `United Kingdom`
- **Quantidade:** 74.215 unidades | **Preço unitário:** £ 1,04 | **Valor monetário:** £ 77.183,60
- **Participação no volume total do produto na base V2:** 95,11% (total de 247 pedido(s) do produto na base V2)
- **Contexto do cliente:** possui 0 outro(s) pedido(s) válido(s) somando £ 0,00.
- **Notas de cancelamento potencialmente relacionadas:**
  - Nota `C541433` em `2011-01-18 10:17:00` (+16 min): quantidade `-74.215`, preço unitário £ 1,04, valor £ -77.183,60.
- **Ressalva metodológica:** A base da UCI não possui chave estrangeira vinculando notas de cancelamento ao pedido original; a correspondência por produto, cliente, quantidade oposta e proximidade temporal constitui forte indício operacional, mas não prova documental definitiva.


## 3. Impacto dos Códigos Operacionais Não-Mercadoria na Base V2

A Base Principal V2 desta execução contém **2.340** linha(s) de códigos operacionais/administrativos (`DOT`, `POST`, `M`, `AMAZONFEE`, `C2`, `BANK CHARGES`, `S`, `PADS` e vouchers `gift_0001_*`), totalizando **£ 383.829,42**.

## 4. Tabela Comparativa de Sensibilidade

| Cenário | Pedidos | Unidades | Faturamento | Variação vs Base V2 | Ticket Médio | Líder em Unidades | Líder em Receita |
|---|---:|---:|---:|---:|---:|---|---|
| 1. Base Principal V2 | 19.959 | 5.572.419 | £ 10.631.048,74 | £ 0,00 (0,00%) | £ 532,64 | 23843 - PAPER CRAFT , LITTLE BIRDIE (80.995) | `14646` |
| 2. Reprodução da Regra V1 | 19.960 | 5.572.420 | £ 10.642.110,80 | £ 11.062,06 (0,10%) | £ 533,17 | 23843 - PAPER CRAFT , LITTLE BIRDIE (80.995) | `14646` |
| 3. Sem Remoção de Duplicatas Exatas | 19.959 | 5.588.375 | £ 10.655.622,48 | £ 24.573,74 (0,23%) | £ 533,88 | 23843 - PAPER CRAFT , LITTLE BIRDIE (80.995) | `14646` |
| 4. Sem Outlier Principal (581483) | 19.958 | 5.491.424 | £ 10.462.579,14 | £ -168.469,60 (-1,58%) | £ 524,23 | 23166 - MEDIUM CERAMIC TOP STORAGE JAR (78.033) | `14646` |
| 5. Sem Dois Maiores Outliers (581483 e 541431) | 19.957 | 5.417.209 | £ 10.385.395,54 | £ -245.653,20 (-2,31%) | £ 520,39 | 22197 - POPCORN HOLDER (56.898) | `14646` |
| 6. Apenas Mercadorias (sem códigos operacionais) | 19.773 | 5.561.384 | £ 10.247.219,32 | £ -383.829,42 (-3,61%) | £ 518,24 | 23843 - PAPER CRAFT , LITTLE BIRDIE (80.995) | `14646` |

## 5. Síntese das Conclusões de Sensibilidade (Execução Atual)

- **Regra V1 vs Base V2:** a diferença entre V1 e V2 nesta entrada foi de £ 11.062,06 (0,10%) e +1 pedido(s), alterando o ticket médio de £ 533,17 (V1) para £ 532,64 (V2).
- **Duplicatas exatas:** manter as 5.226 linha(s) repetida(s) adicionaria £ 24.573,74 (0,23%) ao faturamento da base principal.
- **Outliers investigados:** remover `581483` altera o faturamento em £ -168.469,60 (-1,58%) e passa a liderança em unidades para `23166 - MEDIUM CERAMIC TOP STORAGE JAR` (78.033 un.); remover ambos (`581483` e `541431`) altera o faturamento em £ -245.653,20 (-2,31%) e desloca a liderança em unidades para `22197 - POPCORN HOLDER` (56.898 un.) (evidenciando também a unificação por `StockCode` em vez de fragmentar descrições).
- **Códigos operacionais não-mercadoria:** retirar as 2.340 linha(s) administrativas altera o faturamento em £ -383.829,42 (-3,61%), isolando apenas mercadorias físicas.
