import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

# Configuração da página
st.set_page_config(page_title="Bruniera - Gestão Jurídica", layout="wide")

st.title("⚖️ Sistema de Gerenciamento Bruniera")
st.markdown("---")

# Conexão com Supabase
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

# =========================
# SIDEBAR FILTROS
# =========================

st.sidebar.header("Filtros")

busca = st.sidebar.text_input("Buscar por Processo ou Sinistro")

responsavel_filtro = st.sidebar.selectbox(
    "Responsável",
    responsaveis
)

# =========================
# BUSCA NO BANCO
# =========================

query = conn.table("processos").select("*").limit(500)

if busca:
    query = query.or_(f"numero_processo.ilike.%{busca}%,sinistro_allianz.ilike.%{busca}%")

if responsavel_filtro != "Todos":
    query = query.eq("responsavel", responsavel_filtro)

dados = query.execute()

# =========================
# TABELA DE PROCESSOS
# =========================

if dados.data:

    df = pd.DataFrame(dados.data)

    st.subheader(f"📂 Encontrados {len(df)} processos")

    st.dataframe(
        df[
            [
                "numero_processo",
                "sinistro_allianz",
                "autor",
                "comarca",
                "responsavel",
                "status",
                "prazo_vencimento",
            ]
        ],
        use_container_width=True
    )

else:

    st.info("Nenhum processo encontrado.")

# =========================
# FORMULÁRIO NOVO PROCESSO
# =========================

st.markdown("---")
st.subheader("➕ Cadastrar Novo Processo")

with st.form("form_novo_processo"):

    col1, col2 = st.columns(2)

    with col1:

        numero_processo = st.text_input("Número do Processo")

        sinistro = st.text_input("Número do Sinistro")

        autor = st.text_input("Autor")

        comarca = st.text_input("Comarca")

        instancia = st.text_input("Instância")

    with col2:

        uf = st.selectbox(
            "UF",
            [
                "RJ","SP","MG","ES","RS","SC","PR",
                "BA","PE","CE","GO","DF"
            ]
        )

        responsavel = st.selectbox(
            "Responsável",
            [
                "Marcia",
                "Debora",
                "Victor",
                "Carmem",
                "Miguel",
                "Caroline",
                "Carolina"
            ]
        )

        status = st.selectbox(
            "Status",
            [
                "Ativo",
                "Encerrado",
                "Suspenso"
            ]
        )

        prazo = st.date_input("Prazo de Vencimento")

    salvar = st.form_submit_button("Salvar Processo")

    if salvar:

        if not numero_processo:

            st.error("Número do processo é obrigatório.")

        else:

            novo_processo = {
                "numero_processo": numero_processo,
                "sinistro_allianz": sinistro,
                "autor": autor,
                "comarca": comarca,
                "instancia": instancia,
                "uf": uf,
                "responsavel": responsavel,
                "status": status,
                "prazo_vencimento": prazo.isoformat() if prazo else None
            }

            try:

                conn.table("processos").insert(novo_processo).execute()

                st.success("✅ Processo cadastrado com sucesso!")

                st.rerun()

            except Exception as e:

                st.error(f"Erro ao cadastrar: {e}")