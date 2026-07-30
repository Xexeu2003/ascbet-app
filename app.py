import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")

try:
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Chave API_KEY não encontrada nos Secrets.")
    st.stop()

@st.cache_data(ttl=3600)
def buscar_campeonatos():
    url = "https://v3.football.api-sports.io/leagues"
    headers = {"x-apisports-key": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        dados = response.json()
        
        # DEBUG: Mostra se deu erro na API
        if dados.get("errors"):
            st.error(f"Erro da API: {dados['errors']}")
            return None
            
        return dados["response"]
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return None

if st.button("Buscar Campeonatos"):
    with st.spinner("Buscando dados da API..."):
        dados = buscar_campeonatos()
    
    if dados:
        # FILTRA SÓ TEMPORADA 2025/2026 E PAÍSES PRINCIPAIS
        lista = []
        paises_top = ["Brazil", "England", "Spain", "Germany", "Italy", "France", "Portugal"]
        
        for x in dados:
            temporada_atual = x["seasons"][-1]["year"] if x["seasons"] else 0
            pais = x["country"]["name"]
            
            if temporada_atual >= 2024 and pais in paises_top:
                lista.append({
                    "ID": x["league"]["id"],
                    "Campeonato": x["league"]["name"],
                    "País": pais,
                    "Temporada": temporada_atual
                })
        
        if len(lista) == 0:
            st.warning("Nenhum campeonato encontrado. Verifique sua chave.")
        else:
            st.success(f"{len(lista)} campeonatos encontrados!")
            df = pd.DataFrame(lista)
            st.dataframe(df, use_container_width=True)
