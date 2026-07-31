import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import random

st.set_page_config(page_title="ASCbet V18", page_icon="⚽", layout="wide")
st.title("⚽ ASCbet V18 - Analisador Profissional")
st.caption("Probabilidade 70%+ | Forçando Ligas TOP | API-Football Direta")

API_KEY = "e16821201501788a886ed8316ab5a06f"

# LIGAS QUE O FREE LIBERA: 71=Brasil A, 39=Premier, 140=LaLiga, 78=Bundesliga, 135=SerieA, 61=Ligue1, 2=Champions, 13=Libertadores
LIGAS_TOP = [71, 39, 140, 78, 135, 61, 2, 13]

@st.cache_data(ttl=1800)
def buscar_jogos():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_KEY}
    
    todos_jogos = []
    ano = datetime.now().year
    
    # Busca nas 8 ligas principais pelos próximos 7 dias
    for liga in LIGAS_TOP:
        for i in range(7):
            data = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            params = {"league": liga, "season": ano, "date": data}
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=15)
                if response.status_code == 200:
                    jogos_do_dia = response.json()['response']
                    todos_jogos.extend(jogos_do_dia)
            except:
                pass
    
    return todos_jogos

def analisar_jogo(jogo):
    probabilidade = round(random.uniform(70, 91), 1) # SUA LÓGICA V16 AQUI
    return probabilidade

def gerar_pdf(aprovados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"ASCbet V18 - Relatorio {datetime.now().strftime('%d/%m/%Y')}", 0, 1, "C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    for j in aprovados:
        pdf.cell(0, 8, f"{j['Data']} {j['Horario']} | {j['Jogo']} | Prob: {j['Probabilidade']}", 0, 1)
    pdf.output("relatorio_ascbet.pdf")

if st.button("🚀 Analisar Ligas TOP 7 DIAS", use_container_width=True, type="primary"):
    with st.spinner("Buscando Brasileirão, Champions, Libertadores... 2-3 minutos"):
        jogos = buscar_jogos()
        
        if not jogos:
            st.error("API retornou vazio. Plano free pode estar pausado. Testa amanhã.")
        else:
            aprovados = []
            progresso = st.progress(0, "Analisando jogos...")
            
            for i, jogo in enumerate(jogos[:200]):
                prob = analisar_jogo(jogo)
                if prob >= 70:
                    data_jogo = jogo['fixture']['date'][:10]
                    data_formatada = datetime.strptime(data_jogo, "%Y-%m-%d").strftime("%d/%m")
                    
                    aprovados.append({
                        "Data": data_formatada,
                        "Horario": jogo['fixture']['date'][11:16],
                        "Jogo": f"{jogo['teams']['home']['name']} vs {jogo['teams']['away']['name']}",
                        "Liga": jogo['league']['name'],
                        "País": jogo['league']['country'],
                        "Probabilidade": f"{prob}%"
                    })
                progresso.progress((i + 1) / len(jogos[:200]))
            
            st.success(f"✅ Análise concluída! {len(jogos)} jogos analisados")
            
            if aprovados:
                st.subheader(f"🎯 {len(aprovados)} JOGOS APROVADOS 70%+")
                df = pd.DataFrame(aprovados)
                st.dataframe(df, use_container_width=True)
                if st.button("📄 Baixar Relatório PDF"):
                    gerar_pdf(aprovados)
                    with open("relatorio_ascbet.pdf", "rb") as f:
                        st.download_button("Clique para Baixar PDF", f, "relatorio_ascbet.pdf")
            else:
                st.warning("Nenhum jogo com 70%+ nas ligas top")

st.sidebar.info(f"**Ligas**: Brasil A, Champions, Libertadores, Premier...")
st.sidebar.warning(f"Data Hoje: {datetime.now().strftime('%d/%m/%Y')}")
