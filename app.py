import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from scipy.stats import poisson
from collections import defaultdict
from fpdf import FPDF
import io

st.set_page_config(page_title="Analisador V26.6.14", layout="wide")
st.title("Analisador V26.6.14 - asc.bet PRO FINAL")
st.caption("Horario Manaus UTC-4 | 40 LIGAS | TOP 20 | BACKTEST | PDF")

# CORRECAO 1: INICIAR SESSION_STATE NO TOPO
if 'df_top_global' not in st.session_state: 
    st.session_state.df_top_global = None
    st.session_state.ligas_global = []
    st.session_state.filtro_global = 75
if 'df_bt_global' not in st.session_state: 
    st.session_state.df_bt_global = None
    st.session_state.stats_global = None

API_KEY = "37ebce0fe025b1c24efd20ea8d37e461704b594816bb0d77ee6691a62bfd8205"
API_URL = "https://apiv2.apifootball.com/"

def safe_int(valor):
    try: return int(valor) if valor is not None and valor!= '' else 0
    except: return 0

@st.cache_data(ttl=1800)
def api_call(action, params_extra):
    params = {"action": action, "APIkey": API_KEY}
    params.update(params_extra)
    try:
        r = requests.get(API_URL, params=params, timeout=60)
        data = r.json() if r.status_code == 200 else []
        return data if isinstance(data, list) else []
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
def get_h2h(team1, team2):
    h2h = api_call("get_H2H", {"firstTeamId": team1, "secondTeamId": team2})
    if not isinstance(h2h, list) or len(h2h)==0: return "N/A"
    ultimos_5 = h2h[:5]
    over_15 = sum(1 for j in ultimos_5 if safe_int(j.get('match_hometeam_score')) + safe_int(j.get('match_awayteam_score')) >= 2)
    return f"{over_15}/5"

@st.cache_data(ttl=3600)
def calcular_stats_5jogos(time_id, tipo):
    jogos = api_call("get_events", {"team_id": time_id, "from": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"), "to": datetime.now().strftime("%Y-%m-%d")})
    if not isinstance(jogos, list) or len(jogos)==0: return {"gols_m":1.4, "gols_s":1.4}
    jogos_finalizados = [j for j in jogos if j.get('match_status') == 'Finished']
    ultimos_5 = jogos_finalizados[:5]
    if len(ultimos_5)==0: return {"gols_m":1.4, "gols_s":1.4}
    gols_m = gols_s = jogos_contados = 0
    for j in ultimos_5:
        is_home = str(j.get('match_hometeam_id')) == str(time_id)
        if (tipo == "home" and is_home) or (tipo == "away" and not is_home):
            gols_m += safe_int(j.get('match_hometeam_score')) if is_home else safe_int(j.get('match_awayteam_score'))
            gols_s += safe_int(j.get('match_awayteam_score')) if is_home else safe_int(j.get('match_hometeam_score'))
            jogos_contados += 1
    if jogos_contados == 0: return {"gols_m":1.4, "gols_s":1.4}
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
    lambda_casa = max(0.3, atq_casa * def_fora * divisor)
    lambda_fora = max(0.3, atq_fora * def_casa * divisor)
    p_0_5, p_1_5, p_2_5 = calcular_poisson(lambda_casa, lambda_fora)
    prob_final = (p_2_5 * 60) + (p_1_5 * 30) + (p_0_5 * 10)
    prob_final = min(round(prob_final), 99)
    return prob_final, round(p_0_5*100), round(p_1_5*100), round(p_2_5*100)

def gerar_pdf(df, stats, ranking, periodo, ligas, filtro):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'RELATORIO ANALISADOR V26.6.14', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")} | Manaus UTC-4', 0, 1, 'C')
    pdf.cell(0, 8, f'Periodo: {periodo} | Filtro Prob: >= {filtro}%', 0, 1, 'C')
    pdf.cell(0, 8, f'Ligas: {", ".join(ligas)}', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f'TOP 20 JOGOS - {len(df)} encontrados', 0, 1)
    pdf.set_font('Arial', '', 8)
    colunas = ["Data", "Liga", "Jogo", "Prob 1.5", "Prob 2.5"]
    for col in colunas:
        pdf.cell(38, 6, col[:12], 1)
    pdf.ln()
    for _, row in df.head(20).iterrows():
        pdf.cell(38, 6, str(row['Data'])[:12], 1)
        pdf.cell(38, 6, str(row['Liga'])[:12], 1)
        pdf.cell(38, 6, str(row['Jogo'])[:12], 1)
        pdf.cell(38, 6, f"{row['Prob 1.5']}%", 1)
        pdf.cell(38, 6, f"{row['Prob 2.5']}%", 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# CORRECAO 2: REMOVI EKSTRAKLASA DUPLICADA
LIGAS_NOMES = {
    "Eliteserien": {"pais": "Norway", "liga": "Eliteserien"},
    "Ekstraklasa": {"pais": "Poland", "liga": "Ekstraklasa"}, 
    "Primera B": {"pais": "Chile", "liga": "Primera B"},
    "LPF": {"pais": "Argentina", "liga": "Liga Profesional Argentina"},
    "Brasileirao A": {"pais": "Brazil", "liga": "Serie A"},
    "Brasileirao B": {"pais": "Brazil", "liga": "Serie B"},
    "K League 1": {"pais": "Korea Republic", "liga": "K League 1"},
    "J1 League": {"pais": "Japan", "liga": "J1 League"},
    "Premier League": {"pais": "England", "liga": "Premier League"},
    "Championship": {"pais": "England", "liga": "Championship"},
    "La Liga": {"pais": "Spain", "liga": "LaLiga"},
    "La Liga 2": {"pais": "Spain", "liga": "LaLiga 2"},
    "Bundesliga": {"pais": "Germany", "liga": "Bundesliga"},
    "Bundesliga 2": {"pais": "Germany", "liga": "2. Bundesliga"},
    "Serie A": {"pais": "Italy", "liga": "Serie A"},
    "Serie B": {"pais": "Italy", "liga": "Serie B"},
    "Ligue 1": {"pais": "France", "liga": "Ligue 1"},
    "Ligue 2": {"pais": "France", "liga": "Ligue 2"},
    "Eredivisie": {"pais": "Netherlands", "liga": "Eredivisie"},
    "Primeira Liga": {"pais": "Portugal", "liga": "Primeira Liga"},
    "MLS": {"pais": "USA", "liga": "MLS"},
    "Liga MX": {"pais": "Mexico", "liga": "Liga MX"},
    "Superliga": {"pais": "Denmark", "liga": "Superliga"},
    "Allsvenskan": {"pais": "Sweden", "liga": "Allsvenskan"},
    "Veikkausliiga": {"pais": "Finland", "liga": "Veikkausliiga"},
    "Super League": {"pais": "Switzerland", "liga": "Super League"},
    "Pro League": {"pais": "Belgium", "liga": "Pro League"},
    "Austrian Bundesliga": {"pais": "Austria", "liga": "Bundesliga"},
    "Super Lig": {"pais": "Turkey", "liga": "Super Lig"},
    "Premier League Russia": {"pais": "Russia", "liga": "Premier League"},
    "Ukrainian Premier League": {"pais": "Ukraine", "liga": "Premier League"},
    "HNL": {"pais": "Croatia", "liga": "HNL"},
    "Czech Liga": {"pais": "Czech Republic", "liga": "1. Liga"},
    "Liga I": {"pais": "Romania", "liga": "Liga I"},
    "Scottish Premiership": {"pais": "Scotland", "liga": "Premiership"},
    "J2 League": {"pais": "Japan", "liga": "J2 League"},
    "K League 2": {"pais": "Korea Republic", "liga": "K League 2"},
    "A-League": {"pais": "Australia", "liga": "A-League"},
    "Liga Portugal 2": {"pais": "Portugal", "liga": "Liga Portugal 2"},
    "Division Profesional": {"pais": "Paraguay", "liga": "Division Profesional"}
}

tab1, tab2, tab3 = st.tabs(["ANALISADOR TOP 20", "BACKTEST PRO", "EXPORTAR PDF"])

with tab1:
    st.header("ANALISADOR TOP 20 - V26.6.14")
    
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        ligas_ao_vivo = st.multiselect(
            "Selecionar Ligas",
            list(LIGAS_NOMES.keys()),
            default=["Eliteserien", "Ekstraklasa", "Primera B", "LPF", "Brasileirao A", "K League 1"]
        )
    with col2:
        filtro_prob_vivo = st.slider("Filtro Prob 1.5 Minima", 60, 95, 75)
    with col3:
        dias_busca = st.selectbox("Buscar Jogos", ["Hoje + 2 Dias", "Hoje + 3 Dias", "Hoje + 5 Dias"], index=0)

    if st.button("GERAR TOP 20"):
        with st.spinner("Buscando jogos..."):
            dias_map = {"Hoje + 2 Dias": 2, "Hoje + 3 Dias": 3, "Hoje + 5 Dias": 5}
            data_inicio = datetime.now()
            data_fim = data_inicio + timedelta(days=dias_map[dias_busca])

            jogos_analisados = []
            jogos_totais = []
            
            todos_jogos = api_call("get_events", {"from": data_inicio.strftime("%Y-%m-%d"), "to": data_fim.strftime("%Y-%m-%d")})
            st.info(f"API Retornou: {len(todos_jogos)} jogos totais no periodo")

            for jogo in todos_jogos:
                pais_jogo = jogo.get('country_name')
                liga_jogo = jogo.get('league_name')
                
                for nome_selecionado, dados in LIGAS_NOMES.items():
                    if nome_selecionado in ligas_ao_vivo:
                        if dados["pais"] == pais_jogo and dados["liga"] in liga_jogo:
                            try:
                                casa_id = jogo.get('match_hometeam_id')
                                fora_id = jogo.get('match_awayteam_id')
                                league_id = jogo.get('league_id')
                                prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, league_id)

                                rodada = jogo.get('league_round') if jogo.get('league_round') else "N/A"
                                standings_cache = get_standings(league_id)
                                pos_casa = standings_cache.get(str(casa_id), '-')
                                pos_fora = standings_cache.get(str(fora_id), '-')
                                h2h = get_h2h(casa_id, fora_id)
                                stats_casa = calcular_stats_5jogos(casa_id, "home")
                                stats_fora = calcular_stats_5jogos(fora_id, "away")
                                gc_u8 = round((stats_casa['gols_s'] + stats_fora['gols_s'])/2, 2)
                                gf_u8 = round((stats_casa['gols_m'] + stats_fora['gols_m'])/2, 2)
                                pais_sigla = pais_jogo[:2].upper()

                                jogo_dict = {
                                    "Data": f"{jogo.get('match_date')} {jogo.get('match_time')}",
                                    "Liga": f"[{pais_sigla}] {liga_jogo}",
                                    "Rod": rodada,
                                    "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}",
                                    "Pos": f"{pos_casa} vs {pos_fora}",
                                    "H2H": h2h,
                                    "GC U8": gc_u8,
                                    "GF U8": gf_u8,
                                    "Prob 0.5": p_0_5,
                                    "Prob 1.5": p_1_5,
                                    "Prob 2.5": p_2_5,
                                    "Prob %": prob_final
                                }
                                
                                jogos_totais.append(jogo_dict)
                                
                                if p_1_5 >= filtro_prob_vivo:
                                    jogos_analisados.append(jogo_dict)
                                    
                            except: continue
            
            # SALVA NO SESSION STATE
            st.session_state.df_top_global = pd.DataFrame(jogos_totais) if jogos_totais else None
            st.session_state.ligas_global = ligas_ao_vivo
            st.session_state.filtro_global = filtro_prob_vivo

            if jogos_totais:
                df_todos = pd.DataFrame(jogos_totais).sort_values("Prob 1.5", ascending=False)
                st.subheader(f"TODOS OS {len(df_todos)} JOGOS ENCONTRADOS")
                def color_prob(val):
                    if val >= 90: return 'background-color: #28a745; color: white; font-weight: bold'
                    elif val >= 80: return 'background-color: #ffc107; color: black; font-weight: bold'
                    else: return ''
                st.dataframe(df_todos.style.map(color_prob, subset=['Prob 0.5', 'Prob 1.5', 'Prob 2.5', 'Prob %']), use_container_width=True)

            if jogos_analisados:
                df_top = pd.DataFrame(jogos_analisados).sort_values("Prob 1.5", ascending=False).head(20)
                st.success(f"TOP 20 FILTRADO - {len(df_top)} jogos com Prob 1.5 >= {filtro_prob_vivo}%")
                st.dataframe(df_top.style.map(color_prob, subset=['Prob 0.5', 'Prob 1.5', 'Prob 2.5', 'Prob %']), use_container_width=True)

with tab2:
    st.header("BACKTEST PRO - V26.6.14")
    col1, col2, col3, col4 = st.columns(4)
    with col1: data_inicio_bt = st.date_input("Data Inicio", datetime(2025,8,1).date())
    with col2: data_fim_bt = st.date_input("Data Fim", datetime(2025,9,30).date())
    with col3: stake = st.number_input("Stake R$", 1, 1000, 10)
    with col4: odd_real = st.number_input("Odd", 1.10, 3.00, 1.90, 0.05)
    ligas_selecionadas = st.multiselect("Selecionar Ligas BT", list(LIGAS_NOMES.keys()), default=["K League 1"])
    limite_bt = st.slider("Prob Minima BT", 50, 90, 75)
    
    if st.button("RODAR BACKTEST"):
        with st.spinner("Rodando backtest..."):
            data_de = data_inicio_bt.strftime("%Y-%m-%d"); data_ate = data_fim_bt.strftime("%Y-%m-%d")
            resultados_bt = []; stats = {"1.5FT": {"total":0, "green":0}}
            
            todos_jogos_bt = api_call("get_events", {"from": data_de, "to": data_ate}); 
            
            for jogo in [j for j in todos_jogos_bt if j.get('match_status') == 'Finished'][:200]:
                pais_jogo = jogo.get('country_name')
                liga_jogo = jogo.get('league_name')
                for nome_selecionado, dados in LIGAS_NOMES.items():
                    if nome_selecionado in ligas_selecionadas:
                        if dados["pais"] == pais_jogo and dados["liga"] in liga_jogo:
                            try:
                                casa_id = jogo.get('match_hometeam_id'); fora_id = jogo.get('match_awayteam_id')
                                prob_final, p_0_5, p_1_5, p_2_5 = calcular_probabilidade_final(casa_id, fora_id, jogo.get('league_id'))
                                if prob_final >= limite_bt:
                                    gols_ft = safe_int(jogo.get('match_hometeam_score')) + safe_int(jogo.get('match_awayteam_score'))
                                    green_15 = gols_ft >= 2
                                    stats["1.5FT"]["total"] += 1; stats["1.5FT"]["green"] += 1 if green_15 else 0
                                    resultados_bt.append({"Data": jogo.get('match_date'), "Jogo": f"{jogo.get('match_hometeam_name')} vs {jogo.get('match_awayteam_name')}", "Liga": jogo.get('league_name'), "Prob 1.5": p_1_5, "FT": gols_ft, "1.5FT": "GREEN" if green_15 else "RED"})
                            except: continue
            
            if resultados_bt:
                df_bt = pd.DataFrame(resultados_bt); st.session_state.df_bt_global = df_bt; st.session_state.stats_global = stats
                taxa_15 = (stats['1.5FT']['green'] / stats['1.5FT']['total'] * 100) if stats['1.5FT']['total'] > 0 else 0
                st.metric("Taxa 1.5FT", f"{taxa_15:.1f}%", f"{stats['1.5FT']['green']}/{stats['1.5FT']['total']}")
                st.dataframe(df_bt, use_container_width=True)
            else: st.error("Nenhum jogo encontrado no backtest")

with tab3:
    st.header("EXPORTAR RELATORIO PDF")
    if st.session_state.df_top_global is not None:
        st.success("Dados do TOP 20 carregados")
        periodo = f"{datetime.now().strftime('%d/%m/%Y')}"
        if st.button("GERAR PDF TOP 20"):
            with st.spinner("Gerando PDF..."):
                pdf_bytes = gerar_pdf(st.session_state.df_top_global, {"1.5FT":{"total":0,"green":0}}, {}, periodo, st.session_state.ligas_global, st.session_state.filtro_global)
                st.download_button(label="BAIXAR RELATORIO PDF", data=pdf_bytes, file_name=f"Relatorio_V26.6.14_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf")
    else: st.warning("Primeiro gere o TOP 20 na aba 1 para baixar o PDF")
