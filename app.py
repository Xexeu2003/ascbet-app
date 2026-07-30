import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="ASCbet V16", page_icon="⚽")
st.title("⚽ ASCbet V16 - Analisador Profissional")

API_KEY = "n9LSMA3Cq2j28W8oMcliM9LpHbpfRCZkjIrpjgAnXCxLTME2FwCCkWfSlrHb"

def buscar_jogos_hoje():
    hoje = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.sportmonks.com/v3/football/fixtures/date/{hoje}"
    params = {
        "api_token": API_KEY,
        "include": "participants" # pra vir nome dos times
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        st.error(f"Erro: {e}")
        return []

def analisar_jogo(jogo):
    # LÓGICA V16: Aqui entra sua análise de 70%+
    probabilidade = 75.5 
    return probabilidade

if st.button("🚀 Analisar Jogos de Hoje"):
    with st.spinner("Buscando e analisando jogos... 2-3 minutos"):
        jogos = buscar_jogos_hoje()
        
        if not jogos:
            st.error("Nenhum jogo encontrado ou erro na API.")
        else:
            aprovados = []
            for jogo in jogos[:20]: # limite pra API grátis
                prob = analisar_jogo(jogo)
                if prob >= 70:
                    time_casa = jogo['participants'][0]['name']
                    time_fora = jogo['participants'][1]['name']
                    aprovados.append({
                        "Casa": time_casa,
                        "Fora": time_fora,
                        "Probabilidade": f"{prob}%"
                    })
            
            st.success(f"Análise concluída! {len(jogos)} jogos analisados")
            
            if aprovados:
                st.subheader("=== JOGOS APROVADOS 70%+ ===")
                df = pd.DataFrame(aprovados)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("Nenhum jogo com 70%+ hoje")
