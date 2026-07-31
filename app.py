import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fpdf import FPDF
from scipy.stats import poisson

st.set_page_config(page_title="Analisador V23.1", layout="wide")
st.title("🚀 Analisador V23.1 - Poisson + Força Ataque/Defesa")
st.caption("Calculo Profissional: Gols, Cantos, Cartoes | Min 70%")

# ================== CONFIG ==================
API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"

LIGAS_IDS = {
    "Brasil Serie A": 462, "Brasil Serie B": 463, "Premier League": 148,
    "Champions League": 3, "Libertadores": 2, "La Liga": 302,
    "Bundesliga": 266, "Serie A Italia": 262, "Ligue 1": 168
}
# ============================================

def safe_int(valor):
    """Converte pra int sem quebrar se vier None ou ''"""
    try:
        return int(valor) if valor is not None and valor != '' else 0
    except:
        return 0

@st.cache_data(ttl=3600)
def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        r = requests.get(API_URL, params=params, timeout=60)
        return r.json() if r.status_code == 200 else []
    except: return []

def calcular_stats_8jogos(time_id, league_id, tipo):
    """Calcula media dos ultimos 8 jogos FINALIZADOS: Gols, Cantos, Cartoes"""
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
    if not isinstance(jogos, list): return {"gols_m":1.3, "gols_s":1.3, "cantos":9.5, "cartoes":3.8}
    
    # SÓ PEGA JOGOS FINALIZADOS
    jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished']
    ultimos_8 = jogos_finalizados[:8]
    
    gols_m = gols_s = cantos = cartoes = jogos_contados = 0
    
    for j in ultimos_8:
        is_home = str(j.get('match_hometeam_id')) == str(time_id)
        if (tipo == "home" and is_home) or (tipo == "away" and not is_home):
            gols_m += safe_int(j.get('match_hometeam_score')) if is_home else safe_int(j.get('match_awayteam_score'))
            gols_s += safe_int(j.get('match_awayteam_score')) if is_home else safe_int(j.get('match_hometeam_score'))
            cantos += safe_int(j.get('match_corner_home')) + safe_int(j.get('match_corner_away'))
            cartoes += safe_int(j.get('match_yellowcards_home')) + safe_int(j.get('match_yellowcards_away')) + safe_int(j.get('match_redcards_home'))*2 + safe_int(j.get('match_redcards_away'))*2
            jogos_contados += 1
    
    if jogos_contados == 0: return {"gols_m":1.3, "gols_s":1.3, "cantos":9.5, "cartoes":3.8}
    
    return {
        "gols_m": gols_m / jogos_contados,
        "gols_s": gols_s / jogos_contados,
        "cantos": cantos / jogos_contados,
        "cartoes": cartoes / jogos_contados
    }

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
    stats_casa = calcular_stats_8jogos(casa_id, league_id, "home")
    stats_fora = calcular_stats_8jogos(fora_id, league_id, "away")
    
    tabela = api_call("get_standings", {"league_id": league_id})
    if not isinstance(tabela, list): tabela = []
    total_gols_liga = sum([safe_int(t.get('all_goals_for')) for t in tabela])
    total_jogos_liga = max(len(tabela), 1) * 2
    media_liga = total_gols_liga / total_jogos_liga if total_jogos_liga > 0 else 2.6
    
    atq_casa = stats_casa['gols_m'] / (media_liga / 2)
    def_casa = stats_casa['gols_s'] / (media_liga / 2)
    atq_fora = stats_fora['gols_m'] / (media_liga / 2)
    def_fora = stats_fora['gols_s'] / (media_liga / 2)
    
    lambda_casa = atq_casa * def_fora * (media_liga / 2)
    lambda_fora = atq_fora * def_casa * (media_liga / 2)
    
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    p_cantos = 1 - poisson.cdf(8, (stats_casa['cantos'] + stats_fora['cantos']) / 2)
    p_cartoes = 1 - poisson.cdf(3, (stats_casa['cartoes'] + stats_fora['cartoes']) / 2)
    media_h2h = calcular_h2h(casa_id, fora_id)
    
    prob_final = (p_2_5 * 0.35 + p_1_5 * 0.15 + p_0_5 * 0.1 + p_cantos * 0.2 + p_cartoes * 0.2) * 100
    
    return round(prob_final), round(p_0_5*100), round(p_1_5*100), round(p_2_5*100), round(p_cantos*100), round(p_cartoes*100), round(media_h2h, 2), stats_casa, stats_fora

def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio Analisador V23.1", ln=True, align="C")
    pdf.set_font("Arial", "", 7)
    for i, row in df.iterrows():
        texto = f"{row['Data']} | {row['Liga']} R{row['Rodada']} | {row['Jogo']} | Prob:{row['Prob %']}% | 2.5:{row['Prob 2.5']}% | Cantos:{row['Prob Cantos']}% | Cartoes:{row['Prob Cartoes']}%"
        pdf.cell(200, 5, texto.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    return pdf.output(dest='S').encode('latin1')

# ================== INTERFACE ==================
dias = st.sidebar.slider("Buscar proximos X dias", 1, 7, 3)
limite_prob = st.sidebar.slider("Probabilidade Minima %", 70, 90, 70)

if st.button("🚀 ANALISAR JOGOS 70%+"):
    with st.spinner("Calculando Poisson... Pode demorar 3 min no plano Free"):
        data_de = datetime.now().strftime("%Y-%m-%d")
        data_ate = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        jogos = api_call("get_events", {"from": data_de, "to": data_ate})
        
        resultados = []
        if isinstance(jogos, list):
            for jogo in jogos:
                if safe_int(jogo.get('league_id')) in LIGAS_IDS.values():
                    casa_id = jogo.get('match_hometeam_id')
                    fora_id = jogo.get('match_awayteam_id')
                    league_id = jogo.get('league_id')
                    
                    prob_final, p_0_5, p_1_5, p_2_5, p_cantos, p_cartoes, media_h2h, stats_casa, stats_fora = calcular_probabilidade_final(casa_id, fora_id, league_id)
                    
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
                            "Prob Cantos": f"{p_cantos}%",
                            "Prob Cartoes": f"{p_cartoes}%",
                            "Prob %": prob_final
                        })
        
        if resultados:
            df = pd.DataFrame(resultados).sort_values("Prob %", ascending=False)
            st.success(f"✅ {len(df)} jogos com {limite_prob}%+ encontrados!")
            st.dataframe(df, use_container_width=True)
            pdf_bytes = gerar_pdf(df)
            st.download_button("📄 Baixar PDF", pdf_bytes, "relatorio_v23_1.pdf", "application/pdf")
        else:
            st.info(f"Nenhum jogo bateu {limite_prob}%+ nos proximos {dias} dias.")
