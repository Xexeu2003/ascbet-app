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

LIGAS_ODDS = {
    "soccer_brazil_campeonato": "BRASILEIRÃO SÉRIE A",
    "soccer_brazil_serie_b": "BRASILEIRÃO SÉRIE B",
    "soccer_usa_mls": "MLS - ESTADOS UNIDOS",
    "soccer_sweden_allsvenskan": "ALLSVENSKAN - SUÉCIA",
    "soccer_norway_eliteserien": "ELITESERIEN - NORUEGA"
}

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
    lamb_total = media_gols
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
            "regions": "us,uk,eu", # ADICIONEI MAIS REGIOES PRA TER MAIS ODDS
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
            log_erros.append(f"{nome_liga}: ERRO {r.status_code} - {r.text[:50]}")
            continue

        lista_jogos = r.json()
        log_erros.append(f"{nome_liga}: Encontrados {len(lista_jogos)} jogos")

        prob_base = calcular_prob_15_por_liga(MEDIA_GOLS_LIGA[liga_id])

        for item in lista_jogos:
            for book in item.get('bookmakers', []):
                for market in book.get('markets', []):
                    if market['key'] == 'totals':
                        for outcome in market['outcomes']:
                            # CORREÇÃO: CONVERTER POINT PRA FLOAT
                            if float(outcome['point']) == 1.5 and outcome['name'] == 'Over':
                                odd_over_15 = outcome['price']
                                prob_implicita = round((1 / odd_over_15) * 100, 1)
                                value = prob_base - prob_implicita
                                
                                dt = datetime.fromisoformat(item['commence_time'].replace('Z',''))
                                jogos.append({
                                    "Liga": nome_liga,
                                    "Jogo": f"{item['home_team']} x {item['away_team']}",
                                    "Data": dt.strftime("%d/%m"),
                                    "Hora": dt.strftime("%H:%M"),
                                    "Casa": book['title'], # ADICIONEI CASA DE APOSTA
                                    "Odd Over 1.5": odd_over_15,
                                    "Prob Modelo %": prob_base,
                                    "Prob Implicita %": prob_implicita,
                                    "Value %": round(value, 1),
                                    "Sinal": "GREEN" if value > 0 else "RED"
                                })
    
    log_erros.append(f"TOTAL DE REQUISICOES USADAS: {total_req}/500")
    return pd.DataFrame(jogos), log_erros

def gerar_pdf(df):
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=A4); width, height = A4; y = height - 50
    c.setFont("Helvetica-Bold", 18); c.drawCentredString(width / 2, y, f"Relatorio asc.bet V26.16.19 - THEODDS")
    y -= 30
    for liga in df['Liga'].unique():
        df_liga = df[df['Liga'] == liga].sort_values('Value %', ascending=False).head(15)
        data = [['Data', 'Hora', f'JOGO - {liga}', 'Casa', 'Odd', 'Value']]
        for index, row in df_liga.iterrows():
            data.append([row['Data'], row['Hora'], row['Jogo'][:25], row['Casa'][:10], row['Odd Over 1.5'], f"{row['Value %']}%"])
        table = Table(data, colWidths=[40,35,150,60,40,40])
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A237E")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        table.wrapOn(c, width, height); table.drawOn(c, 20, y - len(data)*14); y -= len(data)*14 + 20
        if y < 150: c.showPage(); y = height - 50
    c.save(); buffer.seek(0); return buffer

st.title("Analisador asc.bet V26.16.19 - THEODDS API FREE")
st.success("ATENÇÃO: BR A/B e MLS liberados. Limite 500 req/mes.")

if st.button("🔄 Buscar Odds REAIS"):
    st.cache_data.clear(); st.rerun()

jogos_df, erros = buscar_jogos_odds()

with st.expander("📋 Log de Status da API", expanded=True):
    for e in erros: st.code(e)

if len(jogos_df) > 0:
    min_value = st.slider("Filtro Value Minimo %", -20, 20, -5) # COMEÇA EM -5 PRA MOSTRAR TUDO
    
    df = jogos_df[jogos_df['Value %'] >= min_value].sort_values('Value %', ascending=False)
    
    qtd_green = len(df[df['Sinal']=='GREEN'])
    st.success(f"{len(df)} JOGOS ENCONTRADOS | {qtd_green} SINAIS GREEN")
    st.dataframe(df, use_container_width=True)
    
    if qtd_green > 0:
        pdf = gerar_pdf(df[df['Sinal']=='GREEN'])
        st.download_button("📄 Baixar PDF SINAIS GREEN", data=pdf, file_name=f"Relatorio_GREEN_{datetime.now().strftime('%d%m%Y')}.pdf")
else:
    st.error("Nenhum jogo encontrado. Veja o Log acima.")
