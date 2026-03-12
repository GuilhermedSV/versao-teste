import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Bruniera - Gestão Jurídica", layout="wide")

st.title("⚖️ Sistema de Gerenciamento Bruniera")

conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url="https://huqvqyxblkkbkyzorhyc.supabase.co",
    key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh1cXZxeXhibGtrYmt5em9yaHljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2MzA5MzgsImV4cCI6MjA4ODIwNjkzOH0.vc9kdIRoC7ifM7AQlKpQZQslAT8i0RpulWZKBXpvocw",
)

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
# CONTROLE DE PÁGINA
# =========================

if "processo_selecionado" not in st.session_state:
    st.session_state.processo_selecionado = None

# =========================
# PÁGINA DO PROCESSO
# =========================

if st.session_state.processo_selecionado:

    processo = st.session_state.processo_selecionado

    st.button("⬅ Voltar", on_click=lambda: st.session_state.update({"processo_selecionado": None}))

    st.header(f"📂 Processo {processo['numero_processo']}")

    col1, col2, col3 = st.columns(3)

    col1.write(f"**Autor:** {processo['autor']}")
    col2.write(f"**Comarca:** {processo['comarca']}")
    col3.write(f"**Responsável:** {processo['responsavel']}")

    st.write(f"**Sinistro:** {processo['sinistro_allianz']}")
    st.write(f"**Status:** {processo['status']}")

    st.markdown("---")

    st.subheader("📜 Histórico de Andamentos")

    andamento_query = conn.table("andamentos")\
        .select("*")\
        .eq("processo_id", processo["id"])\
        .order("data_registro", desc=True, nulls_last=True)\
        .execute()

    if andamento_query.data:

    df_andamentos = pd.DataFrame(andamento_query.data)

    for _, andamento in df_andamentos.iterrows():

        st.markdown(
            f"""
            **{andamento['data_registro']}**  
            {andamento['descricao']}  
            _Responsável: {andamento['responsavel_nome']}_
            """
        )

        st.divider()

else:

    st.info("Nenhum andamento registrado.")

    st.markdown("---")

    st.subheader("➕ Adicionar Andamento")

    with st.form("novo_andamento"):

        descricao = st.text_area("Descrição do Andamento")

        responsavel_nome = st.selectbox(
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

        salvar_andamento = st.form_submit_button("Salvar Andamento")

        if salvar_andamento and descricao.strip():

            novo_andamento = {
                "processo_id": processo["id"],
                "descricao": descricao,
                "responsavel_nome": responsavel_nome
            }

            conn.table("andamentos").insert(novo_andamento).execute()

            st.success("Andamento registrado!")

            st.rerun()

# =========================
# LISTA DE PROCESSOS
# =========================

else:

    st.sidebar.header("Filtros")

    busca = st.sidebar.text_input("Buscar por Processo ou Sinistro")

    responsavel = st.sidebar.selectbox(
        "Responsável",
        responsaveis
    )

    query = conn.table("processos").select("*").range(0,2000)

    if status_filtro != "Todos":
    query = query.eq("status", status_filtro)

    if busca:
        query = query.or_(f"numero_processo.ilike.%{busca}%,sinistro_allianz.ilike.%{busca}%")

    if responsavel != "Todos":
        query = query.eq("responsavel", responsavel)

    dados = query.execute()

    if dados.data:

        df = pd.DataFrame(dados.data)

        st.subheader("📂 Processos")

        for _, row in df.iterrows():

            col1, col2 = st.columns([4,1])

            col1.write(
                f"**{row['numero_processo']}** | {row['autor']} | {row['comarca']} | {row['responsavel']}"
            )

            if col2.button("Abrir", key=row["id"]):

                st.session_state.processo_selecionado = row

                st.rerun()

    else:

        st.info("Nenhum processo encontrado.")

    st.markdown("---")

    st.subheader("➕ Cadastrar Novo Processo")

    with st.form("novo_processo"):

        col1, col2 = st.columns(2)

        with col1:

            numero_processo = st.text_input("Número do Processo")
            sinistro = st.text_input("Número do Sinistro")
            autor = st.text_input("Autor")
            comarca = st.text_input("Comarca")
            instancia = st.text_input("Instância")

        with col2:

            uf = st.selectbox("UF", ["RJ","SP","MG","ES","RS","SC","PR","BA","PE","CE"])

            responsavel = st.selectbox(
                "Responsável",
                responsaveis[1:]
            )

            status_filtro = st.sidebar.selectbox(
                "Status",
               ["Todos", "Ativo", "Encerrado", "Suspenso"]
            )

            status = st.selectbox(
                "Status",
                ["Ativo","Encerrado","Suspenso"]
            )

            prazo = st.date_input("Prazo de Vencimento")

        salvar = st.form_submit_button("Salvar Processo")

        if salvar:

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

            conn.table("processos").insert(novo_processo).execute()

            st.success("Processo cadastrado!")

            st.rerun()