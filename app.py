import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EBD Gamificada", layout="centered")

# --- CONEXÃO COM GOOGLE SHEETS (COM CACHE) ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# ID DA SUA PLANILHA
ID_PLANILHA = "137YLYAmAdg-l_TeHhRClR4dJMG4GIK8ZqeReFY157mQ"

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=10) # Cache rápido para atualizar logo
def carregar_dados():
    client = conectar_google_sheets()
    try:
        sheet = client.open_by_key(ID_PLANILHA).worksheet("Jovens")
        data = sheet.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=["Nome", "Presencas", "Participacoes", "Questionarios"])
            
        df = pd.DataFrame(data)
        
        # --- LIMPEZA E GARANTIA DE COLUNAS ---
        # Se a coluna Questionarios não existir (planilha velha), cria ela na memória
        if "Questionarios" not in df.columns:
            df["Questionarios"] = 0
            
        # Remove linhas de lixo (cabeçalhos repetidos ou vazios)
        df = df[df["Nome"] != "Nome"]
        df = df[df["Nome"] != ""]
        
        return df
    except:
        return pd.DataFrame(columns=["Nome", "Presencas", "Participacoes", "Questionarios"])

def salvar_dados(df):
    client = conectar_google_sheets()
    sheet = client.open_by_key(ID_PLANILHA).worksheet("Jovens")
    
    # Prepara os dados para salvar (garante que todas as colunas existem)
    cols_ordem = ["Nome", "Presencas", "Participacoes", "Questionarios"]
    
    # Verifica se o DataFrame tem todas as colunas, se não, cria com 0
    for col in cols_ordem:
        if col not in df.columns:
            df[col] = 0
            
    df_salvar = df[cols_ordem] # Reordena
    
    sheet.clear() # Limpa tudo antes de salvar para não dar erro de tamanho
    sheet.update([df_salvar.columns.values.tolist()] + df_salvar.values.tolist())
    carregar_dados.clear() # Limpa a memória

def registrar_historico(nome, acao, data_reg):
    client = conectar_google_sheets()
    spreadsheet = client.open_by_key(ID_PLANILHA)
    try:
        sheet_hist = spreadsheet.worksheet("Historico")
    except:
        sheet_hist = spreadsheet.add_worksheet(title="Historico", rows=1000, cols=10)
        sheet_hist.append_row(["Data", "Hora", "Classe", "Nome", "Acao"])
        
    hora = datetime.now().strftime("%H:%M:%S")
    sheet_hist.append_row([data_reg, hora, "Jovens", nome, acao])

# --- BARRA LATERAL (CONFIGURAÇÃO DE PESOS) ---
st.sidebar.header("⚙️ Configurar Pontos")
st.sidebar.info("Defina quanto vale cada item no domingo:")
peso_presenca = st.sidebar.number_input("Peso Presença:", value=70, step=5)
peso_participacao = st.sidebar.number_input("Peso Participação:", value=20, step=5)
peso_questionario = st.sidebar.number_input("Peso Questionário:", value=10, step=5)

# --- INTERFACE PRINCIPAL ---
st.title("🏆 EBD Gamificada")
data_hoje = datetime.now().strftime("%d/%m/%Y")
st.caption(f"📅 Data de hoje: {data_hoje}")

# Carrega Dados
df = carregar_dados()

# Converte números
cols_num = ["Presencas", "Participacoes", "Questionarios"]
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# CÁLCULO DO SCORE TOTAL (Mágica acontecendo aqui)
if not df.empty:
    df["Total Pontos"] = (df["Presencas"] * peso_presenca) + \
                         (df["Participacoes"] * peso_participacao) + \
                         (df["Questionarios"] * peso_questionario)
    
    # Ordena pelo Ranking (Quem tem mais pontos fica em cima)
    df = df.sort_values(by="Total Pontos", ascending=False).reset_index(drop=True)

# --- MÉTRICAS DA CLASSE ---
if not df.empty:
    col1, col2 = st.columns(2)
    col1.metric("Total Presenças", int(df["Presencas"].sum()))
    col2.metric("Maior Pontuação", int(df["Total Pontos"].max()) if not df.empty else 0)
else:
    st.warning("Nenhum aluno cadastrado.")

st.divider()

# --- ÁREA DE LANÇAMENTO (BOTA A MÃO NA MASSA) ---
if not df.empty:
    lista_nomes = df["Nome"].tolist()
    aluno_sel = st.selectbox("Selecione o Aluno para Pontuar:", lista_nomes)
    
    if aluno_sel:
        idx = df[df["Nome"] == aluno_sel].index[0]
        
        st.write(f"### 🎯 Aluno: **{aluno_sel}**")
        
        # COLUNAS DE AÇÃO
        c1, c2, c3 = st.columns(3)
        
        # 1. PRESENÇA
        with c1:
            st.info(f"**Presença ({peso_presenca} pts)**")
            if st.button("✅ Veio", use_container_width=True):
                df.at[idx, "Presencas"] += 1
                salvar_dados(df)
                registrar_historico(aluno_sel, "Presenca", data_hoje)
                st.toast(f"+{peso_presenca} pontos para {aluno_sel}!")
                st.rerun()
            if st.button("🔻 Tirar P.", key="rem_pres", use_container_width=True):
                if df.at[idx, "Presencas"] > 0:
                    df.at[idx, "Presencas"] -= 1
                    salvar_dados(df)
                    st.rerun()

        # 2. PARTICIPAÇÃO
        with c2:
            st.warning(f"**Partic. ({peso_participacao} pts)**")
            if st.button("🗣️ Falou", use_container_width=True):
                df.at[idx, "Participacoes"] += 1
                salvar_dados(df)
                registrar_historico(aluno_sel, "Participacao", data_hoje)
                st.toast(f"+{peso_participacao} pontos!")
                st.rerun()
            if st.button("🔻 Tirar F.", key="rem_part", use_container_width=True):
                if df.at[idx, "Participacoes"] > 0:
                    df.at[idx, "Participacoes"] -= 1
                    salvar_dados(df)
                    st.rerun()

        # 3. QUESTIONÁRIO (NOVO!)
        with c3:
            st.success(f"**Quiz ({peso_questionario} pts)**")
            if st.button("📝 Acertou", use_container_width=True):
                df.at[idx, "Questionarios"] += 1
                salvar_dados(df)
                registrar_historico(aluno_sel, "Questionario", data_hoje)
                st.toast(f"+{peso_questionario} pontos!")
                st.rerun()
            if st.button("🔻 Tirar Q.", key="rem_quest", use_container_width=True):
                if df.at[idx, "Questionarios"] > 0:
                    df.at[idx, "Questionarios"] -= 1
                    salvar_dados(df)
                    st.rerun()

        # RESUMO DO ALUNO
        st.write("---")
        pontos_aluno = df.at[idx, "Total Pontos"]
        st.metric(label="PONTUAÇÃO TOTAL ACUMULADA", value=f"{int(pontos_aluno)} Pts")

st.divider()

# --- GERENCIAMENTO (CADASTRO, REMOÇÃO E DOWNLOAD) ---
with st.expander("⚙️ Gerenciar Alunos e Planilha"):
    tab1, tab2, tab3 = st.tabs(["Novo Aluno", "Remover Aluno", "Baixar Planilha"])
    
    # ABA 1: CADASTRAR
    with tab1:
        novo_nome = st.text_input("Nome do novo aluno:")
        if st.button("💾 Salvar Aluno"):
            if novo_nome and novo_nome not in df["Nome"].values:
                novo = pd.DataFrame([{"Nome": novo_nome, "Presencas": 0, "Participacoes": 0, "Questionarios": 0}])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_dados(df)
                st.success("Cadastrado!")
                st.rerun()
            else:
                st.error("Nome vazio ou já existe.")

    # ABA 2: REMOVER (NOVO!)
    with tab2:
        st.error("⚠️ Cuidado: Isso apaga o aluno para sempre!")
        if not df.empty:
            aluno_remover = st.selectbox("Quem você quer excluir?", df["Nome"].unique())
            if st.button("🗑️ EXCLUIR ALUNO"):
                df = df[df["Nome"] != aluno_remover] # Filtra removendo o aluno
                salvar_dados(df)
                st.success(f"{aluno_remover} foi removido.")
                st.rerun()
        else:
            st.info("Lista vazia.")

    # ABA 3: DOWNLOAD (CORRIGIDO!)
    with tab3:
        st.write("Baixe a lista completa para o Excel:")
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV (Excel)",
                data=csv,
                file_name=f"relatorio_ebd_{data_hoje.replace('/','-')}.csv",
                mime="text/csv",
            )

# --- RANKING GERAL ---
st.write("---")
st.subheader("🏆 Ranking da Classe")
st.dataframe(
    df[["Nome", "Presencas", "Participacoes", "Questionarios", "Total Pontos"]],
    use_container_width=True,
    hide_index=True
)