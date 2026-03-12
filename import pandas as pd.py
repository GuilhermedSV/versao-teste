import pandas as pd
from supabase import create_client, Client

# Configurações do seu Supabase
url = "https://huqvqyxblkkbkyzorhyc.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh1cXZxeXhibGtrYmt5em9yaHljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2MzA5MzgsImV4cCI6MjA4ODIwNjkzOH0.vc9kdIRoC7ifM7AQlKpQZQslAT8i0RpulWZKBXpvocw"
supabase: Client = create_client(url, key)

def migrar_dados(caminho_csv):
    # Lendo o arquivo CSV
    # Nota: usei o separador ';' conforme identificado na sua planilha
    df = pd.read_csv(caminho_csv, sep=';')

    # Mapeamento de colunas da planilha para o Banco de Dados
    # Vamos renomear para facilitar a inserção
    mapeamento = {
        'NÚMERO': 'numero_processo',
        'COMARCA': 'comarca',
        'INSTÂNCIA': 'instancia',
        'SINISTRO ALLIANZ': 'sinistro_allianz',
        'AUTOR': 'autor',
        'Responsável': 'responsavel',
        'UF': 'uf'
    }
    
    # Selecionar e renomear as colunas úteis
    df_migracao = df[list(mapeamento.keys())].rename(columns=mapeamento)

    # Limpeza: Remover linhas onde o número do processo é nulo ou duplicado
    df_migracao = df_migracao.dropna(subset=['numero_processo'])
    df_migracao = df_migracao.drop_duplicates(subset=['numero_processo'])

    # Converter para lista de dicionários (formato que o Supabase aceita)
    registros = df_migracao.to_dict(orient='records')

    print(f"Iniciando a migração de {len(registros)} processos...")

    # Inserir no Supabase (em lotes de 100 para evitar erros de timeout)
    lote_tamanho = 100
    for i in range(0, len(registros), lote_tamanho):
        lote = registros[i : i + lote_tamanho]
        try:
            supabase.table("processos").insert(lote).execute()
            print(f"Lote {i//lote_tamanho + 1} enviado com sucesso.")
        except Exception as e:
            print(f"Erro no lote {i//lote_tamanho + 1}: {e}")

if __name__ == "__main__":
    migrar_dados('ACOMPANHAMENTO PROCESSUAL 2023(Processos).csv')