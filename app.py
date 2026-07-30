import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")

API_KEY = st.secrets["API_KEY"]

@st.cache_data(ttl=600) # Atualiza a cada 10min
def buscar_campeonatos():
    url = "https://v3.football.api-sports.io/leagues"
    headers = {"x-apisports-key": API_KEY}
    response = requests.get(url, headers=headers, timeout=15)
    dados = response.json()["response"]
    
    lista = []
    paises_top = ["Brazil", "England", "Spain", "Germany", "Italy", "France", "Portugal"]
    for x in dados:
        temporada_atual = x["seasons"][-1]["year"] if x["seasons"] else 0
        pais = x["country"]["name"]
        if temporada_atual >= 2024 and pais in paises_top:
            lista.append({
                "league_id": x["league"]["id"],
                "nome": x["league"]["name"],
                "pais": pais
            })
    return lista

@st.cache_data(ttl=600)
def buscar_jogos_hoje():
    hoje = date.today().isoformat()
    url = f"https://v3.football.api-sports.io/fixtures?date={hoje}"
    headers = {"x-apisports-key": API_KEY}
    response = requests.get(url, headers=headers, timeout=15)
    return response.json()["response"]

@st.cache_data(ttl=600)
def buscar_stats(time_id):
    # Pega últimos 10 jogos pra calcular %
    url = f"https://v3.football.api-sports.io/teams/statistics?team={time_id}&season=2026"
    headers = {"x-apisports-key": API_KEY}
    response = requests.get(url, headers=headers, timeout=10)
    return response.json().get("response", {})

# INTERFACE
campeonatos = buscar_campeonatos()
campeonato_selecionado = st.selectbox("Escolha o Campeonato:", [c["nome"] for c in campeonatos])
league_id = [c["league_id"] for c in campeonatos if c["nome"] == campeonato_selecionado][0]

if st.button("Gerar Relatório 70%+"):
    with st.spinner("Analisando jogos de hoje..."):
        jogos = buscar_jogos_hoje()
        jogos_filtrados = [j for j in jogos if j["league"]["id"] == league_id]
        
        relatorio = []
        for jogo in jogos_filtrados:
            home_id = jogo["teams"]["home"]["id"]
            away_id = jogo["teams"]["away"]["id"]
            
            # Aqui vamos calcular a % de Over 1.5, Over 2.5 etc
            # Por enquanto mostra só os jogos
            relatorio.append({
                "Horário": jogo["fixture"]["date"][11:16],
                "Jogo": f"{jogo['teams']['home']['name']} x {jogo['teams']['away']['name']}",
                "Status": jogo["fixture"]["status"]["short"]
            })
        
        if relatorio:
            st.success(f"{len(relatorio)} jogos encontrados hoje!")
            st.dataframe(pd.DataFrame(relatorio))
        else:
            st.warning("Nenhum jogo hoje nesse campeonato.")
