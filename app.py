import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import toml

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EBD Relatório", layout="mobile")

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Pega as credenciais dos "Secrets" do Streamlit
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# --- FUNÇÕES DE DADOS ---
def carregar_dados(aba_nome):
    client = conectar_google_sheets()
    # Substitua pelo NOME DA SUA PLANILHA EXATO
    sheet = client.open("Relatorio_EBD_2026").worksheet(aba_nome)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def salvar_dados(df, aba_nome):
    client = conectar_google_sheets()
    sheet = client.open("Relatorio_EBD_2026").worksheet(aba_nome)
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

def registrar_historico(nome, acao, data, classe):
    client = conectar_google_sheets()
    try:
        # Tenta abrir a aba Historico, se não existir, cria (manual ou ignora erro)
        sheet_hist = client.open("Relatorio_EBD_2026").worksheet("Historico")
        hora = datetime.now().strftime("%H:%M:%S")
        linha = [data, hora, classe, nome, acao]
        sheet_hist.append_row(linha)
    except:
        pass # Se não tiver aba Historico, segue a vida

# --- INTERFACE GRÁFICA ---
st.title("📊 Controle EBD 2026")
st.caption("Sistema de Gestão de Alunos")

# SELEÇÃO DE CLASSE
modo_atual = st.sidebar.selectbox("Selecione a Classe:", ["Jovens", "Adolescentes"])

# CARREGAR DADOS
try:
    df = carregar_dados(modo_atual)
    
    # Garantir que as colunas numéricas são números mesmo
    df["Presencas"] = pd.to_numeric(df["Presencas"], errors="coerce").fillna(0).astype(int)
    df["Participacoes"] = pd.to_numeric(df["Participacoes"], errors="coerce").fillna(0).astype(int)
    
    # DATA DE HOJE
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    st.sidebar.write(f"📅 Data: **{data_hoje}**")

    # --- MÉTRICAS GERAIS (TOPO) ---
    total_presencas = df["Presencas"].sum()
    total_participacao = df["Participacoes"].sum()
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total Presenças", total_presencas)
    col_m2.metric("Total Participações", total_participacao)
    
    st.divider()

    # --- LISTA DE ALUNOS E AÇÕES ---
    lista_alunos = df["Nome"].tolist()
    aluno_sel = st.selectbox("Selecione o Aluno:", lista_alunos)

    if aluno_sel:
        # Pega os dados do aluno selecionado
        dados_aluno = df[df["Nome"] == aluno_sel].iloc[0]
        
        # Mostra estatística individual
        st.write(f"### 👤 {aluno_sel}")
        c_a, c_b, c_c = st.columns(3)
        c_a.metric("Presenças", dados_aluno["Presencas"])
        c_b.metric("Pontos", dados_aluno["Participacoes"])
        c_c.metric("Performance", f"{dados_aluno['Performance']}")
        
        st.write("---")
        
        # --- BOTÕES DE AÇÃO (ATUALIZADO COM REMOVER) ---
        
        # 1. CONTROLE DE PRESENÇA
        st.write("📅 **Controle de Presença**")
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            if st.button("✅ Marcar Presença", use_container_width=True):
                idx = df[df["Nome"] == aluno_sel].index[0]
                df.at[idx, "Presencas"] += 1
                
                # Recalcula Performance
                p = df.at[idx, "Presencas"]
                part = df.at[idx, "Participacoes"]
                df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                
                salvar_dados(df, modo_atual)
                registrar_historico(aluno_sel, "Presenca", data_hoje, modo_atual)
                st.toast(f"Presença marcada para {aluno_sel}!")
                st.rerun()

        with col_p2:
            if st.button("❌ Tirar Presença", use_container_width=True):
                idx = df[df["Nome"] == aluno_sel].index[0]
                if df.at[idx, "Presencas"] > 0:
                    df.at[idx, "Presencas"] -= 1
                    
                    # Recalcula Performance
                    p = df.at[idx, "Presencas"]
                    part = df.at[idx, "Participacoes"]
                    df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                    
                    salvar_dados(df, modo_atual)
                    registrar_historico(aluno_sel, "ANULADO - Presenca", data_hoje, modo_atual)
                    st.toast(f"Presença removida de {aluno_sel}!")
                    st.rerun()
                else:
                    st.warning("O aluno já tem 0 presenças.")

        st.write("") # Espaço vazio

        # 2. CONTROLE DE PARTICIPAÇÃO
        st.write("🗣️ **Controle de Participação**")
        col_pt1, col_pt2 = st.columns(2)
        
        with col_pt1:
            if st.button("➕ Ponto Extra", use_container_width=True):
                idx = df[df["Nome"] == aluno_sel].index[0]
                df.at[idx, "Participacoes"] += 1
                
                # Recalcula Performance
                p = df.at[idx, "Presencas"]
                part = df.at[idx, "Participacoes"]
                df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                
                salvar_dados(df, modo_atual)
                registrar_historico(aluno_sel, "Ponto Extra", data_hoje, modo_atual)
                st.toast(f"Ponto adicionado para {aluno_sel}!")
                st.rerun()

        with col_pt2:
            if st.button("🔻 Tirar Ponto", use_container_width=True):
                idx = df[df["Nome"] == aluno_sel].index[0]
                if df.at[idx, "Participacoes"] > 0:
                    df.at[idx, "Participacoes"] -= 1
                    
                    # Recalcula Performance
                    p = df.at[idx, "Presencas"]
                    part = df.at[idx, "Participacoes"]
                    df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                    
                    salvar_dados(df, modo_atual)
                    registrar_historico(aluno_sel, "ANULADO - Ponto", data_hoje, modo_atual)
                    st.toast(f"Ponto removido de {aluno_sel}!")
                    st.rerun()
                else:
                    st.warning("O aluno já tem 0 pontos.")

    # --- TABELA COMPLETA NO FINAL ---
    st.divider()
    st.subheader(f"Tabela Geral - {modo_atual}")
    st.dataframe(df)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.info("Verifique se a planilha 'Relatorio_EBD_2026' existe e tem as abas 'Jovens' e 'Adolescentes'.")