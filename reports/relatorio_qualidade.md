# Relatório de Qualidade dos Dados — Online Retail Customer Analytics V2

## 1. Identificação e Integridade da Fonte

- **Escopo da entrada:** Dataset oficial confirmado — Online Retail (UCI Machine Learning Repository)
- **URL oficial:** https://archive.ics.uci.edu/dataset/352/online+retail
- **DOI:** https://doi.org/10.24432/C5BW33
- **Autoria original:** Daqing Chen (London South Bank University)
- **Licença:** CC BY 4.0
- **Arquivo avaliado:** `Online Retail.xlsx` (22.62 MB / 23.715.344 bytes)
- **SHA-256 verificado:** `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d` (corresponde ao hash oficial UCI: **Sim**)
- **Registros brutos:** 541.909 linhas e 8 colunas
- **Período efetivo observado:** `2010-12-01 08:26:00` até `2011-12-09 12:50:00`
- **Datas fora da janela de referência UCI (01/12/2010 a 09/12/2011):** 0

## 2. Granularidade das Bases e Ausência de Chave Única de Item

| Nível analítico | Granularidade (chave lógica) | Observações técnicas |
|---|---|---|
| **Linha de transação** | Uma linha por lançamento de item em fatura | **Não existe identificador único de item (`LineItemID`)** no esquema da base. `InvoiceNo` repete-se em pedidos multiproduto. |
| **Pedido** | Uma linha por `InvoiceNo` válido | Consolidado somente após validar 0 conflitos de `CustomerID` e `Country` por pedido. |
| **Produto** | Uma linha por `StockCode` padronizado (maiúsculas) | Existem `112` variações de caixa e `642` códigos com múltiplas descrições nesta entrada. |
| **Cliente** | Uma linha por `CustomerID` identificado válido | Exclui transações válidas com `CustomerID` ausente (mantidas nas visões gerais) e rejeita identificadores inválidos. |

> **Atenção sobre duplicatas exatas:** foram encontradas **5.268** linhas exatamente repetidas na base bruta (10.147 linhas envolvidas). Como não existe chave única de item, não se presume automaticamente que toda linha idêntica seja erro de exportação; a remoção segue a política preservada da V1 na base principal e tem seu impacto quantificado na Análise de Sensibilidade.

## 3. Auditoria de Esquema, Tipos, Valores Ausentes e Integridade Numérica

| Coluna | Tipo lido pelo Pandas | Ausentes | % Ausentes |
|---|---|---:|---:|
| `InvoiceNo` | `object` | 0 | 0,0000% |
| `StockCode` | `object` | 0 | 0,0000% |
| `Description` | `object` | 1.454 | 0,2683% |
| `Quantity` | `int64` | 0 | 0,0000% |
| `InvoiceDate` | `datetime64[us]` | 0 | 0,0000% |
| `UnitPrice` | `float64` | 0 | 0,0000% |
| `CustomerID` | `float64` | 135.080 | 24,9267% |
| `Country` | `str` | 0 | 0,0000% |

- **Tipagem observada na leitura Excel (via OpenPyXL):**
  - `InvoiceNo`: `{'int': 532618, 'str': 9291}`
  - `StockCode`: `{'str': 54873, 'int': 487036}`
  - `CustomerID` não inteiro / inválido no Excel: `0`
- **Validação estrita de campos críticos (sem truncamento silencioso):**
  - Quantidades fracionadas ou não finitas (`Quantity`): **0**
  - Preços unitários não finitos (`UnitPrice`): **0**
  - `CustomerID` ausentes (permitidos em vendas gerais): **135.080**
  - `CustomerID` inválidos (fracionados, infinitos, <= 0 ou malformados — isolados em `registro_ambiguo_ou_inconsistente`): **0**
- **Precisão de `UnitPrice` acima de 2 casas decimais:** `0.001` (4 linhas). Os cálculos intermediários preservam a precisão integral em `Decimal` sem arredondamento antecipado.

## 4. Triagem Mutuamente Exclusiva da Base Bruta

| Categoria de triagem (mutuamente exclusiva) | Quantidade de linhas |
|---|---:|
| `venda_positiva_valida` | 530.103 |
| `cancelamento_identificado` | 9.288 |
| `ajuste_contabil_prefixo_a` | 3 |
| `quantidade_negativa_sem_prefixo_c` | 1.336 |
| `preco_nao_positivo` | 1.179 |
| `registro_ambiguo_ou_inconsistente` | 0 |

- **Vendas positivas padrão antes de deduplicação:** 530.103
- **Duplicatas exatas removidas nas vendas positivas:** 5.226 (impacto monetário: £ 24.573,74)
- **Linhas mantidas na Base Principal V2:** 524.877
- **Linhas na Reprodução da Regra V1:** 524.878 (diferença de `1` linha(s): `A563185` (Adjust bad debt, £ 11.062,06))

## 5. Consistência de Pedidos, Produtos e Clientes

- **Pedidos com múltiplas linhas (na base bruta):** 20.059
- **Pedidos com múltiplos produtos distintos (na base bruta):** 20.006
- **Pedidos com conflito de `CustomerID` (na base V2):** 0
- **Pedidos com mistura de cliente preenchido e nulo (na base V2):** 0
- **Pedidos com conflito de `Country` (na base V2):** 0
- **Pedidos com mais de um timestamp `InvoiceDate` (na base V2):** 42 (todos no mesmo dia calendário: 42; diferença máxima observada: 60 segundos — resolvidos determinísticamente com `min(InvoiceDate)`).
- **Clientes associados a mais de um país na base bruta:** 8

## 6. Cancelamentos e Registros Não Comerciais

- **Notas de cancelamento (prefixo `C`):** 9.288 linhas brutas (9.251 sem duplicatas exatas), 3.836 notas distintas, totalizando £ -893.979,73 (deduplicado) / £ -896.812,49 (bruto).
- **Quantidades negativas sem prefixo `C`:** 1.336 linhas (-206.957 unidades), valor monetário £ 0,00 (**não tratadas automaticamente como devoluções comerciais**).
- **Preços não positivos (sem prefixo `C`/`A`):** 1.179 linhas (40 com `CustomerID`).
- **Ajustes contábeis com prefixo `A`:** 3 linhas (`A563185`, `A563186`, `A563187`), saldo líquido £ -11.062,06.
- **Registros ambíguos ou inconsistentes:** 0 linhas.
