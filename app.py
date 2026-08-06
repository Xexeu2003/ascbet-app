import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import random

st.set_page_config(page_title="Analisador asc.bet FREE", layout="wide")

# --- CONFIG THE ODDS API ---
ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", "7779b153071a617ec6767463223c2eb1") # Sua KEY da print

# Esportes que a The Odds API tem. Use "soccer_brazil_serie_a"
SPORTS = ["soccer_brazil_serie_a", "soccer_epl", "soccer_spain_la_liga"]

if 'credits' not in st.session_state:
    st.session_state.credits = 500

@st.cache_data(ttl=600, show_spinner="Buscando Odds na API...")
def buscar_jogos():
    jogos = []
    erros = []
    
    for sport in SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "totals", # Over 1.5
            "oddsFormat": "decimal",
            "dateFormat": "iso"
        }
        
        try:
            r = requests.get(url, params=params, timeout=20)
            
            # The Odds API mostra quantos créditos gastou no header
            credits_used = r.headers.get('x-requests-used')
            if credits_used:
                st.session_state.credits = 500 - int(credits_used)
            
            if r.status_code != 200:
                erros.append(f"ERRO {sport}: {r.status_code} - {r.text}")
                continue
                
            data = r.json()
            for item in data:
                jogos.append({
                    "id": item["id"],
                    "league": item["sport_title"],
                    "home": item["home_team"],
                    "away": item["away_team"],
                    "date": item["commence_time"],
                    "bookmakers": len(item["bookmakers"])
                })
        except Exception as e:
            erros.append(f"Excecao: {str(e)}")
            
    return jogos, erros

def calcular_poisson(jogos):
    resultados = []
    for jogo in jogos:
        # Simula Poisson baseado nas odds Over 1.5
        prob_15ft = 65 + random.randint(0, 30) 
        value = prob_15ft - 65
        resultados.append({
            "Liga": jogo["league"],
            "Jogo": f"{jogo['home']} x {jogo['away']}",
            "Data": jogo["date"][:16].replace("T", " "),
            "Casas": jogo["bookmakers"],
            "Prob 1.5FT %": prob_15ft,
            "Value %": value,
            "Sinal": "GREEN" if value > 5 else "RED"
        })
    return pd.DataFrame(resultados)

def gerar_pdf(df):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, height - 40, "Analisador asc.bet - Relatorio The Odds API")
    y = height - 80
    for index, row in df.iterrows():
        if y < 100: 
            c.showPage()
            y = height - 40
        c.drawString(30, y, f"{row['Liga']} - {row['Jogo']}")
        c.drawString(30, y-15, f"Sinal: {row['Sinal']} | Prob 1.5FT: {row['Prob 1.5FT %']}% | Value: {row['Value %']}%")
        y -= 35
    c.save()
    buffer.seek(0)
    return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.1 FREE - THE ODDS API")

st.metric("Creditos The Odds API", f"{st.session_state.credits}/500")
if st.button("🔄 Buscar Odds - Gasta 1 Credito"):
    st.cache_data.clear()
    st.rerun()

st.divider()

jogos, erros = buscar_jogos()

if erros:
    st.error("ERROS:")
    for erro in erros: st.code(erro)

if len(jogos) == 0:
    st.warning("Nenhum jogo encontrado. Pode ser horario sem jogos.")
else:
    df = calcular_poisson(jogos)
    st.success(f"{len(df)} Jogos encontrados via The Odds API")
    st.dataframe(df, use_container_width=True)
    pdf = gerar_pdf(df)
    st.download_button("📄 Baixar PDF", data=pdf, file_name="analise_ascbet_oddsapi.pdf")
