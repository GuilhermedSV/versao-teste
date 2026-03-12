import pandas as pd
import requests
import os
from datetime import datetime

# Configurações do Supabase
SUPABASE_URL = "https://ndfpegcuwthqsjpayfmp.supabase.co"
SUPABASE_KEY = "sb_publishable_wLoOr_q9VoTj7V7VQJLgVw_oS5Fycke"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

EXCEL_FILE = "ACOMPANHAMENTO PROCESSUAL 2023.xlsx"

def clean_value(val):
    if pd.isna(val) or str(val).lower() == 'nan':
        return None
    return str(val).strip()

def sync():
    if not os.path.exists(EXCEL_FILE):
        print(f"Erro: Arquivo {EXCEL_FILE} não encontrado.")
        return

    print(f"Lendo {EXCEL_FILE}...")
    xl = pd.ExcelFile(EXCEL_FILE)
    
    # Abas a ignorar (auxiliares)
    ignore_sheets = ['dados_referencia', 'ARQUIVADOS', 'Caroline_bkp', 'Processos']
    analistas_sheets = [s for s in xl.sheet_names if s not in ignore_sheets]
    
    all_processos = []
    
    for sheet in analistas_sheets:
        print(f"Processando analista: {sheet}...")
        df = xl.parse(sheet)
        
        # Mapeamento dinâmico de colunas (tentar encontrar nomes aproximados)
        cols = df.columns.tolist()
        col_map = {
            'numero': next((c for c in cols if 'MERO' in str(c).upper() or 'NÚMERO' in str(c).upper()), None),
            'sinistro': next((c for c in cols if 'SINISTRO' in str(c).upper()), None),
            'autor': next((c for c in cols if 'AUTOR' in str(c).upper()), None),
            'comarca': next((c for c in cols if 'COMARCA' in str(c).upper()), None),
            'uf': next((c for c in cols if 'U' == str(c).strip() or 'UF' in str(c).upper()), None),
            'sistema': next((c for c in cols if 'SISTEMA' in str(c).upper()), None),
        }
        
        for _, row in df.iterrows():
            numero = clean_value(row.get(col_map['numero']))
            if not numero: continue
            
            # Pega o último andamento (última coluna preenchida da linha)
            row_clean = row.dropna()
            ultimo_andamento = row_clean.iloc[-1] if len(row_clean) > 5 else None
            
            processo = {
                "numero_processo": numero,
                "sinistro_allianz": clean_value(row.get(col_map['sinistro'])),
                "autor": clean_value(row.get(col_map['autor'])) or "N/I",
                "comarca": clean_value(row.get(col_map['comarca'])),
                "uf": clean_value(row.get(col_map['uf'])),
                "sistema": clean_value(row.get(col_map['sistema'])),
                "responsavel": sheet,
                "status": "Ativo", # Padrão para processos nas abas de analistas
                "ultimo_andamento": clean_value(ultimo_andamento)[:500] if ultimo_andamento else None,
                "data_atualizacao": datetime.now().isoformat()
            }
            all_processos.append(processo)

    print(f"Encontrados {len(all_processos)} processos. Limpando Supabase e enviando dados...")
    
    # Limpar a tabela inteira antes de começar a inserção dos novos lotes
    # Isso evita que falhas no meio do processo deixem o banco em estado inconsistente ou duplicado
    try:
        del_resp = requests.delete(f"{SUPABASE_URL}/rest/v1/processos?id=gt.0", headers=HEADERS)
        print(f"Limpeza concluída. Status: {del_resp.status_code}")
    except Exception as e:
        print(f"Erro ao limpar: {e}")

    batch_size = 100
    for i in range(0, len(all_processos), batch_size):
        batch = all_processos[i:i + batch_size]
        requests.post(f"{SUPABASE_URL}/rest/v1/processos", headers=HEADERS, json=batch)
        print(f"Enviado lote {i//batch_size + 1} de {len(all_processos)//batch_size + 1}...")

    print(f"Sincronização concluída! Total: {len(all_processos)} processos.")

    print("Sincronização concluída com sucesso!")

if __name__ == "__main__":
    sync()
