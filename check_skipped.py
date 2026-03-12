import pandas as pd
import os

EXCEL_FILE = "ACOMPANHAMENTO PROCESSUAL 2023.xlsx"

if os.path.exists(EXCEL_FILE):
    xl = pd.ExcelFile(EXCEL_FILE)
    ignore_sheets = ['dados_referencia', 'ARQUIVADOS', 'Caroline_bkp', 'Processos']
    analistas_sheets = [s for s in xl.sheet_names if s not in ignore_sheets]
    
    total_skipped = 0
    for sheet in analistas_sheets:
        df = xl.parse(sheet)
        cols = df.columns.tolist()
        col_numero = next((c for c in cols if 'MERO' in str(c).upper() or 'NÚMERO' in str(c).upper()), None)
        if col_numero:
            # Contar linhas onde numero_processo esta vazio mas Autor ou Sinistro nao estao
            skipped = df[df[col_numero].isna() & (df.iloc[:, 1:].notna().any(axis=1))].shape[0]
            print(f"{sheet}: {skipped} linhas ignoradas")
            total_skipped += skipped
    print(f"TOTAL SKIPPED: {total_skipped}")
