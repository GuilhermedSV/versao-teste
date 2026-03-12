import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Bruniera - Gestão Jurídica", layout="wide")

st.title("⚖️ Sistema de Gerenciamento Bruniera")
st.markdown("---")

conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url="https://huqvqyxblkkbkyzorhyc.supabase.co",
    key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh1cXZxeXhibGtrYmt5em9yaHljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2MzA5MzgsImV4cCI6MjA4ODIwNjkzOH0.vc9kdIRoC7ifM7AQlKpQZQslAT8i0RpulWZKBXpvocw",
)

# Responsáveis fixos
responsaveis = [
    "Todos",
    "Marcia",
    "Debora",
    "Victor",
    "Carmem",
    "Miguel",
    "Caroline",
    "Carolina"
]

# Sidebar
st.sidebar.header("Filtros")

busca = st.sidebar.text_input("Buscar por Processo ou Sinistro")
responsavel = st.sidebar.selectbox("Responsável", responsaveis)

# Query base
query = conn.table("processos").select("*").limit(500)

# Busca
if busca:
    query = query.or_(f"numero_processo.ilike.%{busca}%,sinistro_allianz.ilike.%{busca}%")

# Filtro responsável
if responsavel != "Todos":
    query = query.eq("responsavel", responsavel)

dados = query.execute()

if dados.data:

    df = pd.DataFrame(dados.data)

    st.subheader(f"Encontrados {len(df)} processos")

    st.dataframe(df, use_container_width=True)

else:
    st.info("Nenhum processo encontrado.")

if st.button("➕ Cadastrar Novo Processo"):
    st.success("Função de cadastro pronta para ser implementada!")