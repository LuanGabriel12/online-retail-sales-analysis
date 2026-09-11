# Online Retail Sales Analysis

Projeto de análise de dados desenvolvido em Python com Pandas utilizando o dataset Online Retail da UCI Machine Learning Repository.

O objetivo é praticar limpeza, transformação, agrupamento e interpretação de dados reais de vendas.

## Objetivos

- Preparar e limpar os dados de vendas
- Consolidar produtos por pedido
- Calcular o ticket médio
- Comparar o ticket médio entre países
- Identificar os produtos mais vendidos
- Identificar os clientes com maior faturamento
- Investigar valores atípicos encontrados nos dados

## Tecnologias

- Python
- Pandas
- Jupyter Notebook
- OpenPyXL

## Dataset

- **Dataset:** Online Retail
- **Fonte:** [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/352/online+retail)
- **Período:** 01/12/2010 a 09/12/2011
- **Moeda:** libra esterlina (£)
- **Licença do dataset:** CC BY 4.0

O dataset reúne transações de uma empresa de varejo online sediada no Reino Unido. A autoria do dataset pertence à fonte indicada acima.

## Preparação dos Dados

- Foram mantidos registros com `Quantity > 0`.
- Foram mantidos registros com `UnitPrice > 0`.
- Duplicatas exatas foram removidas.
- A coluna `Total_venda` foi criada a partir da quantidade e do preço unitário.
- Foram criadas colunas auxiliares de ano, mês, dia e hora.
- Valores nulos em `CustomerID` foram desconsiderados apenas nas análises que dependem da identificação do cliente.

Quantidades ou preços não positivos podem representar devoluções, cancelamentos ou registros não comerciais; por isso, foram retirados do recorte utilizado neste projeto.

## Principais Resultados

- **Ticket médio geral:** £ 533,17 por pedido
- **Maior ticket médio por país:** Singapura — £ 3.039,90
- **Produto mais vendido:** PAPER CRAFT, LITTLE BIRDIE — 80.995 unidades
- **Cliente com maior faturamento:** ID 14646 — £ 280.206,02

O produto com 80.995 unidades está associado a um único pedido atípico. O registro foi mantido na análise sem atribuição de uma causa que não possa ser comprovada pelos dados.

## Estrutura da Análise

1. Carregamento dos dados
2. Limpeza e preparação
3. Construção da base por pedido
4. Cálculo do ticket médio
5. Análise por país
6. Produtos mais vendidos
7. Clientes com maior faturamento
8. Investigação de outlier
9. Resumo executivo

## Como Executar

1. Clone este repositório.
2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Abra o arquivo `projeto.ipynb` no Jupyter Notebook.
4. Execute as células em ordem.

O arquivo `Online Retail.xlsx` deve permanecer no mesmo diretório do notebook.

## Aprendizados

O projeto permitiu praticar filtros em DataFrames, `groupby`, `agg`, `sum`, `mean`, `nunique`, tratamento de valores nulos, remoção de duplicatas, manipulação de datas, análise de métricas de negócio e interpretação de resultados.
