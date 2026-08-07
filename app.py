import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

st.set_page_config(page_title="Analisador asc.bet THEODDS PRO", layout="wide")
ODDS_API_KEY = "7779b153071a617ec6767463223c2eb1"

# LIGAS MENORES QUE FICAM LIBERADAS NO FREE
LIGAS_ODDS = {
    "soccer_iceland_urvalsdeild": "ÚRVALLSDEILD - ISLÂNDIA",
    "soccer_finland_veikkausliiga": "VEIKKAUSLIIGA - FINLÂNDIA", 
    "soccer_ireland_premier": "PREMIER DIVISION - IRLANDA",
    "soccer_malta_premier_league": "PREMIER LEAGUE - MALTA",
    "soccer_denmark_superliga": "SUPERLIGA - DINAMARCA"
}

# MÉDIA DE GOLS 2025 DAS LIGAS MENORES
MEDIA_GOLS_LIGA = {
    "soccer_iceland_urvalsdeild": 3.40, "soccer_finland_veikkausliiga": 2.95,
    "soccer_ireland_premier": 2.75, "soccer_malta_premier_league": 3.15,
    "soccer_denmark_superliga": 2.90
}
BTTS_MEDIA_LIGA = {
    "soccer_iceland_urvalsdeild": 62, "soccer_finland_veikkausliiga": 58,
    "soccer_ireland_premier": 54, "soccer_malta_premier_league": 60,
    "soccer_denmark_superliga": 56
}

def poisson(k, lamb): return (math.exp(-lamb) * lamb**k) / math.factorial(k)
def calcular_prob_15(media_gols): return round((1 - poisson(0, media_gols) - poisson(1, media_gols)) * 100, 1)
def calcular_prob_25(media_gols): return round((1 - poisson(0, media_gols) - poisson(1, media_gols) - poisson(2, media_gols)) * 100, 1)

@st.cache_data(ttl=1800)
def buscar_jogos_odds(ligas_selecionadas):
    jogos = []
    log_erros = []
    total_req = 0

    for liga_id in ligas_selecionadas:
        nome_liga = LIGAS_ODDS[liga_id]
        url = f"https://api.the-odds-api.com/v4/sports/{liga_id}/odds"
        params = {"apiKey": ODDS_API_KEY, "regions": "us,uk,eu", "markets": "totals,btts", "oddsFormat": "decimal", "dateFormat": "iso"}
        r = requests.get(url, params=params)
        total_req += 1
        
        if r.status_code == 422:
            log_erros.append(f"{nome_liga}: ERRO 422 - Liga bloqueada")
            continue
        if r.status_code == 429:
            log_erros.append(f"{nome_liga}: ERRO 429 - Limite da API")
            break
        if r.status_code!= 200:
            log_erros.append(f"{nome_liga}: ERRO {r.status_code}")
            continue
        
        lista_jogos = r.json()
        log_erros.append(f"{nome_liga}: {len(lista_jogos)} jogos encontrados")
        
        prob_15 = calcular_prob_15(MEDIA_GOLS_LIGA[liga_id])
        prob_25 = calcular_prob_25(MEDIA_GOLS_LIGA[liga_id])
        prob_btts = BTTS_MEDIA_LIGA[liga_id]

        for item in lista_jogos:
            for book in item.get('bookmakers', []):
                for market in book.get('markets', []):
                    dt = datetime.fromisoformat(item['commence_time'].replace('Z',''))
                    jogo_nome = f"{item['home_team']} x {item['away_team']}"
                    
                    if market['key'] == 'totals':
                        for outcome in market['outcomes']:
                            if float(outcome['point']) == 1.5 and outcome['name'] == 'Over':
                                odd = outcome['price']
                                prob_imp = round((1 / odd) * 100, 1)
                                value = prob_15 - prob_imp
                                jogos.append({"Mercado":"Over 1.5FT", "Liga":nome_liga, "Jogo":jogo_nome, "Data":dt.strftime("%d/%m"), "Hora":dt.strftime("%H:%M"), "Casa":book['title'], "Odd":odd, "Prob Modelo":prob_15, "Prob Casa":prob_imp, "Value %":round(value, 1), "Sinal":"GREEN" if value > 0 else "RED"})
                            if float(outcome['point']) == 2.5 and outcome['name'] == 'Over':
                                odd = outcome['price']
                                prob_imp = round((1 / odd) * 100, 1)
                                value = prob_25 - prob_imp
                                jogos.append({"Mercado":"Over 2.5FT", "Liga":nome_liga, "Jogo":jogo_nome, "Data":dt.strftime("%d/%m"), "Hora":dt.strftime("%H:%M"), "Casa":book['title'], "Odd":odd, "Prob Modelo":prob_25, "Prob Casa":prob_imp, "Value %":round(value, 1), "Sinal":"GREEN" if value > 0 else "RED"})
                    
                    if market['key'] == 'btts':
                        for outcome in market['outcomes']:
                            if outcome['name'] == 'Yes':
                                odd = outcome['price']
                                prob_imp = round((1 / odd) * 100, 1)
                                value = prob_btts - prob_imp
                                jogos.append({"Mercado":"BTTS Sim", "Liga":nome_liga, "Jogo":jogo_nome, "Data":dt.strftime("%d/%m"), "Hora":dt.strftime("%H:%M"), "Casa":book['title'], "Odd":odd, "Prob Modelo":prob_btts, "Prob Casa":prob_imp, "Value %":round(value, 1), "Sinal":"GREEN" if value > 0 else "RED"})
    
    log_erros.append(f"TOTAL REQ: {total_req}/500")
    return pd.DataFrame(jogos), log_erros

def gerar_pdf(df):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#0D47A1"))
    c.drawCentredString(width / 2, y, f"RELATORIO ASC.BET V26.16.26")
    y -= 20
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Fonte: TheOdds API")
    y -= 30
    
    if len(df) == 0:
        c.drawString(50, y, "Nenhum sinal GREEN encontrado no filtro atual.")
    else:
        for liga in df['Liga'].unique():
            df_liga = df[df['Liga'] == liga]
            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(colors.HexColor("#1A237E"))
            c.drawString(30, y, f"{liga.upper()}")
            y -= 5
            c.line(30, y, width-30, y)
            y -= 20
            
            for mercado in df_liga['Mercado'].unique():
                df_merc = df_liga[df_liga['Mercado'] == mercado].sort_values('Value %', ascending=False)
                c.setFont("Helvetica-BoldOblique", 11)
                c.setFillColor(colors.HexColor("#D32F2F"))
                c.drawString(35, y, f">>> {mercado} <<<")
                y -= 18
                
                for data_jogo in df_merc['Data'].unique():
                    df_data = df_merc[df_merc['Data'] == data_jogo]
                    c.setFont("Helvetica-Bold", 9)
                    c.setFillColor(colors.HexColor("#424242"))
                    c.drawString(40, y, f"Data: {data_jogo}")
                    y -= 15
                    
                    data = [['Hora', 'JOGO', 'CASA', 'ODD', 'P.MOD', 'P.CASA', 'VALUE']]
                    for index, row in df_data.iterrows():
                        data.append([row['Hora'], row['Jogo'][:25], row['Casa'][:8], row['Odd'], f"{row['Prob Modelo']}%", f"{row['Prob Casa']}%", f"{row['Value %']}%"])
                    
                    table = Table(data, colWidths=[30,130,55,30,35,35,35])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#37474F")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('ALIGN', (1,1), (1,-1), 'LEFT'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), 7)
                    ]))
                    table.wrapOn(c, width, height)
                    table.drawOn(c, 30, y - len(data)*13)
                    y -= len(data)*13 + 10
                    if y < 150:
                        c.showPage()
                        y = height - 50
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.26 - THEODDS FREE TEST")
st.success("MERCADOS: Over 1.5, Over 2.5 e BTTS Sim | LIGAS MENORES FREE")
st.warning("Testando ligas que ficam liberadas no plano FREE: Islândia, Finlândia, Irlanda, Malta, Dinamarca")

col1, col2, col3 = st.columns([2,1,1])
with col1:
    ligas_sel = st.multiselect("1. Escolher Ligas", options=list(LIGAS_ODDS.values()), default=["ÚRVALLSDEILD - ISLÂNDIA", "VEIKKAUSLIIGA - FINLÂNDIA"])
with col2:
    min_value = st.slider("2. Filtro Value Minimo %", -20, 20, -20)
with col3:
    st.write("")
    st.write("")
    buscar = st.button("🔄 BUSCAR DADOS REAIS", type="primary", use_container_width=True)

if buscar:
    st.cache_data.clear()
    st.rerun()
    
ligas_ids_sel = [k for k,v in LIGAS_ODDS.items() if v in ligas_sel]
jogos_df, erros = buscar_jogos_odds(ligas_ids_sel)

with st.expander("📋 Log de Status da API", expanded=True):
    for e in erros:
        if "ERRO" in e:
            st.error(e)
        else:
            st.info(e)

if len(jogos_df) > 0:
    df_filtrado = jogos_df[jogos_df['Value %'] >= min_value].sort_values('Value %', ascending=False)
    qtd_green = len(df_filtrado[df_filtrado['Sinal']=='GREEN'])
else:
    df_filtrado = pd.DataFrame()
    qtd_green = 0

col1, col2, col3 = st.columns(3)
col1.metric("Total de Jogos", len(df_filtrado))
col2.metric("Sinais GREEN", qtd_green, delta=f"+{qtd_green}" if qtd_green > 0 else "0")
col3.metric("Creditos Usados", f"{erros[-1].split(':')[1].strip()}" if erros else "0/500")

if len(df_filtrado) > 0:
    def highlight_value(val):
        return f'color: {"#00C853" if val > 0 else "#D50000"}; font-weight: bold'
    st.dataframe(df_filtrado.style.map(highlight_value, subset=['Value %']), use_container_width=True, height=500)

    if qtd_green > 0:
        pdf = gerar_pdf(df_filtrado[df_filtrado['Sinal']=='GREEN'])
        st.download_button("📄 BAIXAR PDF GREEN PROFISSIONAL", data=pdf, file_name=f"GREEN_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf", type="primary", use_container_width=True)
else:
    st.warning(f"Nenhum jogo encontrado com Value >= {min_value}%. Tente abaixar mais o filtro.")
