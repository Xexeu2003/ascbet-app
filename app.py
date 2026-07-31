import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Analisador V19", layout="wide")
st.title("🚀 Analisador de Futebol V19 - Free Trial")

# ================== CONFIG ==================
API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://api.apifootball.com/"

# Suas Ligas Prioritárias - ID das ligas do API-Football
LIGAS_IDS = {
    "Brasil Serie A": 462,
    "Brasil Serie B": 463,
    "Premier League": 148,
    "Champions League": 3,
    "Libertadores": 2,
    "La Liga": 302,
    "Bundesliga": 266,
    "Serie A Italia": 262,
    "Ligue 1": 168
}
# ============================================

def buscar_jogos(data_de, data_ate):
    """Busca jogos nos próximos 7 dias"""
    params = {
        "action": "get_events",
        "from": data_de,
        "to": data_ate,
        "APIkey": API_KEY
    }
    try:
        response = requests.get(API_URL, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro API: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return []

def calcular_probabilidade(jogo):
    """
    AQUI ENTRA SUA LÓGICA V16 REAL
    Por enquanto deixei um simulador pra testar se tá puxando dados
    Troque isso pela sua lógica de 70%+
    """
    # Exemplo: Simula uma prob entre 50% e 90%
    import random
    prob = random.randint(50, 90)
    return prob

st.sidebar.header("Filtros")
dias = st.sidebar.slider("Buscar próximos X dias", 1, 7, 3)
limite_prob = st.sidebar.slider("Probabilidade Mínima %", 60, 90, 70)

if st.button("🚀 Analisar Próximos 7 DIAS"):
    with st.spinner("Buscando jogos na API... Isso pode demorar 1 min no Free"):
        data_de = datetime.now().strftime("%Y-%m-%d")
        data_ate = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        
        todos_jogos = buscar_jogos(data_de, data_ate)
        
        if not todos_jogos:
            st.warning("Nenhum jogo encontrado ou erro na API. Confere se o IP foi liberado.")
        else:
            resultados = []
            for jogo in todos_jogos:
                league_id = int(jogo.get('league_id', 0))
                
                # Filtra só pelas ligas que você quer
                if league_id in LIGAS_IDS.values():
                    prob = calcular_probabilidade(jogo)
                    
                    # Filtra só 70%+
                    if prob >= limite_prob:
                        resultados.append({
                            "Data": jogo['event_date'],
                            "Liga": jogo['league_name'],
                            "Jogo": f"{jogo['match_hometeam_name']} vs {jogo['match_awayteam_name']}",
                            "Prob %": prob,
                            "Sugestão": "OVER 2.5" if prob > 75 else "BTTS" # Exemplo
                        })
            
            if resultados:
                df = pd.DataFrame(resultados)
                st.success(f"✅ Encontrados {len(df)} jogos com {limite_prob}%+ de chance!")
                st.dataframe(df, use_container_width=True)
            else:
                st.info(f"Nenhum jogo encontrado com {limite_prob}%+ nos próximos {dias} dias.")
