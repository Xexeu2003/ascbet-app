import streamlit as st
import pandas as pd
import requests
import numpy as np
from scipy.stats import poisson
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime, timedelta
import pytz
import time
import os
import json

VERSAO = "V26.14.1"
MARCA_DAGUA = "asc.bet"
API_FOOTBALL_URL = "https://apiv3.apifootball.com/"
API_FOOTBALL_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
HISTORICO_FILE = "/mnt/data/historico_ascbet.json"

ODDS_API_KEY = "cc7a0c9ee51e4bc96110d49730acaa"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports"
REFRESH_MINUTOS = 120

LIGAS_MAPA = {
    534: {"nome": "SUECIA ALLSVENSKAN", "odds_key": "soccer_sweden_allsvenskan"},
    103: {"nome": "NORUEGA ELITESERIEN", "odds_key": "soccer_norway_eliteserien"},
    522: {"nome": "FINLANDIA VEIKKAUSLIIGA", "odds_key": "soccer_finland_veikkausliiga"},
    198: {"nome": "ISLANDIA BESTA DEILD", "odds_key": "soccer_iceland_urvalsdeild"},
    337: {"nome": "ESTONIA MEISTRILIIGA", "odds_key": None},
    340: {"nome": "LETONIA VIRSLIGA", "odds_key": None},
    341: {"nome": "LITUANIA A LYGA", "odds_key": None},
    523: {"nome": "ILHAS FAROE BETRI DEILDIN", "odds_key": None},
    175: {"nome": "IRLANDA LEAGUE OF IRELAND", "odds_key": "soccer_ireland_premier_league"},
}

st.set_page_config(page_title=f"Analisador asc.bet {VERSAO}", layout="wide")
st.title(f"Analisador asc.bet {VERSAO} - TOP 10 + Histórico 7 Dias")

# AUTO REFRESH
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if time.time() - st.session_state.last_update > REFRESH_MINUTOS * 60:
    st.session_state.last_update = time.time()
    st.rerun()
tempo_restante = REFRESH_MINUTOS - int((time.time() - st.session_state.last_update) / 60)
st.sidebar.info(f"Proxima atualizacao em: {tempo_restante}min")
if st.sidebar.button("🔄 Forcar Atualizacao Agora"):
    st.session_state.last_update = 0
    st.rerun()

def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, 'r') as f: return json.load(f)
    return []

def salvar_historico(historico):
    with open(HISTORICO_FILE, 'w') as f: json.dump(historico, f)

def atualizar_historico(df_novo):
    historico = carregar_historico()
    hoje = datetime.now().strftime("%Y-%m-%d")
    for _, row in df_novo.iterrows():
        jogo_id = f"{row['Casa']}_{row['Fora']}_{row['Data']}"
        if not any(j['id'] == jogo_id for j in historico):
            historico.append({
                "id": jogo_id, "data_prev": row['Data'], "liga": row['Liga'],
                "casa": row['Casa'], "fora": row['Fora'], "prob_15": row['Prob 1.5FT'],
                "value": row['Value'], "status": "pendente", "resultado": ""
            })
    limite = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    historico = [j for j in historico if j['data_prev'] >= limite]
    salvar_historico(historico)
    return historico

def mostrar_historico():
    historico = carregar_historico()
    if not historico: return
    df_hist = pd.DataFrame(historico)
    df_hist['ValueNum'] = df_hist['value'].str.replace('%','').astype(float)
    total = len(df_hist[df_hist['status']!= 'pendente'])
    greens = len(df_hist[df_hist['status'] == 'green'])
    reds = len(df_hist[df_hist['status'] == 'red'])
    assertividade = (greens / total * 100) if total > 0 else 0
    
    st.sidebar.subheader(f"📊 Historico 7 Dias")
    st.sidebar.metric("Assertividade Over 1.5", f"{assertividade:.1f}%")
    st.sidebar.metric("Green", greens, delta=greens)
    st.sidebar.metric("Red", reds, delta=-reds)
    with st.sidebar.expander("Ver ultimos 10 jogos"):
        st.dataframe(df_hist.tail(10)[['data_prev', 'casa', 'fora', 'value', 'status']], use_container_width=True)

def poisson_prob(goals, lamb): return poisson.pmf(goals, lamb)
def calc_prob_over(lamb, linha): return 1 - sum([poisson_prob(i, lamb) for i in range(int(linha))])
def get_cor_prob(prob_str):
    try: valor = int(str(prob_str).replace('%', ''))
    except: return colors.black, colors.white
    if valor >= 80: return colors.HexColor("#0F5132"), colors.HexColor("#D1E7DD")
    elif valor > 75: return colors.HexColor("#664D03"), colors.HexColor("#FFF3CD")
    else: return colors.black, colors.white

def adicionar_marca_dagua(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 100)
    canvas.setFillColor(colors.HexColor("#E5E5E5"))
    canvas.setFillAlpha(0.05)
    canvas.drawCentredString(landscape(A4)[0] / 2.0, landscape(A4)[1] / 2.0, MARCA_DAGUA)
    canvas.restoreState()

def gerar_pdf_buffer(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=0.5*cm, leftMargin=0.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=18, alignment=1, fontName='Helvetica-Bold', textColor=colors.HexColor("#1A365D")))
    styles.add(ParagraphStyle(name='SubTitulo', fontSize=9, alignment=1, spaceAfter=12, textColor=colors.grey))
    styles.add(ParagraphStyle(name='LigaTitulo', fontSize=13, fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#2C5282")))

    elementos = [Paragraph(f"Relatorio Analisador asc.bet {VERSAO} - TOP 10", styles['Titulo']),
                 Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['SubTitulo'])]

    for liga, grupo in df.groupby('Liga'):
        elementos.append(Paragraph(f"LIGA: {liga}", styles['LigaTitulo']))
        colunas = ["Data", "PosCasa", "Casa", "PosFora", "Fora", "Odd 1.5", "Prob 0.5HT", "Prob 1.5FT", "Prob 2.5FT", "BTTS", "Casa", "Empate", "Fora", "Value"]
        dados_tabela = [colunas] + grupo[colunas].values.tolist()
        larguras = [1.6*cm, 0.9*cm, 2.5*cm, 0.9*cm, 2.5*cm, 1.3*cm, 1.4*cm, 1.4*cm, 1.4*cm, 1.2*cm, 1.2*cm, 1.2*cm, 1.2*cm, 1.4*cm]
        tabela = Table(dados_tabela, colWidths=larguras, repeatRows=1)
        estilo = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 6.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")])
        ])
        for i in range(1, len(dados_tabela)):
            cor_texto, cor_fundo = get_cor_prob(dados_tabela[i][7])
            estilo.add('TEXTCOLOR', (7, i), (7, i), cor_texto)
            estilo.add('FONTNAME', (7, i), (7, i), 'Helvetica-Bold')
            if cor_fundo!= colors.white: estilo.add('BACKGROUND', (7, i), (7, i), cor_fundo)
            for col in [10, 11, 12]:
                try:
                    if float(dados_tabela[i][col].replace('%','')) > 50:
                        estilo.add('BACKGROUND', (col, i), (col, i), colors.HexColor("#BFDBFE"))
                        estilo.add('FONTNAME', (col, i), (col, i), 'Helvetica-Bold')
                except: pass
            try:
                if float(dados_tabela[i][13].replace('%','')) > 20:
                    estilo.add('BACKGROUND', (13, i), (13, i), colors.HexColor("#A7F3D0"))
                    estilo.add('FONTNAME', (13, i), (13, i), 'Helvetica-Bold')
            except: pass # CORRIGIDO: tirei o try solto
        tabela.setStyle(estilo)
        elementos.append(tabela)
    doc.build(elementos, onFirstPage=adicionar_marca_dagua, onLaterPages=adicionar_marca_dagua)
    buffer.seek(0)
    return buffer

@st.cache_data(ttl=3600)
def get_standings(league_id):
    params = {"action": "get_standings", "league_id": league_id, "APIkey": API_FOOTBALL_KEY}
    try:
        data = requests.get(API_FOOTBALL_URL, params=params, timeout=10).json()
        if isinstance(data, dict): return {}, 2.5
        pos_dict = {t['team_name']: t['overall_league_position'] for t in data}
        total_gols = sum([int(t['overall_league_GF']) + int(t['overall_league_GA']) for t in data])
        total_jogos = sum([int(t['overall_league_payed']) for t in data])
        avg = (total_gols / total_jogos) if total_jogos > 0 else 2.5
        return pos_dict, avg
    except: return {}, 2.5

@st.cache_data(ttl=3600)
def get_last_8_games(team_id):
    params = {"action": "get_events", "team_id": team_id, "APIkey": API_FOOTBALL_KEY}
    try:
        data = requests.get(API_FOOTBALL_URL, params=params, timeout=10).json()
        return data[-8:] if isinstance(data, list) else []
    except: return []

@st.cache_data(ttl=900)
def get_odds_15(league_key, home_team, away_team):
    if not league_key: return 1.85
    url = f"{ODDS_API_URL}/{league_key}/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": "eu", "markets": "totals", "oddsFormat": "decimal"}
    try:
        r = requests.get(url, params=params, timeout=5).json()
        for game in r:
            if home_team.lower()[:4] in game['home_team'].lower() and away_team.lower()[:4] in game['away_team'].lower():
                for book in game['bookmakers']:
                    for market in book['markets']:
                        if market['key'] == 'totals':
                            for outcome in market['outcomes']:
                                if outcome['point'] == 1.5 and outcome['name'] == 'Over':
                                    return float(outcome['price'])
    except: pass
    return 1.85

def calcular_prob_poisson(home_id, away_id, league_id, home_name, away_name, league_key):
    pos_dict, league_avg = get_standings(league_id)
    home_pos = pos_dict.get(home_name, "-")
    away_pos = pos_dict.get(away_name, "-")
    home_games = [g for g in get_last_8_games(home_id) if g['match_hometeam_id'] == str(home_id)]
    away_games = [g for g in get_last_8_games(away_id) if g['match_awayteam_id'] == str(away_id)]
    home_gf = np.mean([int(g['match_hometeam_score']) for g in home_games]) if home_games else 1.2
    home_ga = np.mean([int(g['match_awayteam_score']) for g in home_games]) if home_games else 1.2
    away_gf = np.mean([int(g['match_awayteam_score']) for g in away_games]) if away_games else 1.0
    away_ga = np.mean([int(g['match_hometeam_score']) for g in away_games]) if away_games else 1.0
    home_attack = home_gf / (league_avg / 2) if league_avg > 0 else 1
    home_defense = home_ga / (league_avg / 2) if league_avg > 0 else 1
    away_attack = away_gf / (league_avg / 2) if league_avg > 0 else 1
    away_defense = away_ga / (league_avg / 2) if league_avg > 0 else 1
    home_lambda = home_attack * away_defense * (league_avg / 2)
    away_lambda = away_attack * home_defense * (league_avg / 2)
    total_lambda = home_lambda + away_lambda
    lambda_ht = total_lambda * 0.40
    prob_05ht = calc_prob_over(lambda_ht, 0.5) * 100
    prob_15ft = calc_prob_over(total_lambda, 1.5) * 100
    prob_25ft = calc_prob_over(total_lambda, 2.5) * 100
    prob_btts = (1 - poisson_prob(0, home_lambda)) * (1 - poisson_prob(0, away_lambda)) * 100
    prob_casa = prob_empate = prob_fora = 0
    for i in range(0, 6):
        for j in range(0, 6):
            p = poisson_prob(i, home_lambda) * poisson_prob(j, away_lambda)
            if i > j: prob_casa += p
            elif i == j: prob_empate += p
            else: prob_fora += p
    prob_casa *= 100; prob_empate *= 100; prob_fora *= 100
    odd_real = get_odds_15(league_key, home_name, away_name)
    value = (prob_15ft / 100) * odd_real - 1
    return f"{int(prob_05ht)}%", f"{int(prob_15ft)}%", f"{int(prob_25ft)}%", f"{int(prob_btts)}%", f"{int(prob_casa)}%", f"{int(prob_empate)}%", f"{int(prob_fora)}%", home_pos, away_pos, f"{odd_real:.2f}", f"{value*100:.1f}%"

@st.cache_data(ttl=1800)
def carregar_dados(ligas_selecionadas, filtro_value, filtro_prob, mostrar_todos):
    todos_jogos = []
    tz_br = pytz.timezone('America/Manaus')
    hoje_br = datetime.now(tz_br)
    data_inicio = hoje_br.strftime("%Y-%m-%d")
    data_fim = (hoje_br + timedelta(days=14)).strftime("%Y-%m-%d")
    st.info(f"Buscando jogos de {data_inicio} até {data_fim} em {len(ligas_selecionadas)} ligas")
    with st.spinner("Calculando Poisson Completo..."):
        for league_id in ligas_selecionadas:
            info = LIGAS_MAPA[league_id]
            nome_liga = info["nome"]
            league_key = info["odds_key"]
            params = {"action": "get_events", "league_id": league_id, "from": data_inicio, "to": data_fim, "APIkey": API_FOOTBALL_KEY}
            r = requests.get(API_FOOTBALL_URL, params=params, timeout=15)
            jogos = r.json()
            if isinstance(jogos, list):
                for jogo in jogos:
                    if jogo['match_status'] not in ["", "Not Started", "NS"]: continue
                    p05, p15, p25, btts, p_casa, p_empate, p_fora, pos_home, pos_away, odd, value = calcular_prob_poisson(
                        jogo['match_hometeam_id'], jogo['match_awayteam_id'], league_id,
                        jogo['match_hometeam_name'], jogo['match_awayteam_name'], league_key)
                    val_num = float(value.replace('%',''))
                    prob_num = int(p15.replace('%',''))
                    if not mostrar_todos:
                        if val_num < filtro_value and prob_num < filtro_prob: continue
                    todos_jogos.append({
                        "Liga": nome_liga, "Data": datetime.strptime(jogo['match_date'], "%Y-%m-%d").strftime("%d/%m/%Y"),
                        "PosCasa": pos_home, "Casa": jogo['match_hometeam_name'],
                        "PosFora": pos_away, "Fora": jogo['match_awayteam_name'],
                        "Odd 1.5": odd, "Prob 0.5HT": p05, "Prob 1.5FT": p15, "Prob 2.5FT": p25,
                        "BTTS": btts, "Casa": p_casa, "Empate": p_empate, "Fora": p_fora, "Value": value,
                        "ValueNum": val_num, "ProbNum": prob_num
                    })
    return pd.DataFrame(todos_jogos)

mostrar_historico()

st.sidebar.header("Filtros")
ligas_opcoes = {v["nome"]: k for k, v in LIGAS_MAPA.items()}
ligas_selecionadas = st.sidebar.multiselect("Selecione as Ligas", options=list(ligas_opcoes.keys()), default=list(ligas_opcoes.keys()))
st.sidebar.subheader("Filtro de Qualidade")
mostrar_todos = st.sidebar.checkbox("Mostrar todos os jogos", value=False)
filtro_value = st.sidebar.slider("Value Minimo %", 0, 50, 10)
filtro_prob = st.sidebar.slider("Prob 1.5FT Minima %", 60, 90, 75)
ligas_ids = [ligas_opcoes[nome] for nome in ligas_selecionadas]
df = carregar_dados(ligas_ids, filtro_value, filtro_prob, mostrar_todos)

if not df.empty:
    atualizar_historico(df)
    top3 = df[df['ValueNum'] > 40].sort_values(by='ValueNum', ascending=False).head(3)
    if not top3.empty:
        top3_text = " | ".join([f"{row['Casa']} x {row['Fora']} - {row['Value']}" for _, row in top3.iterrows()])
        st.success(f"🔥 TOP 3 DO DIA - Value > 40%: {top3_text}")
    df = df.sort_values(by='ProbNum', ascending=False).head(10)
    df_display = df.drop(columns=['ValueNum', 'ProbNum'])
    st.dataframe(df_display, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        pdf_buffer = gerar_pdf_buffer(df_display)
        st.download_button("📥 Baixar PDF", data=pdf_buffer, file_name=f"Relatorio_{VERSAO}_{datetime.now().strftime('%d%m%Y')}.pdf", mime="application/pdf", use_container_width=True)
    with col2:
        st.info("CSV desativado. Use o Historico na sidebar pra ver assertividade")
else:
    st.warning("Nenhum jogo encontrado. Marque 'Mostrar todos os jogos'")
