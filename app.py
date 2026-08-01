import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from scipy.stats import poisson

st.set_page_config(page_title="Analisador V26.7", layout="wide")
st.title("Analisador V26.7 - asc.bet PRO")
st.caption("Horario Manaus UTC-4 | ROI + Filtro Prob + Cores")

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"
ODD_PADRAO = 1.85 # Odd média pra simular ROI

def safe_int(valor):
    try: return int(valor) if valor is not None and valor!= '' else 0
    except: return 0

@st.cache_data(ttl=3600)
def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        r = requests.get(API_URL, params=params, timeout=60)
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
    prob_final = (p_2_5 * 70) + (p_1_5 * 20) + (p_0_5 * 10)
    prob_final = min(round(prob_final), 99)
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100)

def gerar_pdf_backtest(df, stats, periodo, stake):
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
    pdf.cell(0, 12, "asc.bet - RELATORIO BACKTEST", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Periodo: {periodo} | Stake: R${stake}", ln=True, align="C")
    
    lucro = (stats['1.5FT']['green'] * stake * (ODD_PADRAO - 1)) - (stats['1.5FT']['total'] * stake)
    roi = (lucro / (stats['1.5FT']['total'] * stake)) * 100 if stats['1.5FT']['total'] > 0 else 0
    pdf.cell(0, 8, f"ROI 1.5FT: {roi:.1f}% | Lucro: R${lucro:.2f} | Taxa: {stats['1.5FT']['taxa']:.1f}%", ln=True, align="C")
    pdf.ln(3)
    
    pdf.set_font("Arial", "B", 6)
    pdf.cell(22, 6, "Data", 1); pdf.cell(70, 6, "Jogo", 1); pdf.cell(15, 6, "Prob 1.5", 1, 0, 'C')
    pdf.cell(10, 6, "FT", 1, 0, 'C'); pdf.cell(15, 6, "1.5FT", 1, 1, 'C')
    
    pdf.set_font("Arial", "", 6)
    for i, row in df.iterrows():
        fill = True if i % 2 == 0 else False
        if fill: pdf.set_fill_color(240, 240, 240)
        if row.get('1.5FT') == 'GREEN': pdf.set_text_color(0, 128, 0)
        else: pdf.set_text_color(200, 0, 0)
        pdf.cell(22, 5, str(row.get('Data','N/A')), 1, 0, '', fill)
        pdf.cell(70, 5, str(row.get('Jogo','N/A'))[:35], 1, 0, '', fill)
        pdf.cell(15, 5, str(row.get('Prob 1.5','0'))+"%", 1, 0, 'C', fill)
        pdf.cell(10, 5, str(row.get('FT','0')), 1, 0, 'C', fill)
        pdf.cell(15, 5, str(row.get('1.5FT','RED')), 1, 1, 'C', fill)
        pdf.set_text_color(0, 0, 0)
    return bytes(pdf.output())

LIGAS_MAP = {462:"Brasileirao A", 463:"Brasileirao B", 148:"Premier League", 149:"Championship", 3:"La Liga", 4:"Serie A"}
LIGAS_IDS = list(LIGAS_MAP.keys())

tab1, tab2 = st.tabs(["ANALISADOR AO VIVO", "BACKTEST PRO V26.7"])

with tab1:
    st.sidebar.header("Filtros asc.bet")
    st.info("Use a aba Backtest")

with tab2:
    st.header("BACKTEST PRO - 0.5HT 1.5FT 2.5FT")
    st.warning("Limite: 50 jogos. API gratis = 100 chamadas/dia")

    col1, col2, col3 = st.columns(3)
    with col1:
        data_inicio = st.date_input("Data Inicio", datetime.now().date() - timedelta(days=7))
    with col2:
        data_fim = st.date_input("Data Fim", datetime.now().date() - timedelta(days=1))
    with col3:
        stake = st.number_input("Stake R$", 1, 1000, 10)
    
    ligas_disponiveis = ["Todas"] + list(LIGAS_MAP.values())
    liga_filtro = st.selectbox("Filtrar por Liga", ligas_disponiveis)
    
    col4, col5 = st.columns(2)
    with col4:
        limite_bt = st.slider("Prob Minima Backtest", 60, 90, 70)
    with col5:
        filtro_prob = st.slider("Filtro Prob 1.5 na Tabela", 60, 100, 70) # ITEM 2

    if st.button("RODAR BACKTEST"):
        with st.spinner("Rodando backtest..."):
            data_de = data_inicio.strftime("%Y-%m-%d")
            data_ate = data_fim.strftime("%Y-%m-%d")
            jogos = api_call("get_events", {"from": data_de, "to": data_ate})

            resultados_bt = []
            stats = {"0.5HT": {"total":0, "green":0, "taxa":0}, "1.5FT": {"total":0, "green":0, "taxa":0}, "2.5FT": {"total":0, "green":0, "taxa":0}}
            cache_times = {}

            if isinstance(jogos, list):
                jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished'][:50]
                if liga_filtro!= "Todas":
                    liga_id_filtro = [k for k, v in LIGAS_MAP.items() if v == liga_filtro][0]
                    jogos_finalizados = [j for j in jogos_finalizados if safe_int(j.get('league_id')) == liga_id_filtro]
                
                progress = st.progress(0)
                for idx, jogo in enumerate(jogos_finalizados):
                    try:
                        casa_id = jogo.get('match_hometeam_id')
                        fora_id = jogo.get('match_awayteam_id')
                        league_id = safe_int(jogo.get('league_id'))

                        cache_key = f"{casa_id}_{fora_id}"
                        if cache_key in cache_times:
                            prob_final, p_0_5, p_1_5, p_2_5 = cache_times[cache_key]
                        else:
                            prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, league_id)
                            cache_times[cache_key] = (prob_final, p_0_5, p_1_5, p_2_5)

                        if prob_final >= limite_bt:
                            gols_ht = safe_int(jogo.get('match_hometeam_score_ht')) + safe_int(jogo.get('match_awayteam_score_ht'))
                            gols_ft = safe_int(jogo.get('match_hometeam_score')) + safe_int(jogo.get('match_awayteam_score'))

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

                            # ITEM 2: FILTRO POR PROB NA TABELA
                            if p_1_5 >= filtro_prob:
                                resultados_bt.append({
                                    "Data": jogo.get('match_date'),
                                    "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                    "Liga": LIGAS_MAP.get(league_id, "Outra"),
                                    "Prob 0.5": p_0_5, "Prob 1.5": p_1_5, "Prob 2.5": p_2_5,
                                    "HT": gols_ht, "FT": gols_ft,
                                    "0.5HT": "GREEN" if green_05 else "RED",
                                    "1.5FT": "GREEN" if green_15 else "RED", # ITEM 3
                                    "2.5FT": "GREEN" if green_25 else "RED"
                                })
                    except: continue
                    progress.progress((idx + 1) / len(jogos_finalizados))

            if resultados_bt:
                df_bt = pd.DataFrame(resultados_bt)
                
                for m in stats:
                    total = stats[m]["total"]
                    green = stats[m]["green"]
                    stats[m]["taxa"] = (green / total) * 100 if total > 0 else 0

                st.success("BACKTEST CONCLUIDO")
                
                # ITEM 1: ROI SIMULADOR
                lucro = (stats['1.5FT']['green'] * stake * (ODD_PADRAO - 1)) - (stats['1.5FT']['total'] * stake)
                roi = (lucro / (stats['1.5FT']['total'] * stake)) * 100 if stats['1.5FT']['total'] > 0 else 0
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("0.5HT", f"{stats['0.5HT']['taxa']:.1f}%", f"{stats['0.5HT']['green']}/{stats['0.5HT']['total']}")
                col2.metric("1.5FT", f"{stats['1.5FT']['taxa']:.1f}%", f"{stats['1.5FT']['green']}/{stats['1.5FT']['total']}")
                col3.metric("2.5FT", f"{stats['2.5FT']['taxa']:.1f}%", f"{stats['2.5FT']['green']}/{stats['2.5FT']['total']}")
                col4.metric("ROI 1.5FT", f"{roi:.1f}%", f"R${lucro:.2f}")

                # ITEM 3: CORES NA TABELA
                def color_result(val):
                    if val == 'GREEN': return 'background-color: #d4edda; color: #155724; font-weight: bold'
                    elif val == 'RED': return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                    else: return ''
                
                st.dataframe(df_bt.style.applymap(color_result, subset=['0.5HT', '1.5FT', '2.5FT']), use_container_width=True)
                
                periodo = f"{data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m')}"
                pdf_bytes = gerar_pdf_backtest(df_bt, stats, periodo, stake)
                st.download_button("Baixar Relatorio PDF", pdf_bytes, f"backtest_{data_inicio}.pdf", "application/pdf")
                
                csv_bt = df_bt.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Backtest CSV", csv_bt, f"backtest_{data_inicio}.csv", "text/csv")
            else:
                st.warning("Nenhum jogo encontrado com esse filtro")
