import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from scipy.stats import poisson
from collections import defaultdict
from fpdf import FPDF

st.set_page_config(page_title="Analisador V26.6.4", layout="wide")
st.title("Analisador V26.6.4 - asc.bet PRO")
st.caption("Horario Manaus UTC-4 | 40 Ligas | Busca por Liga | +Pais +Rodada +Posicao +PDF")

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"

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
def get_standings(league_id):
    standings = api_call("get_standings", {"league_id": league_id})
    pos_map = {}
    if isinstance(standings, list):
        for time in standings:
            pos_map[str(time.get('team_id'))] = safe_int(time.get('overall_league_position'))
    return pos_map

@st.cache_data(ttl=3600)
def get_league_info(league_id):
    ligas = api_call("get_leagues", {"league_id": league_id})
    if isinstance(ligas, list) and len(ligas) > 0:
        return ligas[0].get('country_name'), ligas[0].get('league_name')
    return "N/A", "N/A"

@st.cache_data(ttl=3600)
def calcular_stats_5jogos(time_id, tipo):
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
    if not isinstance(jogos, list): return {"gols_m":1.5, "gols_s":1.5}
    jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished']
    ultimos_5 = jogos_finalizados[:5]
    gols_m = gols_s = jogos_contados = 0
    for j in ultimos_5:
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

def calcular_probabilidade_final(casa_id, fora_id, league_id):
    stats_casa = calcular_stats_5jogos(casa_id, "home")
    stats_fora = calcular_stats_5jogos(fora_id, "away")
    media_liga = 2.6
    divisor = media_liga / 2
    atq_casa = stats_casa['gols_m'] / divisor
    def_casa = stats_casa['gols_s'] / divisor
    atq_fora = stats_fora['gols_m'] / divisor
    def_fora = stats_fora['gols_s'] / divisor
    lambda_casa = atq_casa * def_fora * divisor
    lambda_fora = atq_fora * def_casa * divisor
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    prob_final = (p_2_5 * 60) + (p_1_5 * 30) + (p_0_5 * 10)
    prob_final = min(round(prob_final), 99)
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100)

def gerar_pdf(resultados, stats, ranking, periodo, ligas):
    pdf = FPDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'RELATORIO BACKTEST V26.6.4', 0, 1, 'C')
    pdf.set_font('Arial', '', 10); pdf.cell(0, 8, f'Periodo: {periodo} | Ligas: {", ".join(ligas)}', 0, 1, 'C'); pdf.ln(5)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 8, 'RESUMO GERAL', 0, 1); pdf.set_font('Arial', '', 10)
    taxa_15 = (stats['1.5FT']['green'] / stats['1.5FT']['total'] * 100) if stats['1.5FT']['total'] > 0 else 0
    pdf.cell(0, 6, f'Taxa 1.5FT: {taxa_15:.1f}% - {stats["1.5FT"]["green"]}/{stats["1.5FT"]["total"]} jogos', 0, 1); pdf.ln(5)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 8, 'RANKING DE LIGAS - 1.5FT', 0, 1); pdf.set_font('Arial', '', 9)
    for liga, dados in ranking.items(): taxa = (dados["green"]/dados["total"]*100 if dados["total"]>0 else 0); pdf.cell(0, 6, f'{liga}: {taxa:.1f}% - {dados["green"]}/{dados["total"]}', 0, 1)
    pdf.ln(5); pdf.set_font('Arial', 'B', 8)
    pdf.cell(18, 7, 'Data', 1); pdf.cell(20, 7, 'Pais', 1); pdf.cell(55, 7, 'Jogo', 1); pdf.cell(15, 7, 'Rodada', 1); pdf.cell(15, 7, 'Prob', 1); pdf.cell(10, 7, 'FT', 1); pdf.cell(15, 7, 'Result', 1); pdf.ln()
    pdf.set_font('Arial', '', 7)
    for _, row in resultados.iterrows():
        pdf.cell(18, 6, str(row['Data']), 1); pdf.cell(20, 6, str(row['Pais'])[:10], 1); pdf.cell(55, 6, str(row['Jogo'])[:28], 1)
        pdf.cell(15, 6, str(row['Rodada']), 1); pdf.cell(15, 6, f"{row['Prob 1.5']}%", 1); pdf.cell(10, 6, str(row['FT']), 1); pdf.cell(15, 6, str(row['1.5FT']), 1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# 40 LIGAS - CORRIGI O NOME "Besta deild karla"
LIGAS_MAP = {
    462:"Brasileirao A", 463:"Brasileirao B", 148:"Premier League", 152:"Championship",
    149:"La Liga", 207:"La Liga 2", 175:"Bundesliga", 176:"2. Bundesliga",
    262:"Serie A", 263:"Serie B", 168:"Ligue 1", 169:"Ligue 2",
    302:"K League 1", 303:"K League 2", 310:"J1 League", 311:"J2 League",
    253:"Campeonato Chileno", 255:"Primera B Chile", 339:"Allsvenskan", 340:"Eliteserien",
    341:"Superliga Dinamarca", 342:"Veikkausliiga", 343:"Premier League Russia",
    344:"MLS", 345:"Liga MX", 346:"Eredivisie", 347:"Liga Portugal",
    348:"Super Lig Turquia", 349:"Premier League Ucrania", 350:"Besta deild karla", # CORRIGIDO
    351:"Superliga Grecia", 352:"Liga I Romania", 353:"Premijer Liga Bosnia",
    354:"HNL Croacia", 355:"Fortuna Liga Tcheca", 356:"Ekstraklasa Polonia",
    357:"Superliga Suica", 358:"Austrian Bundesliga", 359:"Jupiler Pro League",
    271:"Superliga Chinesa", 128:"Liga Profesional Argentina", 250:"Liga BetPlay Dimayor"
}

tab1, tab2, tab3 = st.tabs(["ANALISADOR AO VIVO", "BACKTEST PRO", "EXPORTAR PDF"])

# ABA 1: AO VIVO
with tab1:
    st.header("ANALISADOR AO VIVO - V26.6.4")
    
    col1, col2 = st.columns(2)
    with col1:
        ligas_ao_vivo = st.multiselect(
            "Selecionar Ligas", 
            list(LIGAS_MAP.values()), 
            default=["K League 1", "J1 League", "Besta deild karla"]
        )
    with col2:
        filtro_prob_vivo = st.slider("Filtro Prob Minima", 70, 95, 80)
    
    if st.button("ATUALIZAR AO VIVO"):
        with st.spinner("Buscando jogos por liga..."):
            data_hoje = datetime.now().strftime("%Y-%m-%d")
            jogos_ao_vivo = []
            
            ids_foco = {k: v for k, v in LIGAS_MAP.items() if v in ligas_ao_vivo} # dict agora
            
            for league_id, nome_liga_selecionada in ids_foco.items():
                # CORRECAO PRINCIPAL: Buscar 1 liga por vez
                jogos_liga = api_call("get_events", {"league_id": league_id, "from": data_hoje, "to": data_hoje})
                
                if not isinstance(jogos_liga, list): continue
                
                standings_cache = get_standings(league_id)
                pais, nome_liga = get_league_info(league_id)
                
                for jogo in jogos_liga:
                    status = jogo.get('match_status')
                    if status not in ['Finished', 'Not Started', 'Postponed', 'Cancelled']:
                        try:
                            casa_id = jogo.get('match_hometeam_id')
                            fora_id = jogo.get('match_awayteam_id')
                            prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, league_id)
                            
                            if p_1_5 >= filtro_prob_vivo:
                                gols_ft = safe_int(jogo.get('match_hometeam_score')) + safe_int(jogo.get('match_awayteam_score'))
                                rodada = jogo.get('league_round') if jogo.get('league_round') else "N/A"
                                
                                jogos_ao_vivo.append({
                                    "Data": jogo.get('match_date'),
                                    "Hora": jogo.get('match_time'),
                                    "Pais": pais,
                                    "Liga": nome_liga,
                                    "Rodada": rodada,
                                    "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                    "Pos Casa": standings_cache.get(str(casa_id), '-'),
                                    "Pos Fora": standings_cache.get(str(fora_id), '-'),
                                    "Placar": f"{jogo.get('match_hometeam_score')} x {jogo.get('match_awayteam_score')}",
                                    "Minuto": jogo.get('match_status'),
                                    "Prob 1.5": p_1_5,
                                    "Prob 2.5": p_2_5,
                                    "1.5FT": "GREEN" if gols_ft >= 2 else "AGUARDANDO"
                                })
                        except: continue
            
            if jogos_ao_vivo:
                df_vivo = pd.DataFrame(jogos_ao_vivo).sort_values("Prob 1.5", ascending=False)
                st.success(f"ENCONTRADOS {len(df_vivo)} JOGOS NAS {len(ids_foco)} LIGAS")
                
                def color_result(val):
                    if val == 'GREEN': return 'background-color: #d4edda; color: #155724; font-weight: bold'
                    elif val == 'AGUARDANDO': return 'background-color: #fff3cd; color: #856404'
                    else: return ''
                
                def color_prob(val):
                    if val >= 90: return 'background-color: #28a745; color: white; font-weight: bold'
                    elif val >= 85: return 'background-color: #ffc107; color: black; font-weight: bold'
                    else: return ''
                
                st.dataframe(df_vivo.style.map(color_result, subset=['1.5FT']).map(color_prob, subset=['Prob 1.5', 'Prob 2.5']), use_container_width=True)
            else:
                st.warning("Nenhum jogo ao vivo encontrado nas ligas selecionadas hoje")

# ABA 2 E 3: IGUAIS A V26.6.3
with tab2:
    st.header("BACKTEST PRO - V26.6.4")
    col1, col2, col3, col4 = st.columns(4)
    with col1: data_inicio = st.date_input("Data Inicio", datetime(2025,8,1).date())
    with col2: data_fim = st.date_input("Data Fim", datetime(2025,9,30).date())
    with col3: stake = st.number_input("Stake R$", 1, 1000, 10)
    with col4: odd_real = st.number_input("Odd", 1.10, 3.00, 1.90, 0.05)
    ligas_selecionadas = st.multiselect("Selecionar Ligas", list(LIGAS_MAP.values()), default=["K League 1", "J1 League"])
    limite_bt = st.slider("Prob Minima", 60, 90, 70)
    if 'df_bt_global' not in st.session_state: st.session_state.df_bt_global = None; st.session_state.stats_global = None; st.session_state.ranking_global = None
    if st.button("RODAR BACKTEST"):
        with st.spinner("Rodando backtest..."):
            data_de = data_inicio.strftime("%Y-%m-%d"); data_ate = data_fim.strftime("%Y-%m-%d")
            resultados_bt = []; stats = {"0.5HT": {"total":0, "green":0}, "1.5FT": {"total":0, "green":0}, "2.5FT": {"total":0, "green":0}}
            ranking_ligas = defaultdict(lambda: {"total":0, "green":0}); ids_filtro = [k for k, v in LIGAS_MAP.items() if v in ligas_selecionadas]
            for league_id in ids_filtro:
                jogos = api_call("get_events", {"league_id": league_id, "from": data_de, "to": data_ate}); pais, nome_liga = get_league_info(league_id)
                if not isinstance(jogos, list): continue
                for jogo in [j for j in jogos if j.get('match_status') == 'Finished'][:20]:
                    try:
                        casa_id = jogo.get('match_hometeam_id'); fora_id = jogo.get('match_awayteam_id')
                        prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, league_id)
                        if prob_final >= limite_bt:
                            gols_ht = safe_int(jogo.get('match_hometeam_score_ht')) + safe_int(jogo.get('match_awayteam_score_ht'))
                            gols_ft = safe_int(jogo.get('match_hometeam_score')) + safe_int(jogo.get('match_awayteam_score'))
                            green_05 = gols_ht >= 1; green_15 = gols_ft >= 2; green_25 = gols_ft >= 3
                            if p_0_5 >= limite_bt: stats["0.5HT"]["total"] += 1; stats["0.5HT"]["green"] += 1 if green_05 else 0
                            if p_1_5 >= limite_bt: stats["1.5FT"]["total"] += 1; stats["1.5FT"]["green"] += 1 if green_15 else 0; ranking_ligas[nome_liga]["total"] += 1; ranking_ligas[nome_liga]["green"] += 1 if green_15 else 0
                            if p_2_5 >= limite_bt: stats["2.5FT"]["total"] += 1; stats["2.5FT"]["green"] += 1 if green_25 else 0
                            resultados_bt.append({"Data": jogo.get('match_date'), "Pais": pais, "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}", "Liga": nome_liga, "Rodada": jogo.get('league_round') if jogo.get('league_round') else "N/A", "Prob 1.5": p_1_5, "Prob 2.5": p_2_5, "FT": gols_ft, "1.5FT": "GREEN" if green_15 else "RED"})
                    except: continue
            if resultados_bt:
                df_bt = pd.DataFrame(resultados_bt); st.session_state.df_bt_global = df_bt; st.session_state.stats_global = stats; st.session_state.ranking_global = ranking_ligas
                taxa_15 = (stats['1.5FT']['green'] / stats['1.5FT']['total'] * 100) if stats['1.5FT']['total'] > 0 else 0
                total_apostado = stats['1.5FT']['total'] * stake; lucro_green = stats['1.5FT']['green'] * stake * (odd_real - 1)
                lucro_red = (stats['1.5FT']['total'] - stats['1.5FT']['green']) * stake; lucro = lucro_green - lucro_red; roi = (lucro / total_apostado) * 100 if total_apostado > 0 else 0
                col1, col2, col3 = st.columns(3); col1.metric("Taxa 1.5FT", f"{taxa_15:.1f}%", f"{stats['1.5FT']['green']}/{stats['1.5FT']['total']}")
                col2.metric("ROI 1.5FT", f"{roi:.1f}%", f"R${lucro:.2f}"); col3.metric("Lucro", f"R${lucro:.2f}")
                df_ranking = pd.DataFrame([{"Liga": liga, "Jogos": dados["total"], "GREEN": dados["green"], "Taxa": (dados["green"]/dados["total"]*100 if dados["total"]>0 else 0)} for liga, dados in ranking_ligas.items()]).sort_values("Taxa", ascending=False)
                st.dataframe(df_ranking.style.format({"Taxa": "{:.1f}%"}), use_container_width=True)
                def color_result(val): return 'background-color: #d4edda; color: #155724; font-weight: bold' if val == 'GREEN' else 'background-color: #f8d7da; color: #721c24; font-weight: bold' if val == 'RED' else ''
                st.dataframe(df_bt.style.map(color_result, subset=['1.5FT']), use_container_width=True)
            else: st.error("Nenhum jogo encontrado")

with tab3:
    st.header("EXPORTAR RELATORIO PDF")
    if st.session_state.df_bt_global is not None:
        st.success("Dados do ultimo backtest carregados")
        if st.button("GERAR PDF"):
            with st.spinner("Gerando PDF..."):
                periodo = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
                pdf_bytes = gerar_pdf(st.session_state.df_bt_global, st.session_state.stats_global, st.session_state.ranking_global, periodo, ligas_selecionadas)
                st.download_button(label="BAIXAR RELATORIO PDF", data=pdf_bytes, file_name=f"Relatorio_V26.6.4_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf")
    else: st.warning("Primeiro rode o BACKTEST na aba 2 para gerar o PDF")
