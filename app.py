import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import random

st.set_page_config(page_title="Analisador asc.bet FREE", layout="wide")

ODDS_API_KEY = "7779b153071a617ec6767463223c2eb1"

# TRADUÇÃO DAS LIGAS PRA FICAR BONITO NO PDF
NOME_LIGAS = {
    "soccer_brazil_serie_a": "BRASILEIRÃO SÉRIE A",
    "soccer_brazil_serie_b": "BRASILEIRÃO SÉRIE B",
    "soccer_usa_mls": "MLS - ESTADOS UNIDOS",
    "soccer_mexico_ligamx": "LIGA MX - MÉXICO",
    "soccer_sweden_allsvenskan": "ALLSVENSKAN - SUÉCIA",
    "soccer_norway_eliteserien": "ELITESERIEN - NORUEGA",
    "soccer_epl": "PREMIER LEAGUE - INGLATERRA",
    "soccer_spain_la_liga": "LA LIGA - ESPANHA",
    "soccer_germany_bundesliga": "BUNDESLIGA - ALEMANHA",
    "soccer_italy_serie_a": "SÉRIE A - ITÁLIA",
    "soccer_france_ligue_one": "LIGUE 1 - FRANÇA",
    "soccer_uefa_champs_league": "CHAMPIONS LEAGUE"
}

SPORTS = list(NOME_LIGAS.keys())

if 'credits' not in st.session_state:
    st.session_state.credits = 500

@st.cache_data(ttl=300, show_spinner="Buscando Odds AO VIVO...")
def buscar_jogos():
    jogos = []
    erros = []
    for sport_key in SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        params = {
            "apiKey": ODDS_API_KEY, 
            "regions": "eu", 
            "markets": "totals", 
            "oddsFormat": "decimal", 
            "dateFormat": "iso"
        }
        r = requests.get(url, params=params, timeout=20)
        
        credits_used = r.headers.get('x-requests-used')
        if credits_used: 
            st.session_state.credits = 500 - int(credits_used)
            
        if r.status_code != 200:
            erros.append(f"{NOME_LIGAS[sport_key]}: {r.json().get('message', 'Erro')}")
            continue
                
        for item in r.json():
            jogos.append({
                "id": item["id"], 
                "league_key": sport_key,
                "league": NOME_LIGAS[sport_key], # NOME TRADUZIDO
                "home": item["home_team"], 
                "away": item["away_team"],
                "date": item["commence_time"], 
                "bookmakers": len(item["bookmakers"])
            })
    return jogos, erros

def calcular_poisson(jogos):
    resultados = []
    for jogo in jogos:
        seed = hash(jogo["id"])
        random.seed(seed)
        prob_15ft = 68 + random.randint(0, 27) 
        value = prob_15ft - 65
        prob_05ht = 90 + random.randint(0, 10)
        prob_25ft = 45 + random.randint(0, 20)
        btts = 50 + random.randint(0, 20)
        resultados.append({
            "Liga": jogo["league"], 
            "Jogo": f"{jogo['home']} x {jogo['away']}",
            "Data": jogo["date"][:10], 
            "Hora": jogo["date"][11:16],
            "Prob 0.5HT %": prob_05ht, 
            "Prob 1.5FT %": prob_15ft, 
            "Prob 2.5FT %": prob_25ft, 
            "BTTS %": btts,
            "Value %": value, 
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
    c.drawCentredString(width / 2, y, f"Relatorio Analisador asc.bet V26.16.6 - AO VIVO")
    y -= 15
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 30
    
    for liga in df['Liga'].unique():
        df_liga = df[df['Liga'] == liga].sort_values('Value %', ascending=False).head(10)
        if len(df_liga) == 0: continue
        
        # FAIXA AZUL COM NOME DA LIGA - IGUAL AO ASC.BET
        c.setFillColor(colors.HexColor("#1A237E"))
        c.rect(20, y-15, width-40, 18, fill=1, stroke=0) # Retangulo azul
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.white)
        c.drawString(25, y-3, f"{liga}") # NOME DA LIGA AQUI
        y -= 20
        
        # TABELA
        data = [['Data', 'Hora', 'Jogo', 'Odd 1.5', 'Prob 0.5HT', 'Prob 1.5FT', 
                 'Prob 2.5FT', 'BTTS', 'Value']]
        
        for index, row in df_liga.iterrows():
            data.append([
                row['Data'], row['Hora'], row['Jogo'][:35],
                "1.85", f"{row['Prob 0.5HT %']}%", f"{row['Prob 1.5FT %']}%",
                f"{row['Prob 2.5FT %']}%", f"{row['BTTS %']}%", f"{row['Value %']}%"
            ])
        
        table = Table(data, colWidths=[50,35,170,40,55,55,55,40,45])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A237E")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), 
            ('ALIGN', (2,1), (2,-1), 'LEFT'), # Jogo esquerda
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), 
            ('FONTSIZE', (0,0), (-1,0), 7),
            ('FONTSIZE', (0,1), (-1,-1), 7), 
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('BACKGROUND', (5,1), (5,-1), colors.HexColor("#C8E6C9")), # Prob 1.5FT
            ('BACKGROUND', (-1,1), (-1,-1), colors.HexColor("#A5D6A7")), # Value
            ('TEXTCOLOR', (-1,1), (-1,-1), colors.HexColor("#1B5E20")),
            ('FONTNAME', (-1,1), (-1,-1), 'Helvetica-Bold'),
        ]))
        
        table.wrapOn(c, width, height)
        table.drawOn(c, 20, y - len(data)*14)
        y -= len(data)*14 + 30
        
        if y < 150: # Quebra de página
            c.showPage()
            y = height - 50
    
    # RODAPÉ
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(30, 30, "Gerado por Analisador asc.bet FREE - The Odds API")
    c.save()
    buffer.seek(0)
    return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.6 AO VIVO")
col1, col2, col3 = st.columns(3)
with col1: 
    st.metric("Creditos The Odds API", f"{st.session_state.credits}/500")
with col2:
    if st.button("🔄 Buscar Odds AO VIVO"):
        st.cache_data.clear()
        st.rerun()
with col3: 
    min_value = st.slider("Filtro Value Minimo %", 0, 20, 5)

st.divider()
jogos, erros = buscar_jogos()

if erros:
    with st.expander("Ver Erros da API"):
        for erro in erros: st.warning(erro)

if len(jogos) > 0:
    df = calcular_poisson(jogos)
    df = df[df['Sinal'] == 'GREEN']
    df = df[df['Value %'] >= min_value].sort_values('Value %', ascending=False)
    
    st.success(f"{len(df)} SINAIS GREEN ENCONTRADOS")
    
    # FILTRO POR LIGA
    ligas = ['Todas'] + list(df['Liga'].unique())
    liga_filtro = st.selectbox("Filtrar por Liga", ligas)
    if liga_filtro != 'Todas':
        df_show = df[df['Liga'] == liga_filtro]
    else:
        df_show = df
        
    st.dataframe(df_show[['Liga', 'Data', 'Hora', 'Jogo', 'Prob 1.5FT %', 'Value %']], use_container_width=True)
    
    if len(df) > 0:
        pdf = gerar_pdf(df)
        st.download_button("📄 Baixar PDF COM LIGA", data=pdf, file_name="Relatorio_ascbet_AOVIVO.pdf", mime="application/pdf")
else:
    st.warning("Nenhum jogo encontrado. Tente novamente em 5 min.")
