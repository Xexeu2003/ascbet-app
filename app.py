import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")
st.caption("Dados via API-Football")

# 1. PEGA A CHAVE DOS SECRETS
try:
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Chave API_KEY não encontrada nos Secrets.")
    st.stop()

# 2. FUNÇÃO PARA BUSCAR CAMPEONATOS
@st.cache_data(ttl=3600)
def buscar_campeonatos():
    url = "https://v3.football.api-sports.io/leagues"
    headers = {"x-apisports-key": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        st.error(f"Erro ao conectar na API: {e}")
        return None

# 3. BOTÃO
if st.button("Buscar Campeonatos"):
    with st.spinner("Buscando dados da API..."):
        dados = buscar_campeonatos()
    
    if dados:
        st.success(f"{len(dados)} campeonatos encontrados!")
        
        # FILTRA SÓ OS PRINCIPAIS
        lista = []
        for x in dados:
            lista.append({
                "ID": x["league"]["id"],
                "Campeonato": x["league"]["name"],
                "País": x["country"]["name"],
                "Temporada": x["seasons"][-1]["year"] if x["seasons"] else ""
            })
        
        df = pd.DataFrame(lista)
        df = df.sort_values("País")
        st.dataframe(df, use_container_width=True, height=500)
        
        st.write("Última atualização:", datetime.now().strftime("%d/%m/%Y %H:%M"))
