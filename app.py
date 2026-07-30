import streamlit as st
import pandas as pd

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")
st.caption("Horário: Manaus -4 | MODO DEMO ATIVO")
st.warning("API Desligada. Rodando com dados de teste.")

CAMPEONATOS_FAVORITOS = {
    39: "Inglaterra - Premier League", 106: "Noruega - Eliteserien", 
    71: "Brasil - Serie A", 256: "USA - MLS"
}

# BANCO DE DADOS FALSO COM PROBABILIDADES JÁ
JOGOS_DEMO = [
    {"fixture_id": 1, "league_id": 256, "data": "30/07 20:00", "jogo": "LA Galaxy x Inter Miami", "status": "A Começar", "probs": {"Over 1.5": 88, "BTTS": 75, "Over 2.5": 69}},
    {"fixture_id": 2, "league_id": 256, "data": "31/07 22:30", "jogo": "NYCFC x Atlanta United", "status": "A Começar", "probs": {"Over 1.5": 65, "BTTS": 58, "Over 2.5": 42}},
    {"fixture_id": 3, "league_id": 71, "data": "31/07 19:00", "jogo": "Flamengo x Palmeiras", "status": "A Começar", "probs": {"Over 1.5": 91, "BTTS": 82, "Over 3.5": 71}},
    {"fixture_id": 4, "league_id": 71, "data": "03/08 16:00", "jogo": "Corinthians x São Paulo", "status": "A Começar", "probs": {"Over 1.5": 68, "BTTS": 61, "Over 2.5": 55}},
    {"fixture_id": 5, "league_id": 106, "data": "01/08 15:00", "jogo": "Bodo/Glimt x Rosenborg", "status": "A Começar", "probs": {"Over 1.5": 85, "BTTS": 79, "Over 2.5": 72}},
]

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
        jogos = [j for j in JOGOS_DEMO if j["league_id"] == league_id_final]
        
        if jogos:
            st.success(f"{len(jogos)} jogos encontrados!")
            
            for jogo in jogos:
                st.divider()
                st.subheader(f"📊 {jogo['jogo']} - {jogo['data']}")
                
                st.write("### Palpites 70%+")
                achou = False
                for mercado, valor in jogo["probs"].items():
                    if valor >= 70:
                        st.success(f"**{mercado}: {valor}%**")
                        achou = True
                
                if not achou:
                    st.info("Nenhum mercado acima de 70% nesse jogo.")
        else:
            st.warning("Nenhum jogo de DEMO para esse campeonato.")

st.caption("Para ligar a API real: verifique sua key em https://www.api-football.com/")
