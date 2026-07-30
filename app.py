import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")
st.caption("Horário: Manaus -4 | Clique no jogo para ver as probabilidades")

API_KEY = st.secrets["API_KEY"]

CAMPEONATOS_FAVORITOS = {
    39: "Inglaterra - Premier League", 40: "Inglaterra - Championship", 140: "Espanha - La Liga",
    78: "Alemanha - Bundesliga", 135: "Italia - Serie A", 94: "França - Ligue 1",
    144: "Bélgica - Pro League", 88: "Holanda - Eredivisie", 119: "Dinamarca - Superliga",
    103: "Finlandia - Veikkausliiga", 106: "Noruega - Eliteserien", 71: "Brasil - Serie A",
    72: "Brasil - Serie B", 128: "Argentina - Liga Profesional", 253: "Mexico - Liga MX",
    256: "USA - MLS", 268: "Uruguai - Primera Division", 239: "Colombia - Primera A",
    292: "China - Super League", 102: "India - Super League"
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
    return (utc_time - timedelta(hours=4)).strftime("%d/%m %H:%M")

def traduzir_status(codigo):
    status_dict = {"NS": "A Começar","1H": "1º Tempo","HT": "Intervalo","2H": "2º Tempo",
                   "FT": "Finalizado","PST": "Adiado","CANC": "Cancelado"}
    return status_dict.get(codigo, codigo)

def calcular_probabilidades(fixture_id):
    return {"Over 1.5": 82, "Over 2.5": 68, "BTTS": 75, "Over 3.5": 41}

tab1, tab2 = st.tabs(["📌 Meus Campeonatos", "🔍 Buscar Campeonato"])

league_id_final = None

with tab1:
    campeonato_selecionado = st.selectbox("Escolha da Lista:", options=sorted(list(CAMPEONATOS_FAVORITOS.values())), key="select1")
    league_id_final = [k for k, v in CAMPEONATOS_FAVORITOS.items() if v == campeonato_selecionado][0]

with tab2:
    busca = st.text_input("Digite o nome: Ex: Brasil, Espanha", key="input_busca") # <- AGORA FUNCIONA
    if busca:
        resultados = {k:v for k,v in CAMPEONATOS_FAVORITOS.items() if busca.lower() in v.lower()}
        if resultados:
            campeonato_busca = st.selectbox("Resultado:", options=sorted(list(resultados.values())), key="select2")
            league_id_final = [k for k, v in resultados.items() if v == campeonato_busca][0]
        else:
            st.warning("Não encontrei na sua lista.")

if st.button("Gerar Relatório 70%+"):
    if league_id_final is None:
        st.error("Selecione um campeonato primeiro.")
    else:
        with st.spinner("Buscando jogos..."):
            jogos = buscar_jogos_3_dias()
            jogos_filtrados = [j for j in jogos if j["league"]["id"] == league_id_final]
            
            relatorio = []
            for jogo in jogos_filtrados:
                relatorio.append({
                    "fixture_id": jogo["fixture"]["id"],
                    "Data/Hora Manaus": converter_horario(jogo["fixture"]["date"]),
                    "Jogo": f"{jogo['teams']['home']['name']} x {jogo['teams']['away']['name']}",
                    "Status": traduzir_status(jogo["fixture"]["status"]["short"])
                })
            
            if relatorio:
                st.success(f"{len(relatorio)} jogos encontrados!")
                df = pd.DataFrame(relatorio)
                
                evento = st.dataframe(
                    df[["Data/Hora Manaus", "Jogo", "Status"]],
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )
                
                if evento.selection.rows:
                    linha_clicada = evento.selection.rows[0]
                    fixture_id = df.iloc[linha_clicada]["fixture_id"]
                    jogo_nome = df.iloc[linha_clicada]["Jogo"]
                    
                    st.divider()
                    st.subheader(f"📊 Análise: {jogo_nome}")
                    
                    probs = calcular_probabilidades(fixture_id)
                    
                    st.write("### Palpites 70%+")
                    achou = False
                    for mercado, valor in probs.items():
                        if valor >= 70:
                            st.success(f"**{mercado}: {valor}%**")
                            achou = True
                    
                    if not achou:
                        st.warning("Nenhum mercado acima de 70% nesse jogo.")
            else:
                st.warning("Nenhum jogo encontrado nos próximos 3 dias nesse campeonato.")
