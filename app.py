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

FOOTBALL_API_KEY = "a1e4fd8b13622e830db1f983877308e7"

# LIGAS QUE FUNCIONAM NO PLANO FREE - troquei BR e MLS por ligas menores
LIGAS_IDS = {
    218: "PEPSI DEILD - ISLÂNDIA D1",
    113: "ALLSVENSKAN - SUÉCIA D1",
    103: "ELITESERIEN - NORUEGA D1",
    682: "SUPERETTAN - SUÉCIA D2", # NOVA
    317: "OBOS-LIGAEN - NORUEGA D2", # NOVA
    237: "URVALSDEILD - ISLÂNDIA D2" # NOVA
}

conn = sqlite3.connect('cache_stats.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS stats (team_id INT PRIMARY KEY, gf REAL, ga REAL, data TEXT)''')

def buscar_stats_cache(time_id):
    res = conn.execute("SELECT gf,ga FROM stats WHERE team_id=? AND data >?", 
                       (time_id, (datetime.now()-timedelta(hours=24)).isoformat())).fetchone()
    if res: return res
    url = f"https://v3.football.api-sports.io/teams/statistics"
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    params = {"team": time_id, "season": "2025"}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    if r.status_code!= 200: return None
    data = r.json()["response"]
    jogos = data["fixtures"]["played"]["total"]
    if jogos == 0: return 1.2, 1.2
    gf = data["goals"]["for"]["total"]["total"] / jogos
    ga = data["goals"]["against"]["total"]["total"] / jogos
    conn.execute("REPLACE INTO stats VALUES (?,?,?,?)", (time_id,gf,ga,datetime.now().isoformat()))
    conn.commit()
    return gf, ga

def poisson(k, lamb): return (math.exp(-lamb) * lamb**k) / math.factorial(k)
def calcular_prob_15(gf_casa, ga_fora, gf_fora, ga_casa):
    lamb_total = ((gf_casa + ga_fora) / 2) + ((gf_fora + ga_casa) / 2)
    return round((1 - poisson(0, lamb_total) - poisson(1, lamb_total)) * 100, 1)

@st.cache_data(ttl=3600, show_spinner="Buscando Dados REAIS...")
def buscar_jogos_reais():
    jogos = []
    log_erros = []
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    data_30dias = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") # AUMENTEI PRA 30 DIAS
    total_req = 0

    for liga_id, nome_liga in LIGAS_IDS.items():
        if total_req >= 90: 
            log_erros.append("TRAVA: Parou em 90 req")
            break

        url = f"https://v3.football.api-sports.io/fixtures"
        headers = {"x-apisports-key": FOOTBALL_API_KEY}
        params = {"league": liga_id, "season": "2025", "from": data_hoje, "to": data_30dias} # 30 DIAS
        r = requests.get(url, headers=headers, params=params)
        total_req += 1

        if r.status_code == 429:
            log_erros.append(f"{nome_liga}: ERRO 429 - Limite atingido")
            break
        if r.status_code!= 200:
            log_erros.append(f"{nome_liga}: ERRO {r.status_code}")
            continue

        lista_jogos = r.json().get("response", [])
        log_erros.append(f"{nome_liga}: Encontrados {len(lista_jogos)} jogos")

        for item in lista_jogos[:10]:
            if total_req >= 90: break
            home_id = item["teams"]["home"]["id"]; away_id = item["teams"]["away"]["id"]
            stats_home = buscar_stats_cache(home_id); stats_away = buscar_stats_cache(away_id)
            total_req += 2
            if not stats_home or not stats_away: continue
            prob_15 = calcular_prob_15(stats_home[0], stats_away[1], stats_away[0], stats_home[1])
            value = prob_15 - 70
            jogos.append({
                "Liga": nome_liga, "Jogo": f"{item['teams']['home']['name']} x {item['teams']['away']['name']}",
                "Data": item["fixture"]["date"][:10], "Hora": item["fixture"]["date"][11:16],
                "Prob 1.5FT %": prob_15, "Value %": round(value, 1), "Sinal": "GREEN" if value > 5 else "RED"
            })
    log_erros.append(f"TOTAL DE REQUISICOES USADAS: {total_req}/100")
    return pd.DataFrame(jogos), log_erros

def gerar_pdf(df):
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=A4); width, height = A4; y = height - 50
    c.setFont("Helvetica-Bold", 18); c.drawCentredString(width / 2, y, f"Relatorio asc.bet V26.16.16 - LIGAS FREE")
    c.save(); buffer.seek(0); return buffer

st.title("Analisador asc.bet V26.16.16 - LIGAS FREE")
st.warning("ATENÇÃO: Plano FREE só libera ligas menores. BR/MLS só no plano pago.")
if st.button("🔄 Buscar Dados REAIS"):
    st.cache_data.clear(); st.rerun()

jogos_df, erros = buscar_jogos_reais()

with st.expander("📋 Log de Status da API", expanded=True):
    for e in erros: st.code(e)

if len(jogos_df) > 0:
    df = jogos_df[jogos_df['Sinal'] == 'GREEN'].sort_values('Value %', ascending=False)
    st.success(f"{len(df)} SINAIS GREEN ENCONTRADOS")
    st.dataframe(df, use_container_width=True)
    st.download_button("📄 Baixar PDF", data=gerar_pdf(df), file_name="Relatorio_FREE.pdf")
else:
    st.error("Nenhum sinal GREEN. Veja o Log acima.")
