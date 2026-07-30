import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")
st.caption("Horário: Manaus -4 | Puxa: Ontem, Hoje e Amanhã")

API_KEY = st.secrets["API_KEY"]

# SUA LISTA DE CAMPEONATOS FAVORITOS
CAMPEONATOS_FAVORITOS = {
    39: "Inglaterra - Premier League",
    40: "Inglaterra - Championship",
    140: "Espanha - La Liga",
    78: "Alemanha - Bundesliga",
    135: "Italia - Serie A",
    94: "França - Ligue 1",
    144: "Bélgica - Pro League",
    88: "Holanda - Eredivisie",
    119: "Dinamarca - Superliga",
    103: "Finlandia - Veikkausliiga",
    106: "Noruega - Eliteserien",
    71: "Brasil - Serie A",
    72: "Brasil - Serie B",
    128: "Argentina - Liga Profesional",
    253: "Mexico - Liga MX",
    256: "USA - MLS",
    268: "Uruguai - Primera Division",
    239: "Colombia - Primera A",
    292: "China - Super League",
    102: "India - Super League"
}

@st.cache_data(ttl=600)
def buscar_jogos_3_dias():
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    amanha = hoje + timedelta(days=1)
    datas = [ontem.isoformat(), hoje.isoformat(), amanha.isoformat()]
    
    todos_jogos = []
    for d in datas:
        url = f"https://v3.football.api-sports.io/fixtures?date={d}"
        headers = {"x-apisports-key": API_KEY}
        response = requests.get(url, headers=headers, timeout=15)
        todos_jogos.extend(response.json()["response"])
    return todos_jogos

def converter_horario(utc_str):
    utc_time = datetime.fromisoformat(utc_str.replace("Z", ""))
    horario_br = utc_time - timedelta(hours=4) # Manaus -4
    return horario_br.strftime("%d/%m %H:%M")

# ABAS
tab1, tab2 = st.tabs(["📌 Meus Campeonatos", "🔍 Buscar Campeonato"])

with tab1:
    campeonato_selecionado = st.selectbox("Escolha da Lista:", options=sorted(list(CAMPEONATOS_FAVORITOS.values())))
    league_id = [k for k, v in CAMPEONATOS_FAVORITOS.items() if v == campeonato_selecionado][0]

with tab2:
    busca = st.text_input("Digite o nome: Ex: Brasil, Espanha")
    league_id_busca = None
    if busca:
        resultados = {k:v for k,v in CAMPEONATOS_FAVORITOS.items() if busca.lower() in v.lower()}
        if resultados:
            campeonato_selecionado = st.selectbox("Resultado:", options=sorted(list(resultados.values())))
            league_id_busca = [k for k, v in resultados.items() if v == campeonato_selecionado][0]
        else:
            st.warning("Não encontrei na sua lista.")

league_id_final = league_id_busca if league_id_busca else league_id

if st.button("Gerar Relatório 70%+"):
    with st.spinner("Buscando jogos de Ontem, Hoje e Amanhã..."):
        jogos = buscar_jogos_3_dias()
        jogos_filtrados = [j for j in jogos if j["league"]["id"] == league_id_final]
        
        relatorio = []
        for jogo in jogos_filtrados:
            horario_br = converter_horario(jogo["fixture"]["date"])
            
            status = jogo["fixture"]["status"]["short"]
            if status == "NS": status = "A Começar"
            elif status == "FT": status = "Finalizado"
            elif status == "1H": status = "1º Tempo"
            elif status == "2H": status = "2º Tempo"
            
            relatorio.append({
                "Data/Hora Manaus": horario_br,
                "Jogo": f"{jogo['teams']['home']['name']} x {jogo['teams']['away']['name']}",
                "Status": status
            })
        
        if relatorio:
            st.success(f"{len(relatorio)} jogos encontrados!")
            df = pd.DataFrame(relatorio)
            st.dataframe(df.sort_values("Data/Hora Manaus"), use_container_width=True)
        else:
            st.warning("Nenhum jogo encontrado nos próximos 3 dias nesse campeonato.")
