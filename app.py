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
from datetime import datetime

VERSAO = "V26.7.5"
MARCA_DAGUA = "asc.bet"
API_FOOTBALL_URL = "https://apiv3.apifootball.com/"
API_FOOTBALL_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"

ODDS_API_KEY = "cc7a0c9ee51e4bc96110d49730acacaa" # SUA KEY DA THE ODDS API
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports"

# SUAS LIGAS DO ARQUIVO + MAPEAMENTO COM ODDSAPI
LIGAS_MAPA = {
    # BRASIL / AMERICA
    462: {"nome": "BRASIL SERIE A", "odds_key": "soccer_brazil_campeonato"},
    463: {"nome": "BRASIL SERIE B", "odds_key": "soccer_brazil_serie_b"},
    464: {"nome": "BRASIL SERIE C", "odds_key": None},
    37: {"nome": "ARGENTINA PRIMERA DIVISION", "odds_key": "soccer_argentina_liga_profesional"},
    65: {"nome": "CHILE PRIMERA DIVISION", "odds_key": None},
    81: {"nome": "COLOMBIA PRIMERA A", "odds_key": None},
    232: {"nome": "PARAGUAI PRIMERA DIVISION", "odds_key": None},
    263: {"nome": "URUGUAI PRIMERA DIVISION", "odds_key": None},
    274: {"nome": "VENEZUELA LIGA FUTVE", "odds_key": None},
    206: {"nome": "MEXICO LIGA MX", "odds_key": "soccer_mexico_ligamx"},
    244: {"nome": "USA MLS", "odds_key": "soccer_usa_mls"},

    # EUROPA TOP
    148: {"nome": "INGLATERRA PREMIER LEAGUE", "odds_key": "soccer_epl"},
    149: {"nome": "INGLATERRA CHAMPIONSHIP", "odds_key": None},
    302: {"nome": "ESPANHA LA LIGA", "odds_key": "soccer_spain_la_liga"},
    2077: {"nome": "ITALIA SERIE A", "odds_key": "soccer_italy_serie_a"},
    175: {"nome": "ALEMANHA BUNDESLIGA", "odds_key": "soccer_germany_bundesliga"},
    168: {"nome": "FRANCA LIGUE 1", "odds_key": "soccer_france_ligue_one"},
    94: {"nome": "PORTUGAL PRIMEIRA LIGA", "odds_key": "soccer_portugal_primeira_liga"},
    183: {"nome": "HOLANDA EREDIVISIE", "odds_key": "soccer_netherlands_eredivisie"},
    54: {"nome": "BELGICA JUPILER PRO LEAGUE", "odds_key": "soccer_belgium_first_div"},
    245: {"nome": "SUECIA ALLSVENSKAN", "odds_key": None},
    118: {"nome": "DINAMARCA SUPERLIGAEN", "odds_key": "soccer_denmark_superliga"},
    142: {"nome": "FINLANDIA VEIKKAUSLIIGA", "odds_key": None},
    237: {"nome": "POLONIA EKSTRAKLASA", "odds_key": "soccer_poland_ekstraklasa"},
    105: {"nome": "CROACIA HNL", "odds_key": None},
    191: {"nome": "HUNGRIA NB I", "odds_key": None},
    243: {"nome": "SUIÇA SUPER LEAGUE", "odds_key": "soccer_switzerland_superleague"},
    262: {"nome": "TURQUIA SUPER LIG", "odds_key": "soccer_turkey_super_league"},
    164: {"nome": "GRECIA SUPER LEAGUE 1", "odds_key": "soccer_greece_super_league"},
    195: {"nome": "ISRAEL LIGAT HA'AL", "odds_key": None},

    # ASIA / OCEANIA
    50: {"nome": "AUSTRALIA A-LEAGUE", "odds_key": "soccer_australia_aleague"},
    201: {"nome": "JAPAO J1 LEAGUE", "odds_key": "soccer_japan_jleague"},
    71: {"nome": "CHINA SUPER LEAGUE", "odds_key": "soccer_china_superleague"},
    320: {"nome": "COREIA DO SUL K LEAGUE 1", "odds_key": "soccer_korea_kleague1"},
    193: {"nome": "INDIA SUPER LEAGUE", "odds_key": None},
    305: {"nome": "ARABIA SAUDITA PRO LEAGUE", "odds_key": "soccer_saudi_professional_league"},
}

st.set_page_config(page_title=f"Analisador asc.bet {VERSAO}", layout="wide")
st.title(f"Analisador asc.bet {VERSAO} - TOP 20 + Value Real")

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
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=0.8*cm, leftMargin=0.8*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=18, alignment=1, fontName='Helvetica-Bold', textColor=colors.HexColor("#1A365D")))
    styles.add(ParagraphStyle(name='SubTitulo', fontSize=9, alignment=1, spaceAfter=12, textColor=colors.grey))
    styles.add(ParagraphStyle(name='LigaTitulo', fontSize=13, fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#2C5282")))

    elementos = [Paragraph(f"Relatorio Analisador asc.bet {VERSAO} - TOP 20", styles['Titulo']),
                 Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['SubTitulo'])]

    for liga, grupo in df.groupby('Liga'):
        elementos.append(Paragraph(f"LIGA: {liga}", styles['LigaTitulo']))
        colunas = ["Data", "Pos", "Casa", "Pos", "Fora", "Odd 1.5", "Prob 1.5FT", "Value"]
        dados_tabela = [colunas] + grupo[colunas].values.tolist()
        larguras = [2.2*cm, 1*cm, 4.5*cm, 1*cm, 4.5*cm, 1.8*cm, 2.2*cm, 2*cm]
        tabela = Table(dados_tabela, colWidths=larguras, repeatRows=1)
        estilo = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")])])

        for i in range(1, len(dados_tabela)):
            cor_texto, cor_fundo = get_cor_prob(dados_tabela[i][6]) # Prob 1.5
            estilo.add('TEXTCOLOR', (6, i), (6, i), cor_texto)
            estilo.add('FONTNAME', (6, i), (6, i), 'Helvetica-Bold')
            if cor_fundo!= colors.white: estilo.add('BACKGROUND', (6, i), (6, i), cor_fundo)

            try: # Pinta Value
                if float(dados_tabela[i][7].replace('%','')) > 5:
                    estilo.add('BACKGROUND', (7, i), (7, i), colors.HexColor("#A7F3D0"))
                    estilo.add('FONTNAME', (7, i), (7, i), 'Helvetica-Bold')
            except: pass
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
            if home_team.lower()[:5] in game['home_team'].lower() and away_team.lower()[:5] in game['away_team'].lower():
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

    home_attack = home_gf / (league_avg / 2)
    home_defense = home_ga / (league_avg / 2)
    away_attack = away_gf / (league_avg / 2)
    away_defense = away_ga / (league_avg / 2)

    home_lambda = home_attack * away_defense * (league_avg / 2)
    away_lambda = away_attack * home_defense * (league_avg / 2)
    total_lambda = home_lambda + away_lambda

    prob_15ft = calc_prob_over(total_lambda, 1.5) * 100
    prob_25ft = calc_prob_over(total_lambda, 2.5) * 100
    lambda_ht = total_lambda * 0.45
    prob_05ht = calc_prob_over(lambda_ht, 0.5) * 100

    odd_real = get_odds_15(league_key, home_name, away_name)
    value = (prob_15ft / 100) * odd_real - 1
    value_str = f"{value*100:.1f}%"

    return f"{int(prob_05ht)}%", f"{int(prob_15ft)}%", f"{int(prob_25ft)}%", home_pos, away_pos, f"{odd_real:.2f}", value_str

@st.cache_data(ttl=1800)
def carregar_dados():
    todos_jogos = []
    hoje = datetime.now().strftime("%Y-%m-%d")
    with st.spinner("Calculando Poisson + Odds Reais + Tabela..."):
        for league_id, info in LIGAS_MAPA.items():
            nome_liga = info["nome"]
            league_key = info["odds_key"]
            jogos = requests.get(API_FOOTBALL_URL, params={"action": "get_fixtures", "league_id": league_id, "from": hoje, "to": hoje, "APIkey": API_FOOTBALL_KEY}, timeout=15).json()
            if isinstance(jogos, list):
                for jogo in jogos:
                    p05, p15, p25, pos_home, pos_away, odd, value = calcular_prob_poisson(
                        jogo['match_hometeam_id'], jogo['match_awayteam_id'], league_id,
                        jogo['match_hometeam_name'], jogo['match_awayteam_name'], league_key
                    )
                    todos_jogos.append({
                        "Liga": nome_liga, "Data": datetime.strptime(jogo['match_date'], "%Y-%m-%d").strftime("%d/%m/%Y"),
                        "Pos": pos_home, "Casa": jogo['match_hometeam_name'],
                        "Pos": pos_away, "Fora": jogo['match_awayteam_name'],
                        "Odd 1.5": odd, "Prob 0.5FT": p05, "Prob 1.5FT": p15, "Prob 2.5FT": p25, "Value": value,
                    })
    return pd.DataFrame(todos_jogos)

df = carregar_dados()
if not df.empty:
    df['Prob 1.5FT Num'] = df['Prob 1.5FT'].str.replace('%','').astype(int)
    df = df.sort_values(by='Prob 1.5FT Num', ascending=False).head(20)
    df = df.drop(columns=['Prob 1.5FT Num'])
    st.dataframe(df, use_container_width=True)
    pdf_buffer = gerar_pdf_buffer(df)
    st.download_button("📥 Baixar PDF do Relatorio", data=pdf_buffer, file_name=f"Relatorio_Analisador_{VERSAO}_{datetime.now().strftime('%d%m%Y')}.pdf", mime="application/pdf", use_container_width=True)
else:
    st.warning("Nenhum jogo encontrado hoje para as ligas.")
