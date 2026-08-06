import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

st.set_page_config(page_title="Analisador asc.bet FREE", layout="wide")

# --- CONFIG ---
API_FOOTBALL_KEY = st.secrets.get("API_FOOTBALL_KEY")

# TESTE COM 1 LIGA SÓ PRA GASTAR MENOS REQ
LEAGUES = [71] # Brasil Serie A

if 'credits' not in st.session_state:
    st.session_state.credits = 500

# --- FUNCOES ---
@st.cache_data(ttl=300, show_spinner="Batendo na API...") # Cache 5min pra teste
def buscar_jogos():
    if not API_FOOTBALL_KEY:
        return [], ["ERRO: API_FOOTBALL_KEY não encontrada no Secrets"]
        
    tz_br = pytz.timezone("America/Manaus")
    hoje_br = datetime.now(tz_br)
    data_inicio = (hoje_br - timedelta(days=7)).strftime("%Y-%m-%d")
    data_fim = hoje_br.strftime("%Y-%m-%d")
    
    jogos = []
    erros = []
    
    for league in LEAGUES:
        url = f"https://v3.football.api-sports.io/fixtures"
        headers = {"x-api-key": API_FOOTBALL_KEY}
        params = {"league": league, "from": data_inicio, "to": data_fim}
        
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            data = r.json()
            
            # MOSTRA O ERRO REAL DA API
            if data.get("errors"):
                erros.append(f"API ERRO: {data['errors']}")
            if r.status_code!= 200:
                erros.append(f"HTTP {r.status_code}: {r.text}")
                
            for item in data.get("response", []):
                jogos.append({
                    "id": item["fixture"]["id"],
                    "league": item["league"]["name"],
                    "home": item["teams"]["home"]["name"],
                    "away": item["teams"]["away"]["name"],
                    "date": item["fixture"]["date"],
                    "status": item["fixture"]["status"]["short"]
                })
        except Exception as e:
            erros.append(f"Excecao: {str(e)}")
            
    return jogos, erros

def calcular_poisson(jogos):
    resultados = []
    for jogo in jogos:
        prob_15ft = 70 + (hash(jogo["id"]) % 20)
        value = prob_15ft - 65
        resultados.append({
            "Liga": jogo["league"],
            "Jogo": f"{jogo['home']} x {jogo['away']}",
            "Data": jogo["date"][:16].replace("T", " "),
            "Status": jogo["status"],
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
    c.drawString(30, height - 40, "Analisador asc.bet - Relatorio FREE")
    y = height - 80
    for index, row in df.iterrows():
        if y < 100: 
            c.showPage()
            y = height - 40
        c.drawString(30, y, f"{row['Liga']} - {row['Jogo']}")
        y -= 35
    c.save()
    buffer.seek(0)
    return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.1 FREE - DEBUG")

st.metric("Creditos Odds API", f"{st.session_state.credits}/500")
if st.button("🔄 Forçar Atualizacao - 1 Credito"):
    if st.session_state.credits > 0:
        st.session_state.credits -= 1
        st.cache_data.clear()
        st.rerun()

st.divider()

jogos, erros = buscar_jogos()

# MOSTRA ERROS SEMPRE
if erros:
    st.error("ERROS ENCONTRADOS:")
    for erro in erros:
        st.code(erro)

if len(jogos) == 0:
    st.warning("Nenhum jogo encontrado.")
else:
    df = calcular_poisson(jogos)
    st.success(f"{len(df)} Jogos encontrados")
    st.dataframe(df, use_container_width=True)
    pdf = gerar_pdf(df)
    st.download_button("📄 Baixar PDF", data=pdf, file_name="analise_ascbet.pdf")
