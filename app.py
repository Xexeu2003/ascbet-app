import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")
st.caption("Horário: Manaus -4 | Season: 2025")

API_KEY = st.secrets["API_KEY"]
SEASON = 2025 # MUDEI AQUI

CAMPEONATOS_FAVORITOS = {
    39: "Inglaterra - Premier League", 40: "Inglaterra - Championship", 140: "Espanha - La Liga",
    78: "Alemanha - Bundesliga", 135: "Italia - Serie A", 94: "França - Ligue 1",
    144: "Bélgica - Pro League", 88: "Holanda - Eredivisie", 119: "Dinamarca - Superliga",
    103: "Finlandia - Veikkausliiga", 106: "Noruega - Eliteserien", 71: "Brasil - Serie A",
    72: "Brasil - Serie B", 128: "Argentina - Liga Profesional", 253: "Mexico - Liga MX",
    256: "USA - MLS", 268: "Uruguai - Primera Division", 239: "Colombia - Primera A",
    292: "China - Super League", 102: "India - Super League"
}

req_count = 0 # CONTADOR

@st.cache_data(ttl=900)
def buscar_jogos_por_liga(league_id):
    global req_count
    headers = {"x-apisports-key": API_KEY}
    jogos = []
    try:
        req_count += 1
        url_last = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={SEASON}&last=10"
        r1 = requests.get(url_last, headers=headers, timeout=15)
        jogos.extend(r1.json().get("response", []))
    except: pass
    try:
        req_count += 1
        url_next = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={SEASON}&next=10"
        r2 = requests.get(url_next, headers=headers, timeout=15)
        jogos.extend(r2.json().get("response", []))
    except: pass
    
    jogos = list({j['fixture']['id']: j for j in jogos}.values())
    jogos.sort(key=lambda x: x['fixture']['date'])
    return jogos

def converter_horario(utc_str):
    utc_time = datetime.fromisoformat(utc_str.replace("Z", ""))
    return (utc_time - timedelta(hours=4)).strftime("%d/%m %H:%M")

def traduzir_status(codigo):
    status_dict = {"NS": "A Começar","1H": "1º Tempo","HT": "Intervalo","2H": "2º Tempo",
                   "FT": "Finalizado","PST": "Adiado","CANC": "Cancelado"}
    return status_dict.get(codigo, codigo)

tab1, tab2 = st.tabs(["📌 Meus Campeonatos", "🔍 Buscar Campeonato"])
league_id_final = None

with tab1:
    campeonato_selecionado = st.selectbox("Escolha da Lista:", options=sorted(list(CAMPEONATOS_FAVORITOS.values())), key="select1")
    league_id_final = [k for k, v in CAMPEONATOS_FAVORITOS.items() if v == campeonato_selecionado][0]

with tab2:
    busca = st.text_input("Digite o nome: Ex: Brasil, Espanha, Noruega", key="input_busca")
    if busca:
        resultados = {k:v for k,v in CAMPEONATOS_FAVORITOS.items() if busca.lower() in v.lower()}
        if resultados:
            campeonato_busca = st.selectbox("Resultado:", options=sorted(list(resultados.values())), key="select2")
            league_id_final = [k for k, v in resultados.items() if v == campeonato_busca][0]

if st.button("Gerar Relatório 70%+", type="primary"):
    if league_id_final is None:
        st.error("Selecione um campeonato primeiro.")
    else:
        with st.spinner("Buscando jogos..."):
            jogos = buscar_jogos_por_liga(league_id_final)
            st.info(f"Requisições gastas: {req_count}/100") # DEBUG
            
            relatorio = []
            for jogo in jogos:
                relatorio.append({
                    "fixture_id": jogo["fixture"]["id"],
                    "Data/Hora Manaus": converter_horario(jogo["fixture"]["date"]),
                    "Jogo": f"{jogo['teams']['home']['name']} x {jogo['teams']['away']['name']}",
                    "Status": traduzir_status(jogo["fixture"]["status"]["short"])
                })
            
            if relatorio:
                st.success(f"{len(relatorio)} jogos encontrados!")
                df = pd.DataFrame(relatorio)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("Nenhum jogo encontrado. Tente USA - MLS. Provável: API Free bloqueou ou estourou limite.")
