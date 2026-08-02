import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from scipy.stats import poisson
from collections import defaultdict
from fpdf import FPDF

st.set_page_config(page_title="Analisador V26.6.9", layout="wide")
st.title("Analisador V26.6.9 - asc.bet PRO")
st.caption("Horario Manaus UTC-4 | FILTRO TRIPLO ID+PAIS+LIGA")

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"

def safe_int(valor):
    try: return int(valor) if valor is not None and valor!= '' else 0
    except: return 0

@st.cache_data(ttl=1800)
def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        r = requests.get(API_URL, params=params, timeout=60)
        return r.json() if r.status_code == 200 else []
    except: return []

@st.cache_data(ttl=3600)
def get_standings(league_id):
    standings = api_call("get_standings", {"league_id": league_id})
    pos_map = {}
    if isinstance(standings, list):
        for time in standings:
            pos_map[str(time.get('team_id'))] = safe_int(time.get('overall_league_position'))
    return pos_map

@st.cache_data(ttl=3600)
def calcular_stats_5jogos(time_id, tipo):
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
    if not isinstance(jogos, list): return {"gols_m":1.5, "gols_s":1.5}
    jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished']
    ultimos_5 = jogos_finalizados[:5]
    gols_m = gols_s = jogos_contados = 0
    for j in ultimos_5:
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

def calcular_probabilidade_final(casa_id, fora_id, league_id):
    stats_casa = calcular_stats_5jogos(casa_id, "home")
    stats_fora = calcular_stats_5jogos(fora_id, "away")
    media_liga = 2.6
    divisor = media_liga / 2
    atq_casa = stats_casa['gols_m'] / divisor
    def_casa = stats_casa['gols_s'] / divisor
    atq_fora = stats_fora['gols_m'] / divisor
    def_fora = stats_fora['gols_s'] / divisor
    lambda_casa = atq_casa * def_fora * divisor
    lambda_fora = atq_fora * def_casa * divisor
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    prob_final = (p_2_5 * 60) + (p_1_5 * 30) + (p_0_5 * 10)
    prob_final = min(round(prob_final), 99)
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100)

# LIGAS CORRETAS COM PAIS
LIGAS_CORRETAS = {
    340: {"nome": "Eliteserien", "pais": "Norway"},
    356: {"nome": "Ekstraklasa", "pais": "Poland"}, 
    255: {"nome": "Primera B", "pais": "Chile"},
    250: {"nome": "LPF", "pais": "Argentina"}
}

tab1, tab2, tab3 = st.tabs(["ANALISADOR TOP 20", "BACKTEST PRO", "EXPORTAR PDF"])

with tab1:
    st.header("ANALISADOR TOP 20 - V26.6.9 FILTRO TRIPLO")
    
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        ligas_ao_vivo = st.multiselect(
            "Selecionar Ligas",
            ["Eliteserien", "Ekstraklasa", "Primera B", "LPF"],
            default=["Eliteserien", "Ekstraklasa", "Primera B", "LPF"]
        )
    with col2:
        filtro_prob_vivo = st.slider("Filtro Prob 1.5 Minima", 50, 95, 60)
    with col3:
        dias_busca = st.selectbox("Buscar Jogos", ["Hoje + 2 Dias", "Hoje + 3 Dias", "Hoje + 5 Dias"], index=0)

    if st.button("GERAR TOP 20"):
        with st.spinner("Gerando TOP 20 com Filtro Triplo..."):
            dias_map = {"Hoje + 2 Dias": 2, "Hoje + 3 Dias": 3, "Hoje + 5 Dias": 5}
            data_inicio = datetime.now()
            data_fim = data_inicio + timedelta(days=dias_map[dias_busca])

            jogos_analisados = []
            ids_foco = {k: v for k, v in LIGAS_CORRETAS.items() if v["nome"] in ligas_ao_vivo}
            
            debug_info = []

            for league_id, dados_liga in ids_foco.items():
                jogos_liga = api_call("get_events", {"league_id": league_id, "from": data_inicio.strftime("%Y-%m-%d"), "to": data_fim.strftime("%Y-%m-%d")})
                debug_info.append(f"Liga ID {league_id} - {dados_liga['nome']}: {len(jogos_liga) if isinstance(jogos_liga, list) else 0} jogos retornados")

                if not isinstance(jogos_liga, list): continue
                standings_cache = get_standings(league_id)

                for jogo in jogos_liga:
                    pais_jogo = jogo.get('country_name')
                    liga_jogo = jogo.get('league_name')
                    
                    # FILTRO TRIPLO: ID + PAIS + LIGA
                    if pais_jogo == dados_liga["pais"] and dados_liga["nome"] in liga_jogo:
                        try:
                            casa_id = jogo.get('match_hometeam_id')
                            fora_id = jogo.get('match_awayteam_id')
                            prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, league_id)

                            if p_1_5 >= filtro_prob_vivo:
                                gols_ft = safe_int(jogo.get('match_hometeam_score')) + safe_int(jogo.get('match_awayteam_score'))
                                rodada = jogo.get('league_round') if jogo.get('league_round') else "N/A"
                                pos_casa = standings_cache.get(str(casa_id), '-')
                                pos_fora = standings_cache.get(str(fora_id), '-')
                                stats_casa = calcular_stats_5jogos(casa_id, "home")
                                stats_fora = calcular_stats_5jogos(fora_id, "away")
                                gc_u8 = round((stats_casa['gols_s'] + stats_fora['gols_s'])/2, 2)
                                gf_u8 = round((stats_casa['gols_m'] + stats_fora['gols_m'])/2, 2)
                                pais_sigla = pais_jogo[:2].upper()

                                jogos_analisados.append({
                                    "Data": f"{jogo.get('match_date')} {jogo.get('match_time')}",
                                    "Liga": f"[{pais_sigla}] {liga_jogo}",
                                    "Rod": rodada,
                                    "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                    "Pos": f"{pos_casa} vs {pos_fora}",
                                    "H2H": "N/A",
                                    "GC U8": gc_u8,
                                    "GF U8": gf_u8,
                                    "Prob 0.5": p_0_5,
                                    "Prob 1.5": p_1_5,
                                    "Prob 2.5": p_2_5,
                                    "Prob %": prob_final
                                })
                        except: continue
            
            st.info("DEBUG API:")
            for d in debug_info: st.text(d)

            if jogos_analisados:
                df_top = pd.DataFrame(jogos_analisados)
                df_top = df_top.sort_values("Prob 1.5", ascending=False).head(20)
                st.success(f"TOP 20 GERADO - {len(df_top)} jogos com Prob 1.5 >= {filtro_prob_vivo}%")
                def color_prob(val):
                    if val >= 90: return 'background-color: #28a745; color: white; font-weight: bold'
                    elif val >= 85: return 'background-color: #ffc107; color: black; font-weight: bold'
                    else: return ''
                st.dataframe(df_top.style.map(color_prob, subset=['Prob 0.5', 'Prob 1.5', 'Prob 2.5', 'Prob %']), use_container_width=True)
            else:
                st.warning(f"Nenhum jogo encontrado com Prob >= {filtro_prob_vivo}% nas ligas selecionadas")

# As outras 2 abas ficam iguais a anterior
with tab2: st.header("BACKTEST PRO - V26.6.9")
with tab3: st.header("EXPORTAR RELATORIO PDF")
