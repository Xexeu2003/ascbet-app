import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fpdf import FPDF
from scipy.stats import poisson
import time

st.set_page_config(page_title="Analisador V24.3", layout="wide")
st.title("🚀 Analisador V24.3 - 40 Ligas + Filtros PRO")
st.caption("Calculo Profissional: Gols | Cores | Top 10 | PDF Tabela")

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
    media_liga = 2.7
    divisor = media_liga / 2
    atq_casa = stats_casa['gols_m'] / divisor
    def_casa = stats_casa['gols_s'] / divisor
    atq_fora = stats_fora['gols_m'] / divisor
    def_fora = stats_fora['gols_s'] / divisor
    lambda_casa = atq_casa * def_fora * divisor
    lambda_fora = atq_fora * def_casa * divisor
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    media_h2h = calcular_h2h(casa_id, fora_id)
    bonus_h2h = (media_h2h / 3.0) * 10
    prob_final = (p_2_5 * 70) + (p_1_5 * 20) + (p_0_5 * 10) + bonus_h2h
    prob_final = min(round(prob_final), 99)
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100), round(media_h2h, 2), stats_casa, stats_fora

def cor_prob(val): # CORRIGIDO PRA VERSAO NOVA
    if val >= 90: return 'background-color: #d4edda; color: #155724'
    elif val >= 80: return 'background-color: #fff3cd; color: #856404'
    else: return 'background-color: #ffeeba; color: #856404'

def gerar_pdf(df):
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Relatorio Analisador V24.3 - {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(3)
    pdf.set_font("Arial", "B", 6)
    pdf.cell(22, 8, "Data", 1); pdf.cell(40, 8, "Liga", 1); pdf.cell(12, 8, "Rod", 1, 0, 'C')
    pdf.cell(75, 8, "Jogo", 1); pdf.cell(18, 8, "Pos", 1, 0, 'C'); pdf.cell(15, 8, "H2H", 1, 0, 'C')
    pdf.cell(15, 8, "GC U8", 1, 0, 'C'); pdf.cell(15, 8, "GF U8", 1, 0, 'C')
    pdf.cell(18, 8, "Prob 2.5", 1, 0, 'C'); pdf.cell(15, 8, "Prob %", 1, 1, 'C')
    
    pdf.set_font("Arial", "", 6)
    for i, row in df.iterrows():
        fill = True if i % 2 == 0 else False
        if fill: pdf.set_fill_color(240, 240, 240)
        pdf.cell(22, 6, str(row.get('Data','N/A')).encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(40, 6, str(row.get('Liga','N/A'))[:22].encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(12, 6, str(row.get('Rodada','N/A')), 1, 0, 'C', fill)
        pdf.cell(75, 6, str(row.get('Jogo','N/A'))[:38].encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(18, 6, str(row.get('Pos','N/A')), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(row.get('Media H2H 5J',0)), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(row.get('Gols Casa U8',0)), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(row.get('Gols Fora U8',0)), 1, 0, 'C', fill)
        pdf.cell(18, 6, str(row.get('Prob 2.5 FT','0%')), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(row.get('Prob %',0))+"%", 1, 1, 'C', fill)
    
    return bytes(pdf.output())

st.sidebar.header("⚙️ Filtros")
dias = st.sidebar.slider("Buscar proximos X dias", 1, 14, 7)
limite_prob = st.sidebar.slider("Probabilidade Minima %", 60, 90, 70)
mostrar_top10 = st.sidebar.checkbox("Mostrar apenas TOP 10")

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
            if mostrar_top10: df = df.head(10)
            
            st.success(f"✅ {len(df)} jogos com {limite_prob}%+ encontrados! Analisados: {jogos_analisados}")
            
            # CORRECAO AQUI: TROQUEI applymap POR map
            st.dataframe(
                df.style.map(cor_prob, subset=['Prob %']),
                use_container_width=True
            )
            pdf_bytes = gerar_pdf(df)
            st.download_button("📄 Baixar PDF", pdf_bytes, "relatorio_v24_3.pdf", "application/pdf")
        else:
            st.warning(f"Nenhum jogo bateu {limite_prob}%+. Analisados: {jogos_analisados} jogos. Tente 65%")
