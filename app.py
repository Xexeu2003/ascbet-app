import streamlit as st
import requests
import pandas as pd
import sqlite3
import math
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

st.set_page_config(page_title="Analisador asc.bet FREE", layout="wide")

# SUAS CHAVES
ODDS_API_KEY = "7779b153071a617ec6767463223c2eb1" # 500/mes TheOdds
FOOTBALL_API_KEY = "a1e4fd8b13622e830db1f983877308e7" # 100/dia API-Football

# 6 LIGAS AO VIVO AGORA
LIGAS_IDS = {
    71: "BRASILEIRÃO SÉRIE A",
    72: "BRASILEIRÃO SÉRIE B", 
    253: "MLS - ESTADOS UNIDOS",
    113: "ALLSVENSKAN - SUÉCIA",
    103: "ELITESERIEN - NORUEGA",
    218: "PEPSI DEILD - ISLÂNDIA"
}

# CACHE PRA NÃO ESTOURAR OS 100 CRED
conn = sqlite3.connect('cache_stats.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS stats 
                (team_id INT PRIMARY KEY, gf REAL, ga REAL, data TEXT)''')

def buscar_stats_cache(time_id):
    # TENTA CACHE DE 24H
    res = conn.execute("SELECT gf,ga FROM stats WHERE team_id=? AND data > ?", 
                       (time_id, (datetime.now()-timedelta(hours=24)).isoformat())).fetchone()
    if res: return res
    
    # BUSCA NA API E GASTA 1 CREDITO
    url = f"https://v3.football.api-sports.io/teams/statistics"
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    params = {"team": time_id, "season": "2026"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code != 200: return None
        data = r.json()["response"]
        jogos = data["fixtures"]["played"]["total"]
        if jogos == 0: return 1.2, 1.2
        gf = data["goals"]["for"]["total"]["total"] / jogos
        ga = data["goals"]["against"]["total"]["total"] / jogos
        conn.execute("REPLACE INTO stats VALUES (?,?,?,?)", (time_id,gf,ga,datetime.now().isoformat()))
        conn.commit()
        return gf, ga
    except:
        return None

def poisson(k, lamb):
    return (math.exp(-lamb) * lamb**k) / math.factorial(k)

def calcular_prob_15(gf_casa, ga_fora, gf_fora, ga_casa):
    lamb_casa = (gf_casa + ga_fora) / 2
    lamb_fora = (gf_fora + ga_casa) / 2
    lamb_total = lamb_casa + lamb_fora
    p0 = poisson(0, lamb_total)
    p1 = poisson(1, lamb_total)
    prob_15 = (1 - p0 - p1) * 100
    return round(prob_15, 1)

@st.cache_data(ttl=3600, show_spinner="Buscando Dados REAIS... Gastando poucos créditos")
def buscar_jogos_reais():
    jogos = []
    log_erros = []
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    data_7dias = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    limite_batido = False

    for liga_id, nome_liga in LIGAS_IDS.items():
        if limite_batido: break

        # BUSCAR DE HOJE ATE 7 DIAS PRA TER JOGO
        url = f"https://v3.football.api-sports.io/fixtures"
        headers = {"x-apisports-key": FOOTBALL_API_KEY}
        params = {"league": liga_id, "season": "2026", "from": data_hoje, "to": data_7dias}
        r = requests.get(url, headers=headers, params=params)

        if r.status_code == 429:
            log_erros.append(f"{nome_liga}: Limite 100 req/dia atingido. Reset 21h Manaus")
            limite_batido = True
            break
        if r.status_code != 200:
            log_erros.append(f"{nome_liga}: Erro {r.status_code} - {r.text[:50]}")
            continue

        lista_jogos = r.json().get("response", [])
        if len(lista_jogos) == 0:
            log_erros.append(f"{nome_liga}: Sem jogos nos próximos 7 dias")
            continue

        for item in lista_jogos[:10]: # max 10 por liga pra economizar
            if limite_batido: break
            home_id = item["teams"]["home"]["id"]
            away_id = item["teams"]["away"]["id"]
            
            stats_home = buscar_stats_cache(home_id)
            stats_away = buscar_stats_cache(away_id)
            if not stats_home or not stats_away: continue

            gf_casa, ga_casa = stats_home
            gf_fora, ga_fora = stats_away
            
            prob_15 = calcular_prob_15(gf_casa, ga_fora, gf_fora, ga_casa)
            value = prob_15 - 70 # Value baseado em odd 1.85
            
            jogos.append({
                "Liga": nome_liga,
                "Jogo": f"{item['teams']['home']['name']} x {item['teams']['away']['name']}",
                "Data": item["fixture"]["date"][:10],
                "Hora": item["fixture"]["date"][11:16],
                "Prob 1.5FT %": prob_15,
                "Value %": round(value, 1),
                "Sinal": "GREEN" if value > 5 else "RED"
            })
    return pd.DataFrame(jogos), log_erros

def gerar_pdf(df):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor("#0D47A1"))
    c.drawCentredString(width / 2, y, f"Relatorio Analisador asc.bet V26.16.13 - DADOS REAIS")
    y -= 15
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 30
    
    for liga in df['Liga'].unique():
        df_liga = df[df['Liga'] == liga].sort_values('Value %', ascending=False).head(10)
        if len(df_liga) == 0: continue
        data = [['Data', 'Hora', f'JOGO - {liga}', 'Prob 1.5FT', 'Value']]
        for index, row in df_liga.iterrows():
            data.append([row['Data'], row['Hora'], row['Jogo'][:38], f"{row['Prob 1.5FT %']}%", f"{row['Value %']}%"])
        
        table = Table(data, colWidths=[50,35,200,60,50])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A237E")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('ALIGN', (2,0), (2,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('SPAN', (2,0), (-1,0)),
            ('BACKGROUND', (3,1), (3,-1), colors.HexColor("#C8E6C9")),
            ('BACKGROUND', (4,1), (4,-1), colors.HexColor("#A5D6A7")),
            ('TEXTCOLOR', (4,1), (4,-1), colors.HexColor("#1B5E20")),
            ('FONTNAME', (4,1), (4,-1), 'Helvetica-Bold'),
        ]))
        table.wrapOn(c, width, height)
        table.drawOn(c, 20, y - len(data)*14)
        y -= len(data)*14 + 20
        if y < 150: c.showPage(); y = height - 50
    
    c.save(); buffer.seek(0); return buffer

# --- INTERFACE ---
st.title("Analisador asc.bet V26.16.13 - PLANO FREE 100% REAL")
st.info("Ligas: BR A/B, MLS, Suécia, Noruega, Islândia. Busca jogos de hoje até +7 dias.")
st.warning("Modo FREE: Max 100 req/dia na API-Football. O app usa cache de 24h pra economizar.")

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Buscar Dados REAIS"):
        st.cache_data.clear()
        st.rerun()
with col2: min_value = st.slider("Filtro Value Minimo %", 0, 20, 5)

jogos_df, erros = buscar_jogos_reais()

# MOSTRA LOG DE ERROS
if erros:
    with st.expander("📋 Log de Status da API"):
        for e in erros: 
            if "Limite" in e: st.error(e)
            elif "Sem jogos" in e: st.info(e)
            else: st.warning(e)

if len(jogos_df) > 0:
    df = jogos_df[jogos_df['Sinal'] == 'GREEN']
    df = df[df['Value %'] >= min_value].sort_values('Value %', ascending=False)
    
    st.success(f"{len(df)} SINAIS GREEN ENCONTRADOS")
    st.dataframe(df, use_container_width=True)
    
    if len(df) > 0:
        pdf = gerar_pdf(df)
        st.download_button("📄 Baixar PDF DADOS REAIS", data=pdf, file_name=f"Relatorio_REAL_{datetime.now().strftime('%d%m%Y')}.pdf")
else:
    st.error("Nenhum sinal GREEN encontrado. Verifique o Log acima.")
