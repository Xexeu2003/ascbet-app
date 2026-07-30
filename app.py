import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import random

st.set_page_config(page_title="ASCbet V16", page_icon="⚽", layout="wide")
st.title("⚽ ASCbet V16 - Analisador Profissional")
st.caption("Probabilidade 70%+ | API-Football")

# SUA CHAVE RAPIDAPI
API_KEY = "e16821201501788a886ed8316ab5a06f"
API_HOST = "api-football-v1.p.rapidapi.com"

@st.cache_data(ttl=1800) # cache 30 min pra economizar requisição
def buscar_jogos_hoje():
    url = f"https://{API_HOST}/v3/fixtures"
    hoje = datetime.now().strftime("%Y-%m-%d")
    querystring = {"date": hoje}
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        if response.status_code == 200:
            return response.json()['response']
        else:
            st.error(f"Erro API {response.status_code}: {response.text}")
            return []
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return []

def analisar_jogo(jogo):
    # AQUI VAI SUA LÓGICA V16 REAL
    # Por enquanto simulando 68-92%
    probabilidade = round(random.uniform(68, 92), 1)
    return probabilidade

def gerar_pdf(aprovados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"ASCbet V16 - Relatorio {datetime.now().strftime('%d/%m/%Y')}", 0, 1, "C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    
    for j in aprovados:
        pdf.cell(0, 8, f"{j['Jogo']} | {j['Liga']} | Prob: {j['Probabilidade']}", 0, 1)
    
    pdf.output("relatorio_ascbet.pdf")

if st.button("🚀 Analisar Jogos de HOJE", use_container_width=True, type="primary"):
    with st.spinner("Buscando e analisando jogos... 2-3 minutos"):
        jogos = buscar_jogos_hoje()
        
        if not jogos:
            st.warning("Nenhum jogo hoje ou limite de 100 requisições estourou")
        else:
            aprovados = []
            progresso = st.progress(0, "Analisando jogos...")
            
            for i, jogo in enumerate(jogos[:80]): # limite 80 jogos pra economizar
                prob = analisar_jogo(jogo)
                if prob >= 70:
                    aprovados.append({
                        "Jogo": f"{jogo['teams']['home']['name']} vs {jogo['teams']['away']['name']}",
                        "Liga": jogo['league']['name'],
                        "País": jogo['league']['country'],
                        "Horário": jogo['fixture']['date'][11:16],
                        "Probabilidade": f"{prob}%"
                    })
                progresso.progress((i + 1) / len(jogos[:80]))
            
            st.success(f"✅ Análise concluída! {len(jogos)} jogos analisados hoje")
            
            if aprovados:
                st.subheader(f"🎯 {len(aprovados)} JOGOS APROVADOS 70%+")
                df = pd.DataFrame(aprovados)
                st.dataframe(df, use_container_width=True)
                
                if st.button("📄 Baixar Relatório PDF"):
                    gerar_pdf(aprovados)
                    with open("relatorio_ascbet.pdf", "rb") as f:
                        st.download_button("Clique para Baixar PDF", f, "relatorio_ascbet.pdf")
            else:
                st.warning("Nenhum jogo com 70%+ hoje")

st.sidebar.info(f"**DICA**: Plano FREE = 100 requisições/dia. Use 1 vez e aguarde o resultado.")
st.sidebar.warning(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
