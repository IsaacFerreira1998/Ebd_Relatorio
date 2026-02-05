import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EBD Jovens", layout="centered")

# --- CONEXÃO COM GOOGLE SHEETS (COM CACHE DE RECURSO) ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# --- ID DA SUA PLANILHA ---
ID_PLANILHA = "137YLYAmAdg-l_TeHhRClR4dJMG4GIK8ZqeReFY157mQ"

# --- FUNÇÕES DE DADOS (COM CACHE DE DADOS) ---
@st.cache_data(ttl=60) # Guarda os dados na memória por 60 segundos
def carregar_dados():
    client = conectar_google_sheets()
    try:
        # Abre a planilha pelo ID
        sheet = client.open_by_key(ID_PLANILHA).worksheet("Jovens")
        data = sheet.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=["Nome", "Presencas", "Participacoes", "Performance"])
            
        df = pd.DataFrame(data)
        
        # --- CORREÇÃO DO BUG "NOME" ---
        # Remove linhas onde o Nome é igual a "Nome" ou vazio
        df = df[df["Nome"] != "Nome"]
        df = df[df["Nome"] != ""]
        
        return df
    except Exception as e:
        # Se der erro (ex: aba não existe), retorna vazio pra não quebrar
        return pd.DataFrame(columns=["Nome", "Presencas", "Participacoes", "Performance"])

def salvar_dados(df):
    client = conectar_google_sheets()
    sheet = client.open_by_key(ID_PLANILHA).worksheet("Jovens")
    # Atualiza a planilha
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    # LIMPA O CACHE para mostrar os dados novos imediatamente
    carregar_dados.clear()

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

# --- INTERFACE ---
st.title("📊 EBD - Jovens 2026")
data_hoje = datetime.now().strftime("%d/%m/%Y")
st.write(f"📅 **{data_hoje}**")

# Carrega os dados (Usando a memória inteligente)
df = carregar_dados()

# Converte números
cols_num = ["Presencas", "Participacoes", "Performance"]
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# --- MÉTRICAS ---
if not df.empty:
    total_pres = int(df["Presencas"].sum())
    total_part = int(df["Participacoes"].sum())
    c1, c2 = st.columns(2)
    c1.metric("Total Presenças", total_pres)
    c2.metric("Total Participação", total_part)
else:
    st.info("Conectado! Aguardando cadastros.")

st.divider()

# --- CADASTRAR ALUNO ---
with st.expander("➕ Cadastrar Novo Aluno"):
    nome_novo = st.text_input("Nome:")
    if st.button("Salvar Aluno"):
        if nome_novo:
            # Verifica duplicidade
            nomes_existentes = df["Nome"].astype(str).tolist()
            if nome_novo in nomes_existentes:
                st.warning("Já existe!")
            else:
                novo = pd.DataFrame([{"Nome": nome_novo, "Presencas": 0, "Participacoes": 0, "Performance": 0.0}])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_dados(df)
                registrar_historico(nome_novo, "Cadastro", data_hoje)
                st.success("Cadastrado!")
                st.rerun()

st.divider()

# --- LISTA DE CHAMADA ---
if not df.empty:
    # Filtra apenas nomes válidos para a lista
    lista_nomes = df["Nome"].unique()
    aluno = st.selectbox("Selecione o Aluno:", lista_nomes)
    
    if aluno:
        # Encontra o índice do aluno
        idx = df[df["Nome"] == aluno].index[0]
        
        # Botões
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Presença")
            if st.button("✅ Presente", key="p_add"):
                df.at[idx, "Presencas"] += 1
                salvar_dados(df)
                registrar_historico(aluno, "Presenca", data_hoje)
                st.rerun()
                
            if st.button("❌ Anular", key="p_rem"):
                if df.at[idx, "Presencas"] > 0:
                    df.at[idx, "Presencas"] -= 1
                    salvar_dados(df)
                    registrar_historico(aluno, "Anulou Presenca", data_hoje)
                    st.rerun()

        with c2:
            st.caption("Ponto Extra")
            if st.button("➕ Ponto", key="pt_add"):
                df.at[idx, "Participacoes"] += 1
                salvar_dados(df)
                registrar_historico(aluno, "Ponto Extra", data_hoje)
                st.rerun()
                
            if st.button("🔻 Tirar", key="pt_rem"):
                if df.at[idx, "Participacoes"] > 0:
                    df.at[idx, "Participacoes"] -= 1
                    salvar_dados(df)
                    registrar_historico(aluno, "Anulou Ponto", data_hoje)
                    st.rerun()

        # Resumo
        st.write("---")
        pres = df.at[idx, "Presencas"]
        part = df.at[idx, "Participacoes"]
        perf = round(part/pres, 1) if pres > 0 else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Presenças", pres)
        m2.metric("Pontos", part)
        m3.metric("Nota", perf)

# --- TABELA FINAL ---
st.write("---")
with st.expander("Ver Planilha Completa"):
    st.dataframe(df)