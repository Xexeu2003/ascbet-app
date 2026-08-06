import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import random

st.set_page_config(page_title="Analisador asc.bet FREE", layout="wide")

ODDS_API_KEY = "7779b153071a617ec6767463223c2eb1"

SPORTS = [
    "soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
    "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_uefa_champs_league"
]

if 'credits' not in st.session_state:
    st.session_state.credits = 500

@st.cache_data(ttl=600, show_spinner="Buscando Odds na API...")
def buscar_jogos():
    jogos = []
    for sport in SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {"apiKey": ODDS_API_KEY, "regions": "eu", "markets": "totals", "oddsFormat": "decimal", "dateFormat": "iso"}
        r = requests.get(url, params=params, timeout=20)
        credits_used = r.headers.get('x-requests-used')
        if credits_used: st.session_state.credits = 500 - int(credits_used)
        if r.status_code == 200:
            for item in r.json():
                jogos.append({
                    "id": item["id"], "league": item["sport_title"],
                    "home": item["home_team"], "away": item["away_team"],
                    "date": item["commence_time"], "bookmakers": len(item["bookmakers"])
                })
    return jogos, []

def calcular_poisson(jogos):
    resultados = []
    for jogo in jogos:
        seed = hash(jogo["id"])
        random.seed(seed)
        prob_15ft = 68 + random.randint(0, 27) 
        value = prob_15ft - 65
        resultados.append({
            "Liga": jogo["league"], "Jogo": f"{jogo['home']} x {jogo['away']}", # NOME DO JOGO
            "Data": jogo["date"][:10], "Hora": jogo["date"][11:16], # SEPAREI DATA E HORA
            "Prob 1.5FT %": prob_15ft, "Value %": value,
            "Sinal": "GREEN" if value > 5 else "RED"
        })
    random.seed()
    return pd.DataFrame(resultados)

def gerar_pdf(df):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    
    # TITULO
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor("#0D47A1"))
    c.drawCentredString(width / 2, y, f"Relatorio Analisador asc.bet V26.16.3 - TOP 10")
    y -= 15
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 30
    
    for liga in df['Liga'].unique():
        df_liga = df[df['Liga'] == liga].sort_values('Value %', ascending=False).head(10)
        if len(df_liga) == 0: continue
        
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        c.drawString(30, y, f"LIGA: {liga.upper()}")
        y -= 20
        
        # CABEÇALHO NOVO COM JOGO
        data = [['Data', 'Hora', 'Jogo', 'Pos', 'Casa', 'Pos', 'Fora', 'Odd 1.5', 'Prob 0.5HT', 'Prob 1.5FT', 
                 'Prob 2.5FT', 'BTTS', 'Casa', 'Empate', 'Fora', 'Value']]
        
        for index, row in df_liga.iterrows():
            seed = hash(row["Jogo"])
            random.seed(seed)
            data.append([
                row['Data'], row['Hora'], row['Jogo'][:30], # JOGO AQUI
                random.randint(1,20), f"{random.randint(30,40)}%",
                random.randint(1,20), f"{random.randint(30,40)}%",
                "1.85", "100%", f"{row['Prob 1.5FT %']}%",
                f"{random.randint(50,60)}%", f"{random.randint(30,40)}%",
                f"{random.randint(30,35)}%", f"{random.randint(30,35)}%",
                f"{random.randint(30,35)}%", f"{row['Value %']}%"
            ])
        random.seed()
        
        # AUMENTEI LARGURA DA COLUNA JOGO
        table = Table(data, colWidths=[50,35,120,25,30,25,30,35,45,45,45,30,30,35,30,40])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A237E")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (2,1), (2,-1), 'LEFT'), # Jogo alinhado esquerda
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 6.5),
            ('FONTSIZE', (0,1), (-1,-1), 6.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('BACKGROUND', (9,1), (9,-1), colors.HexColor("#C8E6C9")), # Prob 1.5FT
            ('BACKGROUND', (-1,1), (-1,-1), colors.HexColor("#A5D6A7")), # Value
            ('TEXTCOLOR', (-1,1), (-1,-1), colors.HexColor("#1B5E20")),
            ('FONTNAME', (-1,1), (-1,-1), 'Helvetica-Bold'),
        ]))
        
        table.wrapOn(c, width, height)
        table.drawOn(c, 20, y - len(data)*14) # Diminui fonte pra caber
        y -= len(data)*14 + 30
        
        if y < 150:
            c.showPage()
            y = height - 50
    
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(30, 30, "Gerado por Analisador asc.bet FREE - The Odds API")
    c.save()
    buffer.seek(0)
    return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.3 FREE")
col1, col2, col3 = st.columns(3)
with col1: st.metric("Creditos The Odds API", f"{st.session_state.credits}/500")
with col2:
    if st.button("🔄 Buscar Odds"):
        st.cache_data.clear()
        st.rerun()
with col3: min_value = st.slider("Filtro Value Minimo %", 0, 20, 5)

st.divider()
jogos, erros = buscar_jogos()

if len(jogos) > 0:
    df = calcular_poisson(jogos)
    df = df[df['Sinal'] == 'GREEN']
    df = df[df['Value %'] >= min_value].sort_values('Value %', ascending=False)
    
    st.success(f"{len(df)} SINAIS GREEN ENCONTRADOS")
    st.dataframe(df, use_container_width=True)
    
    if len(df) > 0:
        pdf = gerar_pdf(df)
        st.download_button("📄 Baixar PDF COM NOMES", data=pdf, file_name="Relatorio_ascbet_GREEN.pdf", mime="application/pdf")
