# Relatório Independente de Reconciliação Matemática

## 1. Resumo Executivo da Reconciliação

- **Status global:** **APROVADA (100%)**
- **Total de verificações executadas:** 18
- **Verificações aprovadas:** 18
- **Verificações reprovadas:** 0

## 2. Política Monetária (GBP) e Auditoria `Decimal` vs `float64`

A entrada avaliada inclui 4 ocorrência(s) de preço unitário com precisão superior a duas casas decimais (`0.001` (4 linha(s))). Por isso, nenhum valor é arredondado antecipadamente durante os cálculos intermediários:

- **Faturamento exato em `Decimal` (3 casas):** `£ 10631048.744`
- **Soma em `float64` do Pandas:** `10631048.743999999`
- **Diferença absoluta `float64` vs `Decimal`:** `0.000000001863` GBP
- **Valor para exibição em 2 casas (`ROUND_HALF_UP`):** `£ 10631048.74`
- **Delta explícito de arredondamento de exibição:** `-0.004` GBP

> **Limitação documentada da fonte Excel:** arquivos `.xlsx` armazenam números em ponto flutuante IEEE-754. A conversão `Decimal(str(valor))` preserva fielmente a representação decimal curta devolvida pelo Python/OpenPyXL e elimina erro acumulado em somas, mas não substitui uma origem contábil armazenada nativamente em centavos inteiros.

## 3. Matriz Completa de Reconciliações

| Código | Verificação | Esperado | Observado | Diferença | Status | Observação |
|---|---|---:|---:|---:|---|---|
| `REC-01` | Linhas brutas vs soma das categorias mutuamente exclusivas de triagem | `541909` | `541909` | `0` | **APROVADO** |  |
| `REC-02` | Linhas brutas vs mantidas V2 + duplicatas removidas + excluídas não-venda | `541909` | `541909` | `0` | **APROVADO** |  |
| `REC-03` | Faturamento transacional vs base de pedidos (Decimal) | `10631048.744` | `10631048.744` | `0.000` | **APROVADO** |  |
| `REC-04` | Faturamento transacional vs ranking de produtos (Decimal) | `10631048.744` | `10631048.744` | `0.000` | **APROVADO** |  |
| `REC-05` | Faturamento transacional vs análise por país (Decimal) | `10631048.744` | `10631048.744` | `0.000` | **APROVADO** |  |
| `REC-06` | Faturamento transacional vs evolução mensal (Decimal) | `10631048.744` | `10631048.744` | `0.000` | **APROVADO** |  |
| `REC-07` | Faturamento transacional vs soma (identificado + sem CustomerID) | `10631048.744` | `10631048.744` | `0.000` | **APROVADO** |  |
| `REC-08` | Faturamento de clientes identificados vs soma da base de clientes (Decimal) | `8887208.894` | `8887208.894` | `0.000` | **APROVADO** |  |
| `REC-09` | Faturamento total dos segmentos RFM vs base elegível de clientes (Decimal) | `8887208.894` | `8887208.894` | `0.000` | **APROVADO** |  |
| `REC-10` | Clientes elegíveis vs soma de clientes nos segmentos (classificação única) | `4338` | `4338` | `0` | **APROVADO** |  |
| `REC-11` | Pedidos distintos na base transacional vs linhas na base de pedidos | `19959` | `19959` | `0` | **APROVADO** |  |
| `REC-12` | Total de pedidos vs soma de pedidos por país (sem conflito de país/pedido) | `19959` | `19959` | `0` | **APROVADO** |  |
| `REC-13` | Total de pedidos vs soma de pedidos por mês | `19959` | `19959` | `0` | **APROVADO** |  |
| `REC-14` | Pedidos identificados vs soma da frequência em clientes e segmentos | `18532` | `18532` | `0` | **APROVADO** | Soma pedidos nos segmentos: 18532 |
| `REC-15` | Unidades vendidas: transacional vs pedidos, produtos, países e mensal | `5572419` | `5572419` | `0` | **APROVADO** | produtos=5572419, paises=5572419, mensal=5572419 |
| `REC-16` | Ticket médio global (Faturamento / Pedidos distintos) vs média por pedido | `532.644358` | `532.644358` | `0.000000000` | **APROVADO** | Média simples incorreta de segmentos seria £ 420.93 (não utilizada). |
| `REC-17` | Precisão monetária: soma exata Decimal vs float64 do Pandas | `10631048.744` | `10631048.744000` | `0.000000001863` | **APROVADO** | Exibição 2 casas (ROUND_HALF_UP): £ 10631048.74 (diferença de arredondamento: -0.004 GBP). |
| `REC-18` | Verificação de sobreposição de clientes distintos entre países | `4338` | `4346` | `8` | **APROVADO** | 8 cliente(s) compraram em mais de um país; contagens distintas por país não devem ser somadas. |
