import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fpdf import FPDF
from scipy.stats import poisson
import time

st.set_page_config(page_title="Analisador V23.6", layout="wide")
st.title("🚀 Analisador V23.6 - 40 Ligas + Mais Assertivo")
st.caption("Calculo Profissional: Gols | Min 70%")

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"

LIGAS_IDS = {
    "Brasil Serie A": 462, "Brasil Serie B": 463, "Brasil Serie C": 464, "Brasil Serie D": 465,
    "Premier League": 148, "Championship": 149, "Champions League": 3, "Europa League": 4,
    "Libertadores": 2, "Sulamericana": 7, "La Liga": 302, "La Liga 2": 303,
    "Bundesliga": 266, "Bundesliga 2": 267, "Serie A Italia": 262, "Serie B Italia": 263,
    "Ligue 1": 168, "Ligue 2": 169, "Eredivisie": 244, "Primeira Liga": 94,
    "MLS": 253, "Liga MX": 206, "Argentina LPF": 10, "Colombia": 32,
    "Chile": 29, "Uruguai": 116, "Paraguai": 83, "Ecuador": 37,
    "Turquia": 482, "Holanda": 244, "Belgica": 144, "Portugal": 94,
    "Russia": 406, "Ucrania": 488, "Austria": 132, "Suica": 444,
    "Escocia": 172, "Grecia": 207
}

def safe_int(valor):
    try: return int(valor) if valor is not None and valor != '' else 0
    except: return 0

@st.cache_data(ttl=3600)
def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        time.sleep(0.5)
        r = requests.get(API_URL, params=params, timeout=60)
        return r.json() if r.status_code == 200 else []
    except: return []

def calcular_stats_8jogos(time_id, tipo):
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
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

def calcular_h2h(casa_id, fora_id):
    h2h = api_call("get_H2H", {"firstTeamId": casa_id, "secondTeamId": fora_id})
    if not isinstance(h2h, list): return 2.5
    jogos_finalizados = [j for j in h2h if j.get('match_status') == 'Finished']
    ultimos_5 = jogos_finalizados[:5]
    total_gols = sum([safe_int(j.get('match_hometeam_score')) + safe_int(j.get('match_awayteam_score')) for j in ultimos_5])
    return total_gols / len(ultimos_5) if ultimos_5 else 2.5

def calcular_probabilidade_final(casa_id, fora_id, league_id):
    stats_casa = calcular_stats_8jogos(casa_id, "home")
    stats_fora = calcular_stats_8jogos(fora_id, "away")
    
    media_liga = 2.7 # Fixa pra não depender da tabela
    
    divisor = media_liga / 2
    atq_casa = stats_casa['gols_m'] / divisor
    def_casa = stats_casa['gols_s'] / divisor
    atq_fora = stats_fora['gols_m'] / divisor
    def_fora = stats_fora['gols_s'] / divisor
    
    lambda_casa = atq_casa * def_fora * divisor
    lambda_fora = atq_fora * def_casa * divisor
    
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    media_h2h = calcular_h2h(casa_id, fora_id)
    
    # FORMULA V23.6 MAIS REALISTA
    bonus_h2h = (media_h2h / 3.0) * 10 # Bonus de ate 10% se H2H for 3.0
    prob_final = (p_2_5 * 70) + (p_1_5 * 20) + (p_0_5 * 10) + bonus_h2h
    
    prob_final = min(round(prob_final), 99) # LIMITE 99%
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100), round(media_h2h, 2), stats_casa, stats_fora

def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio Analisador V23.6", ln=True, align="C")
    pdf.set_font("Arial", "", 8)
    for i, row in df.iterrows():
        texto = f"{row.get('Data')} | {row.get('Liga')} | {row.get('Jogo')} | 2.5:{row.get('Prob 2.5 FT')} | Prob:{row.get('Prob %')}%"
        pdf.cell(200, 6, texto.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    return pdf.output()

dias = st.sidebar.slider("Buscar proximos X dias", 1, 14, 7)
limite_prob = st.sidebar.slider("Probabilidade Minima %", 60, 90, 70)

if st.button("🚀 ANALISAR JOGOS 70%+"):
    with st.spinner("Analisando 40 ligas... Aguarde 3 min"):
        data_de = datetime.now().strftime("%Y-%m-%d")
        data_ate = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        jogos = api_call("get_events", {"from": data_de, "to": data_ate})
        resultados = []
        jogos_analisados = 0
        if isinstance(jogos, list):
            for jogo in jogos:
                if safe_int(jogo.get('league_id')) in LIGAS_IDS.values():
                    jogos_analisados += 1
                    try:
                        casa_id = jogo.get('match_hometeam_id')
                        fora_id = jogo.get('match_awayteam_id')
                        league_id = jogo.get('league_id')
                        prob_final, p_0_5, p_1_5, p_2_5, media_h2h, stats_casa, stats_fora = calcular_probabilidade_final(casa_id, fora_id, league_id)
                        if prob_final >= limite_prob:
                            tabela = api_call("get_standings", {"league_id": league_id})
                            pos_casa = next((t['overall_league_position'] for t in tabela if str(t.get('team_id')) == str(casa_id)), 'N/A')
                            pos_fora = next((t['overall_league_position'] for t in tabela if str(t.get('team_id')) == str(fora_id)), 'N/A')
                            resultados.append({
                                "Data": f"{jogo.get('match_date')} {jogo.get('match_time')}",
                                "Liga": jogo.get('league_name'),
                                "Rodada": jogo.get('match_round', 'N/A'),
                                "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                "Pos": f"{pos_casa} vs {pos_fora}",
                                "Gols Casa U8": f"{stats_casa['gols_m']:.2f}",
                                "Gols Fora U8": f"{stats_fora['gols_m']:.2f}",
                                "Media H2H 5J": media_h2h,
                                "Prob 0.5 HT": f"{p_0_5}%",
                                "Prob 2.5 FT": f"{p_2_5}%",
                                "Prob %": prob_final
                            })
                    except: continue
        if resultados:
            df = pd.DataFrame(resultados).sort_values("Prob %", ascending=False)
            st.success(f"✅ {len(df)} jogos com {limite_prob}%+ encontrados! Analisados: {jogos_analisados}")
            st.dataframe(df, use_container_width=True)
            pdf_bytes = gerar_pdf(df)
            st.download_button("📄 Baixar PDF", pdf_bytes, "relatorio_v23_6.pdf", "application/pdf")
        else:
            st.warning(f"Nenhum jogo bateu {limite_prob}%+. Analisados: {jogos_analisados} jogos. Tente 65%")
