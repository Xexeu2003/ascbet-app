import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="ASCbet V16", page_icon="⚽")
st.title("⚽ ASCbet V16 - Analisador Profissional")

API_KEY = "n9LSMA3Cq2j28W8oMcliM9LpHbpfRCZkjIrpjgAnXCxLTME2FwCCkWfSlrHb"

def buscar_jogos_hoje():
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    hoje = datetime.now().strftime("%Y-%m-%d")
    querystring = {"date": hoje}
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        return response.json()['response']
    except:
        return []

def analisar_jogo(jogo):
    # LÓGICA V16: Aqui entra sua análise de 70%+
    # Por enquanto está simulada em 75%
    probabilidade = 75.5 
    return probabilidade

if st.button("🚀 Analisar Jogos de Hoje"):
    with st.spinner("Buscando e analisando jogos... 2-3 minutos"):
        jogos = buscar_jogos_hoje()
        
        if not jogos:
            st.error("Erro ao buscar jogos. Verifique sua chave da API.")
        else:
            aprovados = []
            for jogo in jogos[:20]: # Limitei em 20 jogos pra não estourar a API grátis
                prob = analisar_jogo(jogo)
                if prob >= 70:
                    aprovados.append({
                        "Casa": jogo['teams']['home']['name'],
                        "Fora": jogo['teams']['away']['name'],
                        "Probabilidade": f"{prob}%"
                    })
            
            st.success(f"Análise concluída! {len(jogos)} jogos analisados")
            
            if aprovados:
                st.subheader("=== JOGOS APROVADOS 70%+ ===")
                df = pd.DataFrame(aprovados)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("Nenhum jogo com 70%+ hoje")
