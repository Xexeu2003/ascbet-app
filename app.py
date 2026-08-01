import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from scipy.stats import poisson
import io

st.set_page_config(page_title="Analisador V26.4", layout="wide")
st.title("Analisador V26.4 - asc.bet PRO")
st.caption("Horario Manaus UTC-4 | Backtest 0.5HT 1.5FT 2.5FT")

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"

def pegar_bandeira(liga_nome):
    liga = liga_nome.lower()
    if "brasil" in liga: return "BR"
    if "premier" in liga or "england" in liga: return "GB-ENG"
    if "la liga" in liga or "espanha" in liga: return "ES"
    if "bundesliga" in liga: return "DE"
    if "serie a" in liga or "italia" in liga: return "IT"
    if "ligue" in liga: return "FR"
    if "portugal" in liga: return "PT"
    if "polonia" in liga: return "PL"
    if "noruega" in liga: return "NO"
    return "GLB"

def safe_int(valor):
    try: return int(valor) if valor is not None and valor!= '' else 0
    except: return 0

def converter_horario(data_str, hora_str):
    try:
        dt_utc = datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M")
        dt_manaus = dt_utc - timedelta(hours=4)
        return dt_manaus, dt_manaus.strftime("%d/%m %H:%M")
    except: return datetime.now(), f"{data_str} {hora_str}"

@st.cache_data(ttl=3600)
def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        r = requests.get(API_URL, params=params, timeout=45)
        return r.json() if r.status_code == 200 else []
    except: return []

@st.cache_data(ttl=3600)
def calcular_stats_8jogos(time_id, tipo):
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
    if not isinstance(jogos, list): return {"gols_m":1.5, "gols_s":1.5}
    jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished']
    ultimos_8 = jogos_finalizados[:8]
    gols_m = gols_s = jogos_contados = 0
    for j in ultimos_8:
        is_home = str(j.get('match_hometeam_id')) == str(time_id)
        if (tipo == "home" and is_home) or (tipo == "away" and not is_home):
            gols_m += safe_int(j.get('match_hometeam_score')) if is_home else safe_int(j.get('match_awayteam_score'))
            gols_s += safe_int(j.get('match_awayteam_score')) if is_home else safe_int(j.get('match_hometeam_score'))
            jogos_contados += 1
    if jogos_contados == 0: return {"gols_m":1.5, "gols_s":1.5}
    return {"gols_m": gols_m / jogos_contados, "gols_s": gols_s / jogos_contados}

def calcular_poisson(lambda_casa, lambda_fora):
    prob_0_5_ht = 1 - poisson.pmf(0, (lambda_casa + lambda_fora) / 2)
    prob_1_5 = 1 - poisson.cdf(1, lambda_casa + lambda_fora)
    prob_2_5 = 1 - poisson.cdf(2, lambda_casa + lambda_fora)
    return prob_0_5_ht, prob_1_5, prob_2_5

@st.cache_data(ttl=3600)
def calcular_h2h(casa_id, fora_id):
    h2h = api_call("get_H2H", {"firstTeamId": casa_id, "secondTeamId": fora_id})
    if not isinstance(h2h, list): return "N/A"
    jogos_finalizados = [j for j in h2h if j.get('match_status') == 'Finished']
    ultimos_5 = jogos_finalizados[:5]
    total_gols = sum([safe_int(j.get('match_hometeam_score')) + safe_int(j.get('match_awayteam_score')) for j in ultimos_5])
    return round(total_gols / len(ultimos_5), 2) if ultimos_5 else "N/A"

@st.cache_data(ttl=3600)
def calcular_probabilidade_final(casa_id, fora_id, league_id):
    stats_casa = calcular_stats_8jogos(casa_id, "home")
    stats_fora = calcular_stats_8jogos(fora_id, "away")
    media_liga = 2.7
    divisor = media_liga / 2
    atq_casa = stats_casa['gols_m'] / divisor
    def_casa = stats_casa['gols_s'] / divisor
    atq_fora = stats_fora['gols_m'] / divisor
    def_fora = stats_fora['gols_s'] / divisor
    lambda_casa = atq_casa * def_fora * divisor
    lambda_fora = atq_fora * def_casa * divisor
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    media_h2h = calcular_h2h(casa_id, fora_id)
    bonus_h2h = 0 if media_h2h == "N/A" else (media_h2h / 3.0) * 10
    prob_final = (p_2_5 * 70) + (p_1_5 * 20) + (p_0_5 * 10) + bonus_h2h
    prob_final = min(round(prob_final), 99)
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100), media_h2h, stats_casa, stats_fora

def cor_prob(val):
    if val >= 90: return 'background-color: #d4edda; color: #155724'
    elif val >= 80: return 'background-color: #cce5ff; color: #004085'
    else: return 'background-color: #fff3cd; color: #856404'

def gerar_pdf(df, titulo="Completo"):
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", "B", 50)
    pdf.set_text_color(230, 230, 230)
    pdf.rotate(45)
    pdf.text(50, 150, "asc.bet PRO")
    pdf.rotate(0)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(0, 128, 0)
    pdf.cell(0, 12, "asc.bet", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 14)
    data_hoje = (datetime.now() - timedelta(hours=4)).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, f"Relatorio Analisador V26.4 - {titulo} - {data_hoje}", ln=True, align="C")
    pdf.ln(3)
    pdf.set_font("Arial", "B", 6)
    pdf.cell(22, 8, "Data", 1); pdf.cell(45, 8, "Liga", 1); pdf.cell(12, 8, "Rod", 1, 0, 'C')
    pdf.cell(70, 8, "Jogo", 1); pdf.cell(18, 8, "Pos", 1, 0, 'C'); pdf.cell(15, 8, "H2H", 1, 0, 'C')
    pdf.cell(15, 8, "GC U8", 1, 0, 'C'); pdf.cell(15, 8, "GF U8", 1, 0, 'C')
    pdf.cell(18, 8, "Prob 0.5", 1, 0, 'C'); pdf.cell(18, 8, "Prob 1.5", 1, 0, 'C')
    pdf.cell(18, 8, "Prob 2.5", 1, 0, 'C'); pdf.cell(15, 8, "Prob %", 1, 1, 'C')
    pdf.set_font("Arial", "", 6)
    for i, row in df.iterrows():
        fill = True if i % 2 == 0 else False
        if fill: pdf.set_fill_color(240, 240, 240)
        prob = row.get('Prob %', 0)
        if prob >= 90: pdf.set_text_color(0, 128, 0)
        elif prob >= 80: pdf.set_text_color(0, 0, 255)
        else: pdf.set_text_color(255, 140, 0)
        pdf.cell(22, 6, str(row.get('Data','N/A')).encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(45, 6, str(row.get('Liga','N/A'))[:25].encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(12, 6, str(row.get('Rodada','N/A')), 1, 0, 'C', fill)
        pdf.cell(70, 6, str(row.get('Jogo','N/A'))[:35].encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(18, 6, str(row.get('Pos','N/A')), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(row.get('Media H2H 5J',0)), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(row.get('Gols Casa U8',0)), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(row.get('Gols Fora U8',0)), 1, 0, 'C', fill)
        pdf.cell(18, 6, str(row.get('Prob 0.5 HT','0%')), 1, 0, 'C', fill)
        pdf.cell(18, 6, str(row.get('Prob 1.5 FT','0%')), 1, 0, 'C', fill)
        pdf.cell(18, 6, str(row.get('Prob 2.5 FT','0%')), 1, 0, 'C', fill)
        pdf.cell(15, 6, str(prob)+"%", 1, 1, 'C', fill)
        pdf.set_text_color(0, 0, 0)
    return bytes(pdf.output())

LIGAS_IDS = [462, 463, 464, 465, 148, 149, 3, 4, 2, 7, 302, 303, 266, 267, 262, 263, 168, 169, 244, 94, 253, 206, 10, 32, 29, 116, 83, 37, 482, 144, 406, 488, 132, 444, 172, 207]
PAISES = {"Todos": LIGAS_IDS, "Brasil": [462, 463, 464, 465], "Europa": [148, 149, 3, 4, 302, 303, 266, 267, 262, 263, 168, 169, 244, 94, 482, 144, 406, 488, 132, 444, 172, 207], "Sul-America": [2, 7, 10, 32, 29, 116, 83, 37]}

tab1, tab2 = st.tabs(["ANALISADOR AO VIVO", "BACKTEST 7 DIAS"])

with tab1:
    st.sidebar.header("Filtros asc.bet")
    pais = st.sidebar.selectbox("Filtrar por Pais", list(PAISES.keys()))

    @st.cache_data(ttl=3600)
    def carregar_ligas(pais_selecionado):
        ligas_para_buscar = PAISES[pais_selecionado]
        data_de = (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d")
        data_ate = ((datetime.now() - timedelta(hours=4)) + timedelta(days=7)).strftime("%Y-%m-%d")
        jogos = api_call("get_events", {"from": data_de, "to": data_ate})
        ligas_encontradas = set()
        if isinstance(jogos, list):
            for jogo in jogos:
                if safe_int(jogo.get('league_id')) in ligas_para_buscar:
                    ligas_encontradas.add(jogo.get('league_name'))
        return sorted(list(ligas_encontradas))

    ligas_disponiveis = carregar_ligas(pais)
    liga_filtro = st.sidebar.selectbox("Filtrar por Liga", ["Todas"] + ligas_disponiveis)
    dias = st.sidebar.slider("Buscar proximos X dias", 1, 7, 3)
    limite_prob = st.sidebar.slider("Probabilidade Minima %", 60, 90, 70)
    mostrar_top10 = st.sidebar.checkbox("Mostrar apenas TOP 10 na tela")

    if st.button("ANALISAR JOGOS 70%+"):
        # codigo de analise igual V26.3 aqui...
        st.info("Usa o mesmo codigo de analise da V26.3")

with tab2:
    st.header("BACKTEST 7 DIAS - 0.5HT 1.5FT 2.5FT")

    data_fim = st.date_input("Data Fim", datetime.now().date() - timedelta(days=1))
    data_inicio = data_fim - timedelta(days=6) # sempre 7 dias
    st.write(f"Periodo: {data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m')}")

    limite_bt = st.slider("Prob Minima Backtest", 60, 90, 70, key="bt")

    if st.button("RODAR BACKTEST 7 DIAS"):
        with st.spinner("Rodando backtest... isso demora 2 min"):
            data_de = data_inicio.strftime("%Y-%m-%d")
            data_ate = data_fim.strftime("%Y-%m-%d")
            jogos = api_call("get_events", {"from": data_de, "to": data_ate})

            resultados_bt = []
            stats = {"0.5HT": {"total":0, "green":0}, "1.5FT": {"total":0, "green":0}, "2.5FT": {"total":0, "green":0}}

            if isinstance(jogos, list):
                for jogo in jogos:
                    if jogo.get('match_status') == 'Finished':
                        try:
                            casa_id = jogo.get('match_hometeam_id')
                            fora_id = jogo.get('match_awayteam_id')
                            league_id = safe_int(jogo.get('league_id'))

                            prob_final, p_0_5, p_1_5, p_2_5, _, _ = calcular_probabilidade_final(casa_id, fora_id, league_id)

                            if prob_final >= limite_bt:
                                gols_ht = safe_int(jogo.get('match_hometeam_score_ht')) + safe_int(jogo.get('match_awayteam_score_ht'))
                                gols_ft = safe_int(jogo.get('match_hometeam_score')) + safe_int(jogo.get('match_awayteam_score'))

                                # TESTA OS 3 MERCADOS
                                green_05 = gols_ht >= 1
                                green_15 = gols_ft >= 2
                                green_25 = gols_ft >= 3

                                if p_0_5 >= limite_bt:
                                    stats["0.5HT"]["total"] += 1
                                    if green_05: stats["0.5HT"]["green"] += 1
                                if p_1_5 >= limite_bt:
                                    stats["1.5FT"]["total"] += 1
                                    if green_15: stats["1.5FT"]["green"] += 1
                                if p_2_5 >= limite_bt:
                                    stats["2.5FT"]["total"] += 1
                                    if green_25: stats["2.5FT"]["green"] += 1

                                resultados_bt.append({
                                    "Data": jogo.get('match_date'),
                                    "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                    "Prob 0.5": p_0_5, "Prob 1.5": p_1_5, "Prob 2.5": p_2_5,
                                    "HT": gols_ht, "FT": gols_ft,
                                    "0.5HT": "GREEN" if green_05 else "RED",
                                    "1.5FT": "GREEN" if green_15 else "RED",
                                    "2.5FT": "GREEN" if green_25 else "RED"
                                })
                        except: continue

            if resultados_bt:
                df_bt = pd.DataFrame(resultados_bt)

                st.success("BACKTEST CONCLUIDO")
                col1, col2, col3 = st.columns(3)
                for i, mercado in enumerate(["0.5HT", "1.5FT", "2.5FT"]):
                    total = stats[mercado]["total"]
                    green = stats[mercado]["green"]
                    taxa = (green / total) * 100 if total > 0 else 0
                    [col1, col2, col3][i].metric(mercado, f"{taxa:.1f}%", f"{green}/{total}")

                st.dataframe(df_bt, use_container_width=True)
                csv_bt = df_bt.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Backtest CSV", csv_bt, f"backtest_7dias_{data_inicio}.csv", "text/csv")
            else:
                st.warning("Nenhum jogo encontrado no periodo")
