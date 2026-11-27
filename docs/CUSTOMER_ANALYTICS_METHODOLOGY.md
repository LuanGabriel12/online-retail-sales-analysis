# Metodologia de Customer Analytics — RFM, Recorrência, Concentração e Sensibilidade

## 1. Definição das Métricas RFM

A análise RFM desta V2 é estritamente **descritiva, determinística e reproduzível**, aplicada aos **4.338 clientes identificados** presentes na Base Principal V2 (`18.532` pedidos, `£ 8.887.208,894`):

- **Recency (`recencia_dias`):** quantidade de dias corridos entre a data de referência fixa **`2011-12-10`** e a data calendário normalizada da última compra válida observada do cliente (`(2011-12-10 - ultima_compra.normalize()).days`).
  - Por que `2011-12-10`? A última transação do dataset ocorreu em `2011-12-09 12:50:00`. Fixar o dia seguinte garante `recencia >= 1` dia e resultados idênticos em qualquer execução futura (jamais usar `datetime.now()`).
- **Frequency (`frequencia`):** quantidade de pedidos de venda distintos (`nunique(invoice_no)`) do cliente na base V2. Não conta linhas de item, e sim eventos distintos de compra.
- **Monetary (`valor_monetario` / `faturamento_acumulado_decimal`):** faturamento bruto acumulado das vendas válidas observadas no período. **Não equivale a lucro** (não há custos) nem a **Customer Lifetime Value (CLV)** preditivo.

### Perfil Estatístico Observado dos 4.338 Clientes

| Dimensão | Mínimo | Mediana | Média | Máximo | Interpretação |
|---|---:|---:|---:|---:|---|
| Recência (dias) | `1` | `51,0` | `93,06` | `374` | Metade dos clientes comprou nos últimos 51 dias; há forte cauda longa. |
| Frequência (pedidos) | `1` | `2,0` | `4,27` | `209` | Metade fez até 2 pedidos; clientes atacadistas elevam a média (máx. 209). |
| Valor Monetário (GBP) | `£ 3,75` | `£ 668,57` | `£ 2.048,69` | `£ 280.206,02` | Forte assimetria à direita: média é mais de 3× superior à mediana. |

---

## 2. Segmentação Comercial por Regras Transparentes

Em vez de algoritmos caixa-preta (K-Means) ou quantis automáticos (`qcut`), utilizamos **5 regras explícitas, mutuamente exclusivas e coletivamente exaustivas**, avaliadas em ordem estrita de prioridade em `src/analytics/segmentation.py`:

| Prioridade | Segmento | Regra exata | Clientes | % Clientes | Faturamento | % Receita Ident. | Ticket Médio |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | **Alto valor e recorrentes** | `freq >= 5` e `valor >= £ 1.500` e `rec <= 90 d` | `840` | `19,36%` | `£ 5.954.738,26` | `67,00%` | `£ 564,54` |
| 2 | **Recorrentes recentes** | `freq >= 2` e `rec <= 90 d` | `1.403` | `32,34%` | `£ 1.642.178,58` | `18,48%` | `£ 353,16` |
| 3 | **Compra única recente** | `freq == 1` e `rec <= 90 d` | `646` | `14,89%` | `£ 257.749,76` | `2,90%` | `£ 398,99` |
| 4 | **Recorrentes há mais tempo sem compras** | `freq >= 2` e `rec > 90 d` | `602` | `13,88%` | `£ 676.302,49` | `7,61%` | `£ 367,36` |
| 5 | **Compra única há mais tempo sem compras** | `freq == 1` e `rec > 90 d` | `847` | `19,53%` | `£ 356.239,80` | `4,01%` | `£ 420,59` |
| — | **Total elegível** | Todos os clientes identificados (100%) | **`4.338`** | **`100,00%`** | **`£ 8.887.208,89`** | **`100,00%`** | **`£ 479,56`** |

### Justificativa dos Limites e Ressalvas Obrigatórias
- **Limites ancorados na base observada:** `5` pedidos e `£ 1.500` ficam próximos ao quartil superior observado (`P75`: `5` pedidos e `£ 1.660,60`); `90` dias representam um trimestre de calendário dentro de uma base de ~12 meses. **Esses cortes não são padrões universais de mercado** e devem ser recalibrados em outros negócios.
- **Não classificar como "churn definitivo":** um cliente com `recencia > 90 dias` pode ser comprador sazonal (ex.: natalino) ou atacadista de reposição semestral.
- **Ticket médio do segmento vs ticket médio global:** o ticket médio de cada segmento é `faturamento_segmento / pedidos_segmento`. A média simples dos 5 tickets médios seria `£ 420,93`, enquanto o ticket médio ponderado real dos clientes identificados é `£ 8.887.208,894 / 18.532 = £ 479,56` (e o global com não identificados é `£ 532,64`).

---

## 3. Recorrência Observada vs Retenção de Longo Prazo

- **Recorrência observada no período:** `2.845` de `4.338` clientes (`65,58%`) fizeram `>= 2` pedidos; `1.493` (`34,42%`) fizeram apenas `1` pedido.
- **Concentração de frequência:** `391` clientes com `10+` pedidos (`9,01%` da base) respondem por **`51,31%`** (`£ 4.560.301,78`) de toda a receita identificada.
- **Limitação da janela de observação (censura à direita e à esquerda):**
  - `968` clientes tiveram sua primeira compra observada nos últimos `90` dias (sendo `646` ainda com 1 pedido). Eles tiveram menos tempo para recomprar dentro da base.
  - A "primeira compra observada" em `2010-12` pode pertencer a um cliente antigo que já comprava antes de dezembro de 2010.
  - Portanto, **recorrência observada no recorte não equivale a taxa de retenção de longo prazo**, nem autoriza extrapolações para períodos futuros.

---

## 4. Concentração Comercial e Análise de Sensibilidade

- **Concentração em clientes:** Top 10 = `17,30%` da receita identificada (`14,46%` da total); Top 50 = `33,30%` (`27,84%` da total); Top 100 = `40,61%` (`33,95%` da total).
- **Concentração geográfica:** `United Kingdom` concentra `84,57%` da receita (`£ 8.990.682,03`); Top 5 países somam `94,04%`.
- **Sensibilidade metodológica:** os clientes `16446` (#4, `£ 168.472,50`) e `12346` (#10, `£ 77.183,60`) dependem de pedidos únicos extremos (`581483` e `541431`) seguidos minutos depois pelas notas `C581484` e `C541433`. Sem afirmar vínculo documental comprovado, o módulo `outliers.py` mede o impacto exato da exclusão desses registros (`-£ 245.653,20`, `-2,31%` na receita e mudança do produto líder em unidades para `22197 - POPCORN HOLDER`, `56.898` un.).
