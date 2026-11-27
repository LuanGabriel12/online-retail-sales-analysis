# Regras de Negócio — Online Retail Customer Analytics V2

## 1. Triagem Mutuamente Exclusiva da Base Bruta

Cada uma das `541.909` linhas do arquivo original é classificada em **exatamente uma** categoria na ordem abaixo (implementada em `src/data/cleaning.py:classify_raw_record`):

1. **`registro_ambiguo_ou_inconsistente`:** ausência de `InvoiceNo`, `StockCode`, `InvoiceDate`, `Country`, `Quantity` ou `UnitPrice`; `Quantity` não finita (`inf`, `-inf`, `NaN`) ou fracionada (ex.: `1.5`, jamais truncada silenciosamente para `1`, com validação exata via `int`/`Decimal` preservando precisão acima de `2**53`); `UnitPrice` não finito (`inf`, `-inf`, `NaN`); `CustomerID` inválido (fracionado como `123.5`, infinito, `<= 0`, notação científica textual ou malformado — distinguido explicitamente de `CustomerID` ausente, sem truncamento e com preservação exata acima de `2**53`); `InvoiceNo` fora dos padrões (dígitos, prefixo `C` ou prefixo `A`); prefixo `C` com `Quantity >= 0` ou `UnitPrice <= 0`; ou `Quantity == 0`.
2. **`cancelamento_identificado`:** `InvoiceNo` iniciado pela letra `C`, com `Quantity < 0` e `UnitPrice > 0`.
3. **`ajuste_contabil_prefixo_a`:** `InvoiceNo` iniciado pela letra `A` (`A563185`, `A563186`, `A563187` — `Adjust bad debt`).
4. **`quantidade_negativa_sem_prefixo_c`:** `InvoiceNo` puramente numérico com `Quantity < 0` (na base real, todas as `1.336` linhas têm `UnitPrice == 0` e refletem baixas/avarias/ajustes de estoque).
5. **`preco_nao_positivo`:** `InvoiceNo` puramente numérico com `Quantity > 0` e `UnitPrice <= 0`.
6. **`venda_positiva_valida`:** `InvoiceNo` puramente numérico com `Quantity > 0` e `UnitPrice > 0`.

## 2. Política de Limpeza: Base Principal V2 vs Reprodução Histórica V1

- **Base Principal V2 (`df_sales_v2`):** utiliza apenas registros `venda_positiva_valida` e remove duplicatas exatas sobre as 8 colunas originais (`keep="first"`), preservando a política de deduplicação da V1 para comparabilidade, porém **excluindo o lançamento contábil `A563185` (`Adjust bad debt`, £ 11.062,06)**.
- **Reprodução Histórica V1 (`df_sales_v1`):** reproduz literalmente `Quantity > 0 and UnitPrice > 0` seguido de `drop_duplicates()` (mantendo `A563185`) para evidenciar de forma transparente a diferença entre V1 e V2.
- **Registros sem `CustomerID`:** mantidos em todas as visões comerciais gerais (faturamento total, pedidos, países, produtos e evolução mensal) e excluídos apenas da base de clientes, RFM, segmentação e recorrência.

## 3. Política de Consolidação de Pedidos, Produtos e Clientes

- **Pedidos (`InvoiceNo`):** antes de agregar, o sistema valida que não existem pedidos com mais de um `CustomerID`, mistura de `CustomerID` preenchido/nulo ou mais de um `Country`. Caso exista qualquer conflito, o pipeline interrompe com `ValueError`. Para `InvoiceDate` (onde há `42` pedidos com 2 timestamps separados por 60 segundos no mesmo dia), adota-se `min(InvoiceDate)` de forma determinística.
- **Produtos (`StockCode`):** agrupados por `StockCode` padronizado em maiúsculas (unificando `110` variações de caixa). A descrição principal é a mais frequente não nula (desempate alfabético) e a coluna `qtd_descricoes_distintas` expõe publicamente os conflitos de descrição.
- **Clientes (`CustomerID`):** cada cliente recebe um `pais_principal` (país com maior número de pedidos; desempate por receita e ordem alfabética) e mantém `paises_distintos` explícito para nunca mascarar clientes multigeográficos (`8` clientes).

## 4. Política de Cancelamentos e Saldo Observado

- Notas de cancelamento (`C`) são analisadas separadamente e **nunca** associadas automaticamente a um pedido original sem chave estrangeira oficial.
- Quantidades negativas sem prefixo `C` (`UnitPrice == 0`) **não** são somadas como devoluções comerciais.
- A taxa de cancelamento usa denominador explícito: `abs(valor_cancelamentos) / valor_vendas_positivas_V2 * 100`.
- O indicador `saldo_monetario_observado = vendas_positivas_V2 + cancelamentos_C` é estritamente descritivo e **não deve ser apresentado como faturamento líquido contábil certificado**.

## 5. Fórmulas Oficiais de Indicadores

- **Ticket médio (global, por país, por mês ou por segmento):** `faturamento_total_do_grupo / quantidade_de_pedidos_distintos_do_grupo`. Nunca utilizar média simples de tickets médios de subgrupos.
- **Recência (RFM):** `(date(2011, 12, 10) - data_ultima_compra_valida).days`, com data fixa de referência.
- **Frequência (RFM):** `nunique(invoice_no)` nas vendas positivas válidas V2 do cliente.
- **Valor Monetário (RFM):** soma do faturamento das vendas positivas válidas V2 do cliente (não é lucro nem CLV).
- **Taxa de recorrência observada:** `clientes_com_2_ou_mais_pedidos / total_clientes_identificados * 100`.

## 6. Regras de Contexto e Restrições de Interpretação

1. **Dezembro/2011 incompleto:** marcado com `periodo_incompleto = True` (`01/12/2011` a `09/12/2011`); não comparar diretamente com meses completos sem normalização.
2. **Amostra pequena em países:** países com `< 10` pedidos são rotulados como `Amostra muito baixa (< 10 pedidos)` e países com `< 10` clientes identificados recebem `recorrencia_interpretavel = False`.
3. **Não aditividade de contagens distintas:** nunca somar `clientes_identificados` por país ou por mês para obter o total global de clientes.
4. **Sem cálculo de lucro/margem:** a fonte não possui custos unitários, impostos ou despesas logísticas.
5. **Política monetária GBP:** todos os somatórios oficiais preservam precisão integral em `Decimal` (inclusive as 3 casas decimais oriundas dos 4 registros de `0.001` GBP); arredondamentos para 2 casas (`ROUND_HALF_UP`) ocorrem apenas na apresentação, com delta explicitamente reportado.
