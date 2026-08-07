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

st.set_page_config(page_title="Analisador asc.bet THEODDS PRO", layout="wide")

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

def poisson(k, lamb): return (math.exp(-lamb) * lamb**k) / math.factorial(k)
def calcular_prob_15_por_liga(media_gols):
    lamb_total = media_gols
    return round((1 - poisson(0, lamb_total) - poisson(1, lamb_total)) * 100, 1)

@st.cache_data(ttl=1800, show_spinner="Buscando Odds REAIS da TheOdds...")
def buscar_jogos_odds(ligas_selecionadas):
    jogos = []
    log_erros = []
    total_req = 0

    for liga_id in ligas_selecionadas:
        nome_liga = LIGAS_ODDS[liga_id]
        url = f"https://api.the-odds-api.com/v4/sports/{liga_id}/odds"
        params = {"apiKey": ODDS_API_KEY, "regions": "us,uk,eu", "markets": "totals", "oddsFormat": "decimal", "dateFormat": "iso"}
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
            for book in item.get('bookmakers', []):
                for market in book.get('markets', []):
                    if market['key'] == 'totals':
                        for outcome in market['outcomes']:
                            if float(outcome['point']) == 1.5 and outcome['name'] == 'Over':
                                odd = outcome['price']
                                prob_imp = round((1 / odd) * 100, 1)
                                value = prob_base - prob_imp
                                dt = datetime.fromisoformat(item['commence_time'].replace('Z',''))
                                jogos.append({
                                    "Liga": nome_liga, "Jogo": f"{item['home_team']} x {item['away_team']}",
                                    "Data": dt.strftime("%d/%m"), "Hora": dt.strftime("%H:%M"), "Casa": book['title'],
                                    "Odd 1.5": odd, "Prob Modelo": prob_base, "Prob Casa": prob_imp,
                                    "Value %": round(value, 1), "Sinal": "GREEN" if value > 0 else "RED"
                                })

    log_erros.append(f"TOTAL REQUISICOES USADAS: {total_req}/500")
    return pd.DataFrame(jogos), log_erros

def gerar_pdf(df):
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=A4); width, height = A4; y = height - 50
    c.setFont("Helvetica-Bold", 20); c.setFillColor(colors.HexColor("#0D47A1"))
    c.drawCentredString(width / 2, y, f"RELATORIO ASC.BET V26.16.22")
    y -= 20; c.setFont("Helvetica", 9); c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Fonte: TheOdds API")
    y -= 30
    if len(df) == 0:
        c.setFont("Helvetica", 12); c.drawString(50, y, "Nenhum sinal GREEN encontrado.")
    else:
        for liga in df['Liga'].unique():
            df_liga = df[df['Liga'] == liga].sort_values('Value %', ascending=False)
            c.setFont("Helvetica-Bold", 14); c.setFillColor(colors.HexColor("#1A237E"))
            c.drawString(30, y, f"{liga.upper()}"); y -= 5; c.line(30, y, width-30, y); y -= 20
            for data_jogo in df_liga['Data'].unique():
                df_data = df_liga[df_liga['Data'] == data_jogo]
                c.setFont("Helvetica-BoldOblique", 10); c.setFillColor(colors.HexColor("#424242"))
                c.drawString(35, y, f"DATA: {data_jogo}"); y -= 15
                data = [['Hora', 'JOGO', 'CASA', 'ODD', 'P.MOD', 'P.CASA', 'VALUE']]
                for index, row in df_data.iterrows():
                    data.append([row['Hora'], row['Jogo'][:28], row['Casa'][:9], row['Odd 1.5'], f"{row['Prob Modelo']}%", f"{row['Prob Casa']}%", f"{row['Value %']}%"])
                table = Table(data, colWidths=[35,155,60,35,40,40,40])
                table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#37474F")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('ALIGN', (1,1), (1,-1), 'LEFT'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 8)]))
                table.wrapOn(c, width, height); table.drawOn(c, 30, y - len(data)*14); y -= len(data)*14 + 15
                if y < 150: c.showPage(); y = height - 50
            y -= 10
    c.save(); buffer.seek(0); return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.22 - THEODDS PRO")
st.success("DADOS 100% REAIS: Jogos, Datas, Odds e Casas. Limite 500 req/mes.")

col1, col2, col3 = st.columns([2,1,1])
with col1:
    ligas_sel = st.multiselect("1. Escolher Ligas", options=list(LIGAS_ODDS.values()), default=["BRASILEIRÃO SÉRIE A", "BRASILEIRÃO SÉRIE B", "MLS - ESTADOS UNIDOS"])
with col2:
    min_value = st.slider("2. Filtro Value Minimo %", -20, 20, -10) # BAIXEI PRA -10 PRA APARECER JOGO
with col3:
    st.write(""); st.write("")
    if st.button("🔄 BUSCAR DADOS REAIS", type="primary", use_container_width=True):
        st.cache_data.clear(); st.rerun()

ligas_ids_sel = [k for k,v in LIGAS_ODDS.items() if v in ligas_sel]
jogos_df, erros = buscar_jogos_odds(ligas_ids_sel)

with st.expander("📋 Log de Status da API", expanded=False):
    for e in erros:
        if "ERRO" in e: st.error(e)
        else: st.info(e)

if len(jogos_df) > 0:
    df = jogos_df[jogos_df['Value %'] >= min_value].sort_values('Value %', ascending=False)
    qtd_green = len(df[df['Sinal']=='GREEN'])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Jogos", len(df))
    col2.metric("Sinais GREEN", qtd_green)
    col3.metric("Creditos Usados", f"{erros[-1].split(':')[1].strip()}")

    # CORREÇÃO AQUI: usei.style.map em vez de applymap
    def highlight_value(val):
        return f'color: {"#00C853" if val > 0 else "#D50000"}; font-weight: bold'
    
    st.dataframe(df.style.map(highlight_value, subset=['Value %']), use_container_width=True, height=500)

    if qtd_green > 0:
        pdf = gerar_pdf(df[df['Sinal']=='GREEN'])
        st.download_button("📄 BAIXAR PDF SINAIS GREEN", data=pdf, file_name=f"GREEN_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf", type="primary", use_container_width=True)
else:
    st.warning("Clique em 'BUSCAR DADOS REAIS' para começar.")
