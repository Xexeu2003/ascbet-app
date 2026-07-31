import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fpdf import FPDF
from scipy.stats import poisson
import math

st.set_page_config(page_title="Analisador V21 Poisson", layout="wide")
st.title("🚀 Analisador V21 - Poisson + Força Ataque/Defesa")

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"
LIGAS_IDS = [462, 463, 148, 3, 2, 302, 266, 262, 168]

def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        r = requests.get(API_URL, params=params, timeout=40)
        return r.json() if r.status_code == 200 else []
    except: return []

def calcular_poisson(lambda_casa, lambda_fora):
    """Calcula prob de 0-5 gols usando Poisson"""
    probs = {}
    for i in range(6):
        for j in range(6):
            prob = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_fora)
            probs[f"{i}x{j}"] = prob
    
    prob_over_0_5_ht = 1 - poisson.pmf(0, (lambda_casa + lambda_fora) / 2) # HT aprox
    prob_over_1_5 = 1 - sum([p for placar, p in probs.items() if sum(map(int, placar.split('x'))) <= 1])
    prob_over_2_5 = 1 - sum([p for placar, p in probs.items() if sum(map(int, placar.split('x'))) <= 2])
    
    return prob_over_0_5_ht, prob_over_1_5, prob_over_2_5

def calcular_forca_ataque_defesa(time_id, league_id, tipo):
    """Calcula Força Ataque e Defesa baseado nos ultimos 8 jogos"""
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
    if not isinstance(jogos, list) or len(jogos) < 3: return 1.0, 1.0, 1.4
    
    ultimos_8 = jogos[:8]
    gols_marcados = 0
    gols_sofridos = 0
    jogos_contados = 0
    
    for j in ultimos_8:
        if str(j.get('match_hometeam_id')) == str(time_id) and tipo == "home":
            gols_marcados += int(j.get('match_hometeam_score', 0))
            gols_sofridos += int(j.get('match_awayteam_score', 0))
            jogos_contados += 1
        elif str(j.get('match_awayteam_id')) == str(time_id) and tipo == "away":
            gols_marcados += int(j.get('match_awayteam_score', 0))
            gols_sofridos += int(j.get('match_hometeam_score', 0))
            jogos_contados += 1
    
    if jogos_contados == 0: return 1.0, 1.0, 1.4
    
    media_marcados = gols_marcados / jogos_contados
    media_sofridos = gols_sofridos / jogos_contados
    
    # Media de gols do campeonato
    tabela = api_call("get_standings", {"league_id": league_id})
    total_gols_liga = sum([int(t.get('all_goals_for', 0)) for t in tabela])
    total_jogos_liga = len(tabela) * 2 # aprox
    media_liga = total_gols_liga / total_jogos_liga if total_jogos_liga > 0 else 1.4
    
    forca_ataque = media_marcados / (media_liga / 2)
    forca_defesa = media_sofridos / (media_liga / 2)
    
    return forca_ataque, forca_defesa, media_liga

def calcular_probabilidade_final(casa_id, fora_id, league_id):
    """Método Poisson + Força Ataque/Defesa"""
    atq_casa, def_casa, media_liga = calcular_forca_ataque_defesa(casa_id, league_id, "home")
    atq_fora, def_fora, _ = calcular_forca_ataque_defesa(fora_id, league_id, "away")
    
    # Gols esperados
    lambda_casa = atq_casa * def_fora * (media_liga / 2)
    lambda_fora = atq_fora * def_casa * (media_liga / 2)
    
    prob_0_5_ht, prob_1_5, prob_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    
    # Probabilidade Final = Média ponderada. Você pode ajustar os pesos
    prob_final = (prob_2_5 * 0.5 + prob_1_5 * 0.3 + prob_0_5_ht * 0.2) * 100
    
    return round(prob_final), round(prob_0_5_ht*100), round(prob_1_5*100), round(prob_2_5*100), round(lambda_casa, 2), round(lambda_fora, 2)

def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Relatorio Analisador V21 - Poisson", ln=True, align="C")
    pdf.set_font("Arial", "", 7)
    for i, row in df.iterrows():
        texto = f"{row['Data']} | {row['Liga']} R{row['Rodada']} | {row['Jogo']} | Prob: {row['Prob %']}% | 2.5: {row['Prob 2.5']}% "
        pdf.cell(200, 6, texto.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    return pdf.output(dest='S').encode('latin1')

if st.button("🚀 ANALISAR COM POISSON"):
    with st.spinner("Calculando Poisson... Pode demorar 3 min no Free"):
        data_de = datetime.now().strftime("%Y-%m-%d")
        data_ate = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        jogos = api_call("get_events", {"from": data_de, "to": data_ate})
        
        resultados = []
        if isinstance(jogos, list):
            for jogo in jogos:
                if int(jogo.get('league_id', 0)) in LIGAS_IDS:
                    casa_id = jogo.get('match_hometeam_id')
                    fora_id = jogo.get('match_awayteam_id')
                    league_id = jogo.get('league_id')
                    
                    prob_final, p_0_5, p_1_5, p_2_5, lam_casa, lam_fora = calcular_probabilidade_final(casa_id, fora_id, league_id)
                    
                    if prob_final >= 70:
                        tabela = api_call("get_standings", {"league_id": league_id})
                        pos_casa = next((t['overall_league_position'] for t in tabela if str(t['team_id']) == casa_id), 'N/A')
                        pos_fora = next((t['overall_league_position'] for t in tabela if str(t['team_id']) == fora_id), 'N/A')
                        
                        resultados.append({
                            "Data": f"{jogo.get('match_date')} {jogo.get('match_time')}",
                            "Liga": jogo.get('league_name'),
                            "Rodada": jogo.get('match_round', 'N/A'),
                            "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                            "Pos": f"{pos_casa} vs {pos_fora}",
                            "Exp Gols": f"{lam_casa} x {lam_fora}",
                            "Prob 0.5 HT": f"{p_0_5}%",
                            "Prob 1.5 FT": f"{p_1_5}%",
                            "Prob 2.5 FT": f"{p_2_5}%",
                            "Prob %": prob_final
                        })
        
        if resultados:
            df = pd.DataFrame(resultados).sort_values("Prob %", ascending=False)
            st.success(f"✅ {len(df)} jogos com 70%+ encontrados via Poisson!")
            st.dataframe(df, use_container_width=True)
            
            pdf_bytes = gerar_pdf(df)
            st.download_button("📄 Baixar PDF", pdf_bytes, "relatorio_poisson.pdf", "application/pdf")
        else:
            st.info("Nenhum jogo bateu 70%+ com Poisson nos próximos 7 dias.")
