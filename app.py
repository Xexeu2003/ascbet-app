import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from scipy.stats import poisson
from collections import defaultdict

st.set_page_config(page_title="Analisador V26.7.1", layout="wide")
st.title("Analisador V26.7.1 - asc.bet PRO")
st.caption("Horario Manaus UTC-4 | 40 Ligas | Estavel")

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"

def safe_int(valor):
    try: return int(valor) if valor is not None and valor!= '' else 0
    except: return 0

@st.cache_data(ttl=300)
def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        r = requests.get(API_URL, params=params, timeout=60)
        return r.json() if r.status_code == 200 else []
    except: return []

@st.cache_data(ttl=3600)
def calcular_stats_8jogos(time_id, tipo):
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
    if not isinstance(jogos, list): return {"gols_m":1.5, "gols_s":1.5}
    jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished']
    ultimos_8 = jogos_finalizados[:8]
    gols_m = gols_s = jogos_contados = 0
    for j in ultimos_8:
        is_home = str(j.get('match_hometeam_id')) == str(time_id)
        if (tipo == "home" and is_home) or (tipo == "away" and not is_home):
            gols_m += safe_int(j.get('match_hometeam_score')) if is_home else safe_int(j.get('match_awayteam_score'))
            gols_s += safe_int(j.get('match_awayteam_score')) if is_home else safe_int(j.get('match_hometeam_score'))
            jogos_contados += 1
    if jogos_contados == 0: return {"gols_m":1.5, "gols_s":1.5}
    return {"gols_m": gols_m / jogos_contados, "gols_s": gols_s / jogos_contados}

def calcular_poisson(lambda_casa, lambda_fora):
    prob_0_5_ht = 1 - poisson.pmf(0, (lambda_casa + lambda_fora) / 2)
    prob_1_5 = 1 - poisson.cdf(1, lambda_casa + lambda_fora)
    prob_2_5 = 1 - poisson.cdf(2, lambda_casa + lambda_fora)
    return prob_0_5_ht, prob_1_5, prob_2_5

@st.cache_data(ttl=3600)
def calcular_probabilidade_final(casa_id, fora_id, league_id):
    stats_casa = calcular_stats_8jogos(casa_id, "home")
    stats_fora = calcular_stats_8jogos(fora_id, "away")
    media_liga = 2.7
    divisor = media_liga / 2
    atq_casa = stats_casa['gols_m'] / divisor
    def_casa = stats_casa['gols_s'] / divisor
    atq_fora = stats_fora['gols_m'] / divisor
    def_fora = stats_fora['gols_s'] / divisor
    lambda_casa = atq_casa * def_fora * divisor
    lambda_fora = atq_fora * def_casa * divisor
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    prob_final = (p_2_5 * 70) + (p_1_5 * 20) + (p_0_5 * 10)
    prob_final = min(round(prob_final), 99)
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100)

# 40 LIGAS
LIGAS_MAP = {
    462:"Brasileirao A", 463:"Brasileirao B", 148:"Premier League", 152:"Championship",
    149:"La Liga", 207:"La Liga 2", 175:"Bundesliga", 176:"2. Bundesliga",
    262:"Serie A", 263:"Serie B", 168:"Ligue 1", 169:"Ligue 2",
    302:"K League 1", 303:"K League 2", 310:"J1 League", 311:"J2 League",
    253:"Campeonato Chileno", 255:"Primera B Chile", 339:"Allsvenskan", 340:"Eliteserien",
    341:"Superliga Dinamarca", 342:"Veikkausliiga", 343:"Premier League Russia",
    344:"MLS", 345:"Liga MX", 346:"Eredivisie", 347:"Liga Portugal",
    348:"Super Lig Turquia", 349:"Premier League Ucrania", 350:"Besta deild karla",
    351:"Superliga Grecia", 352:"Liga I Romania", 353:"Premijer Liga Bosnia",
    354:"HNL Croacia", 355:"Fortuna Liga Tcheca", 356:"Ekstraklasa Polonia",
    357:"Superliga Suica", 358:"Austrian Bundesliga", 359:"Jupiler Pro League",
    271:"Superliga Chinesa", 128:"Liga Profesional Argentina", 250:"Liga BetPlay Dimayor"
}

tab1, tab2 = st.tabs(["ANALISADOR AO VIVO", "BACKTEST"])

# ABA 1: AO VIVO
with tab1:
    st.header("ANALISADOR AO VIVO - 40 LIGAS")
    st.warning("API gratis = 100 chamadas/dia. Selecione max 5 ligas")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ligas_ao_vivo = st.multiselect(
            "Selecionar Ligas", 
            list(LIGAS_MAP.values()), 
            default=["K League 1", "J1 League", "Brasileirao A"]
        )
    with col2:
        filtro_prob_vivo = st.slider("Filtro Prob Minima", 70, 95, 80)
    with col3:
        if st.button("ATUALIZAR AO VIVO"):
            st.rerun()
    
    with st.spinner("Buscando jogos ao vivo..."):
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        jogos_hoje = api_call("get_events", {"from": data_hoje, "to": data_hoje})
        
        jogos_ao_vivo = []
        if isinstance(jogos_hoje, list):
            ids_foco = [k for k, v in LIGAS_MAP.items() if v in ligas_ao_vivo]
            for jogo in jogos_hoje:
                league_id = safe_int(jogo.get('league_id'))
                status = jogo.get('match_status')
                
                if league_id in ids_foco and status not in ['Finished', 'Not Started', 'Postponed', 'Cancelled']:
                    try:
                        casa_id = jogo.get('match_hometeam_id')
                        fora_id = jogo.get('match_awayteam_id')
                        prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, league_id)
                        
                        if p_1_5 >= filtro_prob_vivo:
                            jogos_ao_vivo.append({
                                "Hora": jogo.get('match_time'),
                                "Liga": LIGAS_MAP.get(league_id),
                                "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                "Placar": f"{jogo.get('match_hometeam_score')} x {jogo.get('match_awayteam_score')}",
                                "Minuto": jogo.get('match_status'),
                                "Prob 1.5": p_1_5,
                                "Prob 2.5": p_2_5
                            })
                    except: continue
        
        if jogos_ao_vivo:
            df_vivo = pd.DataFrame(jogos_ao_vivo).sort_values("Prob 1.5", ascending=False)
            st.success(f"ENCONTRADOS {len(df_vivo)} JOGOS COM +{filtro_prob_vivo}%")
            st.dataframe(df_vivo, use_container_width=True)
        else:
            st.warning("Nenhum jogo ao vivo encontrado. Baixe o filtro ou adicione ligas")

# ABA 2: BACKTEST
with tab2:
    st.header("BACKTEST - 40 LIGAS")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        data_inicio = st.date_input("Data Inicio", datetime(2025,8,1).date())
    with col2:
        data_fim = st.date_input("Data Fim", datetime(2025,9,30).date())
    with col3:
        stake = st.number_input("Stake R$", 1, 1000, 10)
    with col4:
        odd_real = st.number_input("Odd", 1.10, 3.00, 1.90, 0.05)
    
    ligas_selecionadas = st.multiselect("Selecionar Ligas", list(LIGAS_MAP.values()), default=["K League 1", "J1 League"])
    limite_bt = st.slider("Prob Minima", 60, 90, 70)

    if st.button("RODAR BACKTEST"):
        with st.spinner("Rodando backtest..."):
            data_de = data_inicio.strftime("%Y-%m-%d")
            data_ate = data_fim.strftime("%Y-%m-%d")

            resultados_bt = []
            stats = {"0.5HT": {"total":0, "green":0}, "1.5FT": {"total":0, "green":0}, "2.5FT": {"total":0, "green":0}}
            ranking_ligas = defaultdict(lambda: {"total":0, "green":0})

            ids_filtro = [k for k, v in LIGAS_MAP.items() if v in ligas_selecionadas]
            
            for league_id in ids_filtro:
                jogos = api_call("get_events", {"league_id": league_id, "from": data_de, "to": data_ate})
                
                if not isinstance(jogos, list): continue
                jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished'][:30]

                for jogo in jogos_finalizados:
                    try:
                        casa_id = jogo.get('match_hometeam_id')
                        fora_id = jogo.get('match_awayteam_id')
                        nome_liga = LIGAS_MAP.get(league_id, "Outra")
                        prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, league_id)

                        if prob_final >= limite_bt:
                            gols_ht = safe_int(jogo.get('match_hometeam_score_ht')) + safe_int(jogo.get('match_awayteam_score_ht'))
                            gols_ft = safe_int(jogo.get('match_hometeam_score')) + safe_int(jogo.get('match_awayteam_score'))

                            green_05 = gols_ht >= 1
                            green_15 = gols_ft >= 2
                            green_25 = gols_ft >= 3

                            if p_0_5 >= limite_bt:
                                stats["0.5HT"]["total"] += 1
                                if green_05: stats["0.5HT"]["green"] += 1
                            if p_1_5 >= limite_bt:
                                stats["1.5FT"]["total"] += 1
                                if green_15: stats["1.5FT"]["green"] += 1
                                ranking_ligas[nome_liga]["total"] += 1
                                if green_15: ranking_ligas[nome_liga]["green"] += 1
                            if p_2_5 >= limite_bt:
                                stats["2.5FT"]["total"] += 1
                                if green_25: stats["2.5FT"]["green"] += 1

                            resultados_bt.append({
                                "Data": jogo.get('match_date'),
                                "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                "Liga": nome_liga,
                                "Prob 1.5": p_1_5, "Prob 2.5": p_2_5,
                                "FT": gols_ft,
                                "1.5FT": "GREEN" if green_15 else "RED"
                            })
                    except: continue

            if resultados_bt:
                df_bt = pd.DataFrame(resultados_bt)
                
                taxa_15 = (stats['1.5FT']['green'] / stats['1.5FT']['total'] * 100) if stats['1.5FT']['total'] > 0 else 0
                total_apostado = stats['1.5FT']['total'] * stake
                lucro = (stats['1.5FT']['green'] * stake * (odd_real - 1)) - ((stats['1.5FT']['total'] - stats['1.5FT']['green']) * stake)
                roi = (lucro / total_apostado) * 100 if total_apostado > 0 else 0
                
                col1, col2 = st.columns(2)
                col1.metric("Taxa 1.5FT", f"{taxa_15:.1f}%", f"{stats['1.5FT']['green']}/{stats['1.5FT']['total']}")
                col2.metric("ROI 1.5FT", f"{roi:.1f}%", f"R${lucro:.2f}")

                st.dataframe(df_bt, use_container_width=True)
            else:
                st.error("Nenhum jogo encontrado")
