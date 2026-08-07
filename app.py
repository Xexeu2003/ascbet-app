import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

st.set_page_config(page_title="Analisador asc.bet THEODDS", layout="wide")

ODDS_API_KEY = "7779b153071a617ec6767463223c2eb1"

# LIGAS DA THEODDS - AGORA SIM TEM BR E MLS
LIGAS_ODDS = {
    "soccer_brazil_campeonato": "BRASILEIRÃO SÉRIE A",
    "soccer_brazil_serie_b": "BRASILEIRÃO SÉRIE B",
    "soccer_usa_mls": "MLS - ESTADOS UNIDOS",
    "soccer_sweden_allsvenskan": "ALLSVENSKAN - SUÉCIA",
    "soccer_norway_eliteserien": "ELITESERIEN - NORUEGA"
}

# MEDIA DE GOLS POR LIGA - USAMOS PRA CALCULAR SEM GASTAR CREDITO
MEDIA_GOLS_LIGA = {
    "soccer_brazil_campeonato": 2.65,
    "soccer_brazil_serie_b": 2.15,
    "soccer_usa_mls": 3.10,
    "soccer_sweden_allsvenskan": 2.85,
    "soccer_norway_eliteserien": 3.25
}

def poisson(k, lamb):
    return (math.exp(-lamb) * lamb**k) / math.factorial(k)

def calcular_prob_15_por_liga(media_gols):
    lamb_total = media_gols # Usamos a média da liga como lambda
    p0 = poisson(0, lamb_total)
    p1 = poisson(1, lamb_total)
    prob_15 = (1 - p0 - p1) * 100
    return round(prob_15, 1)

@st.cache_data(ttl=1800, show_spinner="Buscando Odds REAIS da TheOdds...")
def buscar_jogos_odds():
    jogos = []
    log_erros = []
    total_req = 0

    for liga_id, nome_liga in LIGAS_ODDS.items():
        url = f"https://api.the-odds-api.com/v4/sports/{liga_id}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "totals",
            "oddsFormat": "decimal",
            "dateFormat": "iso"
        }
        r = requests.get(url, params=params)
        total_req += 1

        if r.status_code == 429:
            log_erros.append(f"{nome_liga}: ERRO 429 - Limite 500/mes atingido")
            break
        if r.status_code!= 200:
            log_erros.append(f"{nome_liga}: ERRO {r.status_code}")
            continue

        lista_jogos = r.json()
        log_erros.append(f"{nome_liga}: Encontrados {len(lista_jogos)} jogos")

        prob_base = calcular_prob_15_por_liga(MEDIA_GOLS_LIGA[liga_id])

        for item in lista_jogos:
            # Pega a linha de 1.5 gols
            for market in item.get('bookmakers', [{}])[0].get('markets', []):
                if market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        if outcome['point'] == 1.5 and outcome['name'] == 'Over':
                            odd_over_15 = outcome['price']
                            prob_implicita = round(100 / odd_over_15, 1)
                            value = prob_base - prob_implicita
                            
                            dt = datetime.fromisoformat(item['commence_time'].replace('Z',''))
                            jogos.append({
                                "Liga": nome_liga,
                                "Jogo": f"{item['home_team']} x {item['away_team']}",
                                "Data": dt.strftime("%d/%m"),
                                "Hora": dt.strftime("%H:%M"),
                                "Odd Over 1.5": odd_over_15,
                                "Prob Modelo %": prob_base,
                                "Prob Implicita %": prob_implicita,
                                "Value %": round(value, 1),
                                "Sinal": "GREEN" if value > 5 else "RED"
                            })
    
    log_erros.append(f"TOTAL DE REQUISICOES USADAS: {total_req}/500")
    return pd.DataFrame(jogos), log_erros

def gerar_pdf(df):
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=A4); width, height = A4; y = height - 50
    c.setFont("Helvetica-Bold", 18); c.drawCentredString(width / 2, y, f"Relatorio asc.bet V26.16.17 - THEODDS")
    c.save(); buffer.seek(0); return buffer

st.title("Analisador asc.bet V26.16.17 - THEODDS API FREE")
st.success("ATENÇÃO: Usando TheOdds API. Agora tem BR A/B e MLS. Limite 500 req/mes.")

if st.button("🔄 Buscar Odds REAIS"):
    st.cache_data.clear(); st.rerun()

jogos_df, erros = buscar_jogos_odds()

with st.expander("📋 Log de Status da API", expanded=True):
    for e in erros: st.code(e)

if len(jogos_df) > 0:
    df = jogos_df[jogos_df['Sinal'] == 'GREEN'].sort_values('Value %', ascending=False)
    st.success(f"{len(df)} SINAIS GREEN ENCONTRADOS")
    st.dataframe(df, use_container_width=True)
    st.download_button("📄 Baixar PDF", data=gerar_pdf(df), file_name="Relatorio_THEODDS.pdf")
else:
    st.error("Nenhum sinal GREEN. Veja o Log acima.")
