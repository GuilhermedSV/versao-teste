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

PAGE_SIZE = 1000
RESPONSAVEIS_FIXOS = [
    "Miguel_1",
    "Carmem",
    "Caroline",
    "Victor",
    "Miguel",
    "Carolina",
    "Marcia",
    "Debora",
]


@st.cache_data(ttl=90)
def carregar_todos_processos():
    """Lê todos os processos por paginação para evitar corte em 1000 linhas."""
    processos = []
    inicio = 0

    while True:
        fim = inicio + PAGE_SIZE - 1
        resposta = (
            conn.table("processos")
            .select("*")
            .order("id", desc=True)
            .range(inicio, fim)
            .execute()
        )

        lote = resposta.data or []
        if not lote:
            break

        processos.extend(lote)

        if len(lote) < PAGE_SIZE:
            break

        inicio += PAGE_SIZE

    return processos


def filtrar_processos(df, busca_texto, responsavel_filtro, status_filtro):
    if df.empty:
        return df

    filtrado = df.copy()

    if status_filtro != "Todos" and "status" in filtrado.columns:
        filtrado = filtrado[filtrado["status"] == status_filtro]

    if responsavel_filtro != "Todos" and "responsavel" in filtrado.columns:
        filtrado = filtrado[filtrado["responsavel"] == responsavel_filtro]

    if busca_texto:
        busca_lower = busca_texto.lower()
        col_num = filtrado["numero_processo"].fillna("").astype(str).str.lower() if "numero_processo" in filtrado.columns else ""
        col_sin = filtrado["sinistro_allianz"].fillna("").astype(str).str.lower() if "sinistro_allianz" in filtrado.columns else ""
        col_aut = filtrado["autor"].fillna("").astype(str).str.lower() if "autor" in filtrado.columns else ""
        mask = col_num.str.contains(busca_lower) | col_sin.str.contains(busca_lower) | col_aut.str.contains(busca_lower)
        filtrado = filtrado[mask]

    return filtrado


processos = carregar_todos_processos()
df_processos = pd.DataFrame(processos)

if "processo_selecionado" not in st.session_state:
    st.session_state.processo_selecionado = None

if df_processos.empty:
    st.warning("Nenhum processo encontrado no banco.")

responsaveis_encontrados = []
if not df_processos.empty and "responsavel" in df_processos.columns:
    responsaveis_encontrados = [
        r for r in df_processos["responsavel"].fillna("").astype(str).str.strip().unique().tolist() if r
    ]

for nome in RESPONSAVEIS_FIXOS:
    if nome not in responsaveis_encontrados:
        responsaveis_encontrados.append(nome)

ordem_base = [nome for nome in RESPONSAVEIS_FIXOS if nome in responsaveis_encontrados]
extras = sorted([nome for nome in responsaveis_encontrados if nome not in RESPONSAVEIS_FIXOS])
responsaveis = ["Todos"] + ordem_base + extras

st.markdown("---")
st.subheader("📊 Painel Geral")

col1, col2, col3, col4 = st.columns(4)

total_processos = len(df_processos)
ativos = int((df_processos.get("status") == "Ativo").sum()) if not df_processos.empty and "status" in df_processos.columns else 0
encerrados = int((df_processos.get("status") == "Encerrado").sum()) if not df_processos.empty and "status" in df_processos.columns else 0
suspensos = int((df_processos.get("status") == "Suspenso").sum()) if not df_processos.empty and "status" in df_processos.columns else 0

col1.metric("⚖ Total de Processos", total_processos)
col2.metric("📂 Ativos", ativos)
col3.metric("📁 Encerrados", encerrados)
col4.metric("⏸ Suspensos", suspensos)

st.markdown("---")
st.subheader("👨‍⚖ Processos por Responsável")

if not df_processos.empty and "responsavel" in df_processos.columns:
    contagem = df_processos["responsavel"].fillna("").astype(str).str.strip()
    contagem = contagem[contagem != ""].value_counts()
    st.bar_chart(contagem)
else:
    st.info("Sem dados de responsável para exibir o gráfico.")

st.sidebar.header("Filtros")
busca = st.sidebar.text_input("Buscar por Processo, Sinistro ou Autor")
responsavel_filtro = st.sidebar.selectbox("Responsável", responsaveis)
status_filtro = st.sidebar.selectbox("Status", ["Todos", "Ativo", "Encerrado", "Suspenso"])

df_filtrado = filtrar_processos(df_processos, busca, responsavel_filtro, status_filtro)

# =========================
# PÁGINA DO PROCESSO
# =========================
if st.session_state.processo_selecionado:
    processo = st.session_state.processo_selecionado

    st.button("⬅ Voltar", on_click=lambda: st.session_state.update({"processo_selecionado": None}))

    st.header(f"📂 Processo {processo.get('numero_processo', 'Sem número')}")

    col_a, col_b, col_c = st.columns(3)
    col_a.write(f"**Autor:** {processo.get('autor', '-')}")
    col_b.write(f"**Comarca:** {processo.get('comarca', '-')}")
    col_c.write(f"**Responsável:** {processo.get('responsavel', '-')}")

    st.write(f"**Sinistro:** {processo.get('sinistro_allianz', '-')}")
    st.write(f"**Status:** {processo.get('status', '-')}")

    st.markdown("---")
    st.subheader("📜 Histórico de Andamentos")

    andamento_query = (
        conn.table("andamentos")
        .select("*")
        .eq("processo_id", processo["id"])
        .order("data_registro", desc=True, nulls_last=True)
        .execute()
    )

    if andamento_query.data:
        df_andamentos = pd.DataFrame(andamento_query.data)

        for _, andamento in df_andamentos.iterrows():
            st.markdown(
                f"""
                **{andamento.get('data_registro', '')}**  
                {andamento.get('descricao', '')}  
                _Responsável: {andamento.get('responsavel_nome', '')}_
                """
            )
            st.divider()
    else:
        st.info("Nenhum andamento registrado.")

    st.markdown("---")
    st.subheader("➕ Adicionar Andamento")

    with st.form("novo_andamento"):
        descricao = st.text_area("Descrição do Andamento")
        responsavel_nome = st.selectbox("Responsável", responsaveis[1:])
        salvar_andamento = st.form_submit_button("Salvar Andamento")

        if salvar_andamento:
            if descricao.strip():
                novo_andamento = {
                    "processo_id": processo["id"],
                    "descricao": descricao,
                    "responsavel_nome": responsavel_nome,
                }
                conn.table("andamentos").insert(novo_andamento).execute()
                st.success("Andamento registrado!")
                st.rerun()
            else:
                st.error("A descrição não pode estar vazia.")

# =========================
# LISTA DE PROCESSOS
# =========================
else:
    st.markdown("---")
    st.subheader("📂 Processos")

    if not df_filtrado.empty:
        for _, row in df_filtrado.iterrows():
            col_left, col_right = st.columns([4, 1])
            col_left.write(
                f"**{row.get('numero_processo', '')}** | {row.get('autor', '')} | {row.get('comarca', '')} | {row.get('responsavel', '')}"
            )

            if col_right.button("Abrir", key=f"abrir_{row.get('id', '')}"):
                st.session_state.processo_selecionado = row.to_dict()
                st.rerun()
    else:
        st.info("Nenhum processo encontrado com os filtros selecionados.")

st.markdown("---")
st.subheader("➕ Cadastrar Novo Processo")

with st.form("novo_processo"):
    col_p1, col_p2 = st.columns(2)

    with col_p1:
        numero_processo = st.text_input("Número do Processo")
        sinistro = st.text_input("Número do Sinistro")
        autor = st.text_input("Autor")
        comarca = st.text_input("Comarca")
        instancia = st.text_input("Instância")

    with col_p2:
        uf = st.selectbox("UF", ["RJ", "SP", "MG", "ES", "RS", "SC", "PR", "BA", "PE", "CE"])
        responsavel_novo = st.selectbox("Responsável", responsaveis[1:])
        status_novo = st.selectbox("Status", ["Ativo", "Encerrado", "Suspenso"])
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
            "responsavel": responsavel_novo,
            "status": status_novo,
            "prazo_vencimento": prazo.isoformat() if prazo else None,
        }

        conn.table("processos").insert(novo_processo).execute()
        st.cache_data.clear()
        st.success("Processo cadastrado!")
        st.rerun()
