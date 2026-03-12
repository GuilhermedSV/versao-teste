import pandas as pd
import os

EXCEL_FILE = "ACOMPANHAMENTO PROCESSUAL 2023.xlsx"

if os.path.exists(EXCEL_FILE):
    xl = pd.ExcelFile(EXCEL_FILE)
    ignore_sheets = ['dados_referencia', 'ARQUIVADOS', 'Caroline_bkp', 'Processos']
    analistas_sheets = [s for s in xl.sheet_names if s not in ignore_sheets]
    
    for sheet in analistas_sheets:
        df = xl.parse(sheet)
        cols = [str(c).upper() for c in df.columns]
        
        # Procurar por uma coluna que pareça ser responsavel/analista
        resp_col_idx = -1
        for i, c in enumerate(cols):
            if 'RESPON' in c or 'ANALISTA' in c:
                resp_col_idx = i
                break
        
        if resp_col_idx != -1:
            col_name = df.columns[resp_col_idx]
            counts = df[col_name].value_counts()
            if len(counts) > 0:
                print(f"Aba {sheet} - Coluna '{col_name}' detectada:")
                for val, count in counts.items():
                    print(f"  -> {val}: {count}")
        else:
            print(f"Aba {sheet} - Sem coluna de responsavel interno.")
else:
    print("Excel não encontrado")
