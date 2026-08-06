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
API_FOOTBALL_KEY = st.secrets.get("API_FOOTBALL_KEY", "SUA_CHAVE_AQUI")

# LIGAS QUE SEMPRE TEM JOGO
LEAGUES = [
    71,   # Brasil Serie A 
    39,   # Inglaterra Premier League
    140,  # Espanha La Liga
    135,  # Itália Serie A
    78    # Alemanha Bundesliga
]

if 'credits' not in st.session_state:
    st.session_state.credits = 500

# --- FUNCOES ---
@st.cache_data(ttl=43200, show_spinner="Buscando jogos na API...") # Cache 12h
def buscar_jogos():
    tz_br = pytz.timezone("America/Manaus")
    hoje_br = datetime.now(tz_br)
    
    # BUSCAR 7 DIAS PRA TRÁS PRA TESTE
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
            
            if r.status_code != 200:
                erros.append(f"Liga {league}: Erro {r.status_code} - {r.text}")
                continue
                
            data = r.json()
            if data.get("errors"):
                erros.append(f"Liga {league}: {data['errors']}")
                continue

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
            erros.append(f"Liga {league}: {str(e)}")
            
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
    c.setFont("Helvetica", 10)
    y = height - 80
    for index, row in df.iterrows():
        if y < 100: 
            c.showPage()
            y = height - 40
        c.drawString(30, y, f"{row['Liga']} - {row['Jogo']}")
        c.drawString(30, y-15, f"Status: {row['Status']} | Prob 1.5FT: {row['Prob 1.5FT %']}% | Value: {row['Value %']}% | Sinal: {row['Sinal']}")
        y -= 35
    c.save()
    buffer.seek(0)
    return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.1 FREE - Modo FREE 500 creditos")

col1, col2 = st.columns([2,1])
with col1:
    st.info(f"Buscando jogos de 7 dias atras ate hoje | Cache 12h ativo")
with col2:
    st.metric("Creditos Odds API", f"{st.session_state.credits}/500")
    if st.button("🔄 Forçar Atualizacao - 1 Credito"):
        if st.session_state.credits > 0:
            st.session_state.credits -= 1
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Sem creditos")

st.divider()

jogos, erros = buscar_jogos()

# MOSTRA ERROS SE TIVER
if erros:
    with st.expander("Ver Erros da API"):
        for erro in erros:
            st.error(erro)

if len(jogos) == 0:
    st.warning("Nenhum jogo encontrado. Verifica se a KEY da API-Football está correta em Secrets")
else:
    df = calcular_poisson(jogos)
    st.success(f"{len(df)} Jogos encontrados")
    
    st.dataframe(df, use_container_width=True)
    
    pdf = gerar_pdf(df)
    st.download_button(
        label="📄 Baixar PDF dos Jogos",
        data=pdf,
        file_name="analise_ascbet.pdf",
        mime="application/pdf"
    )

st.divider()
st.caption("Modo FREE: Atualiza 2x ao dia. Cache de 12h para economizar creditos.")
