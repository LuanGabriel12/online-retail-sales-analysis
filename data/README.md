# Dataset Oficial — Online Retail (UCI Machine Learning Repository)

## Fonte, Autoria e Licença

- **Dataset:** Online Retail
- **Fonte oficial:** [UCI Machine Learning Repository — ID 352](https://archive.ics.uci.edu/dataset/352/online+retail)
- **DOI:** [https://doi.org/10.24432/C5BW33](https://doi.org/10.24432/C5BW33)
- **Autoria original:** Daqing Chen (School of Engineering, London South Bank University)
- **Licença:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- **Período coberto:** 01/12/2010 a 09/12/2011 (dezembro de 2011 incompleto)
- **Moeda:** libra esterlina (`GBP` / `£`)
- **Dimensões verificadas:** `541.909` linhas × `8` colunas

## Posicionamento do Arquivo Bruto

Para preservar integralmente a execução histórica do notebook original `projeto.ipynb` (V1) sem alterar seu caminho relativo (`pd.read_excel("Online Retail.xlsx")`), o arquivo bruto permanece intacto na raiz do repositório:

```text
online-retail-sales-analysis/Online Retail.xlsx
```

O pipeline V2 também aceita `data/raw/Online Retail.xlsx` como caminho alternativo ou qualquer caminho explícito via `python main.py --input <caminho>`.

O arquivo bruto **nunca é modificado** pelo código da V2.

## Verificação de Integridade (SHA-256)

- **Tamanho esperado:** `23.715.344` bytes (`22,62 MB`)
- **SHA-256 esperado:** `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d`

### Como obter e verificar manualmente (caso não esteja incluído no pacote)

1. Acesse a página oficial na UCI: <https://archive.ics.uci.edu/dataset/352/online+retail>.
2. Baixe o pacote do dataset e extraia o arquivo `Online Retail.xlsx`.
3. Coloque `Online Retail.xlsx` na raiz do projeto (ou em `data/raw/Online Retail.xlsx`).
4. Verifique o hash SHA-256 antes de executar o pipeline:

   **Windows (PowerShell):**
   ```powershell
   Get-FileHash "Online Retail.xlsx" -Algorithm SHA256
   ```

   **Linux / macOS:**
   ```bash
   sha256sum "Online Retail.xlsx"
   ```

5. Execute o pipeline:
   ```bash
   python main.py
   ```
