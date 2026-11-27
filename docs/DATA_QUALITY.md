# Diagnóstico de Qualidade dos Dados — Online Retail Customer Analytics V2

Este documento consolida a investigação estrutural sobre o arquivo original `Online Retail.xlsx` (UCI Machine Learning Repository, DOI `10.24432/C5BW33`, CC BY 4.0, SHA-256 `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d`), complementando o relatório gerado automaticamente em [relatorio_qualidade.md](../reports/relatorio_qualidade.md).

---

## 1. Resumo dos Achados Críticos

| Dimensão | Achado verificado na base real | Impacto analítico | Tratamento na V2 |
|---|---|---|---|
| **Volume e período** | `541.909` linhas × `8` colunas; `2010-12-01 08:26` a `2011-12-09 12:50` | `2011-12` cobre apenas 9 dias (mês incompleto) | Sinalizado com `periodo_incompleto = True` em `evolucao_mensal.csv` |
| **Ajustes contábeis (`A`)** | `3` linhas (`A563185` `+£11.062,06`; `A563186` e `A563187` `-£11.062,06`) | Na V1, `A563185` entrou silenciosamente como pedido válido (+£ 11.062,06) | Isolado na categoria `ajuste_contabil_prefixo_a`; V1 preservada na sensibilidade |
| **Duplicatas exatas** | `5.268` linhas excedentes na base bruta (`5.226` nas vendas positivas = £ 24.573,74) | Sem `LineItemID`, não é possível provar se toda repetição é erro | Removidas na base principal (política V1) e avaliadas no Cenário 3 da sensibilidade |
| **Ausência de `CustomerID`** | `135.080` linhas brutas (`24,93%`); `132.185` linhas V2 (`£ 1.743.839,85` = `16,40%`) | Excluir cedo demais subestima faturamento global | Mantidas nas análises gerais; excluídas apenas na camada de clientes/RFM |
| **Cancelamentos (`C`)** | `9.288` linhas brutas (`9.251` deduplicadas), `3.836` notas distintas, `-£ 893.979,73` | Não possuem chave estrangeira apontando para o pedido original | Analisados em módulo próprio (`cancellations.py`), com saldo observado separado |
| **Negativos sem `C`** | `1.336` linhas (`-206.957` un.), **100% com `UnitPrice == 0`** | Baixas/avarias/descartes de estoque (`damaged`, `thrown away`, `NaN`) | Nunca contabilizados como devoluções comerciais |
| **Preços zerados positivos** | `1.179` linhas (`Quantity > 0`, `UnitPrice == 0`; `40` com `CustomerID`) | Bonificações, ajustes internos ou falta de preço cadastrado | Separados na categoria `preco_nao_positivo` |
| **Tipagem mista Excel** | `InvoiceNo`: `532.618 int` / `9.291 str`; `StockCode`: `487.036 int` / `54.873 str` | `query("StockCode == 23843")` da V1 falha se o código for string | Padronização explícita para texto limpo em maiúsculas |
| **Variações de `StockCode` e `Description`** | `112` variações de caixa na base bruta; `642` códigos com múltiplas descrições (`220` nas vendas) | Na V1, `22197` (`POPCORN HOLDER` / `SMALL POPCORN HOLDER`) ficou fragmentado | Agrupamento por `stock_code` maiúsculo com `qtd_descricoes_distintas` exposta |
| **Múltiplos timestamps/pedido** | `42` pedidos V2 possuem `2` timestamps separados por `60s` no mesmo dia | `.first()` depende da ordem de leitura do arquivo | Consolidação determinística com `min(invoice_date)` após validação |
| **Clientes em múltiplos países** | `8` clientes compraram em `2` países (`12370, 12394, 12417, 12422, 12429, 12431, 12455, 12457`) | Somar clientes por país dá `4.346` em vez de `4.338` | Verificação `REC-18` + coluna `paises_distintos` na base de clientes |
| **Precisão > 2 casas decimais** | `4` registros com `UnitPrice = 0.001` (`3` de `PADS`, `1` de `BANK CHARGES`) | Soma exata possui 3 casas (`£ 10.631.048,744`) | Cálculo intermediário em `Decimal` exato; delta `-0,004` documentado na exibição |

---

## 2. Granularidade: Por Que Cada Nível Exige Regras Próprias

1. **Linha de transação (`524.877` linhas V2):** representa um lançamento de item dentro de uma fatura. Como a fonte não possui `LineItemID`, duas linhas com exatamente as mesmas 8 colunas são indistinguíveis — razão pela qual `drop_duplicates()` exige alerta metodológico e cenário de sensibilidade.
2. **Pedido (`19.959` pedidos V2):** uma linha por `InvoiceNo`. Só é seguro atribuir `customer_id` e `country` ao pedido após confirmar que **0 pedidos** possuem dois clientes ou dois países diferentes (`validate_order_level_consistency`).
3. **Produto (`StockCode` padronizado):** agrupar por `["StockCode", "Description"]` como na V1 fragmenta produtos que mudaram de nome ao longo do ano (caso emblemático do `22197`, que soma `56.898` unidades quando unificado!).
4. **Cliente (`4.338` identificados):** exclui `1.427` pedidos sem `CustomerID`, cuja receita (`£ 1.743.839,85`) é sempre reconciliada de volta ao total geral (`REC-07`).

---

## 3. Qualidade dos Códigos Operacionais Não-Mercadoria

Na Base Principal V2, `2.340` linhas (`£ 383.829,42`, ou `3,61%` da receita) referem-se a códigos administrativos/logísticos (`DOT`, `POST`, `M`, `AMAZONFEE`, `C2`, `BANK CHARGES`, `S`, `PADS` e vouchers `gift_0001_*`). O item `DOT` (`DOTCOM POSTAGE`, `£ 206.248,77`) aparece inclusive em 1º lugar no ranking bruto por faturamento caso códigos operacionais não sejam rotulados — por isso `ranking_produtos.csv` traz explicitamente a coluna `codigo_operacional` e o Cenário 6 de `relatorio_sensibilidade.md` isola exclusivamente mercadorias físicas (`£ 10.247.219,32`).

---

## 4. Política Estrita de Integridade de `Quantity`, `CustomerID` e Limites de Ingestão

- **Ingestão CSV (`dtype=str`):** em `src/data/loader.py`, arquivos `.csv` são lidos explicitamente com `dtype=str` e tratamento padrão de ausentes (`keep_default_na=True`), convertendo `InvoiceDate` separadamente. Isso impede que o Pandas infira `float64` automaticamente durante a leitura quando existem inteiros acima de `2**53` junto a valores fracionados (`1.5`) ou nulos na mesma coluna.
- **Limites naturais da precisão numérica do Excel (`.xlsx`):** células numéricas no padrão Excel armazenam valores em ponto flutuante binário IEEE-754 de 64 bits (53 bits de significando, aproximadamente 15 dígitos decimais exatos). Por limitação intrínseca do formato `.xlsx`, inteiros acima de `2**53` (`9.007.199.254.740.992`) só preservam todos os dígitos no Excel se armazenados como texto; caso gravados como número na planilha original, o arredondamento ocorre antes da leitura pelo OpenPyXL/Pandas. No dataset oficial UCI, todos os `CustomerID` (5 dígitos) e `Quantity` (até `80.995`) estão muito abaixo desse limite.
- **Quantidades (`Quantity`):** somente valores numéricos finitos e exatamente inteiros são aceitos nas categorias comerciais, validados via `int` e `Decimal` sem conversão intermediária para `float` (preservando precisão exata inclusive para inteiros acima de `2**53`). Valores fracionados (`1.5`, `-1.5`) ou não finitos (`inf`, `-inf`, `NaN`) são classificados em `registro_ambiguo_ou_inconsistente` sem truncamento silencioso.
- **Identificadores de cliente (`CustomerID`):** distingue-se explicitamente `valido` (inteiro positivo finito validado via `int`/`Decimal`, preservando precisão exata acima de `2**53`), `ausente` (`None`, `NaN` ou texto vazio — permitido nas análises comerciais gerais) e `invalido` (fracionados como `123.5`, infinitos, `<= 0`, notação científica textual ou textos malformados — isolados em `registro_ambiguo_ou_inconsistente` para impedir fusão indevida de clientes).

---

## 5. Reprodução Exata do Ambiente vs Compatibilidade Entre Versões

- **Reprodução exata do ambiente oficial (`requirements.txt` fixado):** `Python 3.12.7`, `pandas==3.0.6`, `openpyxl==3.1.5`, `pytest==8.4.2` — garante igualdade integral nos `15/15` arquivos de relatório.
- **Compatibilidade entre versões (Pandas 2.2.3 + Pytest 9.0.2):** validada com `0 FutureWarning` (após tipagem explícita de DataFrames vazios em `cancellations.py`), `18/18` reconciliações e indicadores idênticos; a única diferença textual esperada ocorre na exibição de `dtypes` no `relatorio_qualidade.md` (`object` / `datetime64[ns]` no Pandas 2.2.x versus `str` / `datetime64[us]` no Pandas 3.0.x), preservada autenticamente sem forçar igualdade artificial entre ambientes.
