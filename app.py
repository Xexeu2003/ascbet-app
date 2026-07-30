import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")
st.title("⚽ Relatório Automático ASCbet 70%+")
st.caption("Horário: Manaus -4 | Análise: Últimos 10 Casa x Últimos 10 Fora")

API_KEY = st.secrets["API_KEY"]
SEASON = 2025

CAMPEONATOS_FAVORITOS = {
    39: "Inglaterra - Premier League", 106: "Noruega - Eliteserien", 
    71: "Brasil - Serie A", 256: "USA - MLS"
}

@st.cache_data(ttl=300)
def buscar_jogos_por_data():
    hoje = date.today()
    datas = [(hoje + timedelta(days=i)).isoformat() for i in range(0, 4)]
    todos_jogos = []
    headers = {"x-apisports-key": API_KEY}
    for d in datas:
        url = f"https://v3.football.api-sports.io/fixtures?date={d}"
        response = requests.get(url, headers=headers, timeout=15)
        todos_jogos.extend(response.json().get("response", []))
    return todos_jogos

@st.cache_data(ttl=1800)
def calcular_estatisticas(time_id, venue, last_n):
    # venue = "home" ou "away"
    headers = {"x-apisports-key": API_KEY}
    url = f"https://v3.football.api-sports.io/fixtures?team={time_id}&season={SEASON}&last={last_n}"
    response = requests.get(url, headers=headers, timeout=15)
    jogos = response.json().get("response", [])
    
    # Filtra só Casa ou só Fora
    jogos_filtrados = [j for j in jogos if j["teams"]["home"]["id"] == time_id and venue == "home"] if venue == "home" else [j for j in jogos if j["teams"]["away"]["id"] == time_id and venue == "away"]
    
    total = len(jogos_filtrados)
    if total == 0: return {}

    over_05_ht = sum(1 for j in jogos_filtrados if (j["goals"]["home"] or 0) + (j["goals"]["away"] or 0) > 0 and j["fixture"]["status"]["short"]!= "NS") / total * 100
    over_15 = sum(1 for j in jogos_filtrados if (j["goals"]["home"] or 0) + (j["goals"]["away"] or 0) >= 2) / total * 100
    over_25 = sum(1 for j in jogos_filtrados if (j["goals"]["home"] or 0) + (j["goals"]["away"] or 0) >= 3) / total * 100
    over_35 = sum(1 for j in jogos_filtrados if (j["goals"]["home"] or 0) + (j["goals"]["away"] or 0) >= 4) / total * 100
    btts = sum(1 for j in jogos_filtrados if (j["goals"]["home"] or 0) > 0 and (j["goals"]["away"] or 0) > 0) / total * 100
    
    return {
        "Over 0.5 HT": round(over_05_ht),
        "Over 1.5": round(over_15),
        "Over 2.5": round(over_25),
        "Over 3.5": round(over_35),
        "BTTS": round(btts)
    }

def gerar_pdf(dados):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph("Relatório ASCbet 70%+", styles['Title']))
    elements.append(Spacer(1, 12))
    
    for jogo in dados:
        elements.append(Paragraph(f"{jogo['jogo']} - {jogo['data']}", styles['Heading2']))
        tabela_dados = [["Mercado", "Probabilidade"]]
        for mercado, valor in jogo['probs'].items():
            tabela_dados.append([mercado, f"{valor}%"])
        
        t = Table(tabela_dados)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def converter_horario(utc_str):
    utc_time = datetime.fromisoformat(utc_str.replace("Z", ""))
    return (utc_time - timedelta(hours=4)).strftime("%d/%m %H:%M")

tab1, tab2 = st.tabs(["📌 Meus Campeonatos", "🔍 Buscar Campeonato"])
league_id_final = None

with tab1:
    campeonato_selecionado = st.selectbox("Escolha da Lista:", options=sorted(list(CAMPEONATOS_FAVORITOS.values())), key="select1")
    league_id_final = [k for k, v in CAMPEONATOS_FAVORITOS.items() if v == campeonato_selecionado][0]

if st.button("Gerar Relatório 70%+", type="primary"):
    with st.spinner("Analisando últimos 10 jogos de cada time... Isso demora 30s"):
        todos_jogos = buscar_jogos_por_data()
        jogos = [j for j in todos_jogos if j["league"]["id"] == league_id_final]
        
        relatorio_final = []
        for jogo in jogos:
            casa_id = jogo["teams"]["home"]["id"]
            fora_id = jogo["teams"]["away"]["id"]
            jogo_nome = f"{jogo['teams']['home']['name']} x {jogo['teams']['away']['name']}"
            
            stats_casa = calcular_estatisticas(casa_id, "home", 10)
            stats_fora = calcular_estatisticas(fora_id, "away", 10)
            
            # CALCULA A MÉDIA ENTRE CASA E FORA
            probs_finais = {}
            for mercado in stats_casa.keys():
                media = (stats_casa.get(mercado, 0) + stats_fora.get(mercado, 0)) / 2
                if media >= 70:
                    probs_finais[mercado] = round(media)
            
            if probs_finais:
                relatorio_final.append({
                    "jogo": jogo_nome,
                    "data": converter_horario(jogo["fixture"]["date"]),
                    "probs": probs_finais
                })
        
        if relatorio_final:
            st.success(f"{len(relatorio_final)} jogos com probabilidade 70%+ encontrados!")
            
            for item in relatorio_final:
                st.divider()
                st.subheader(f"📊 {item['jogo']} - {item['data']}")
                st.write("### Probabilidades 70%+")
                for mercado, valor in item['probs'].items():
                    st.success(f"**{mercado}: {valor}%**")
            
            # BOTÃO PDF
            pdf_file = gerar_pdf(relatorio_final)
            st.download_button(
                label="📄 Baixar Relatório em PDF",
                data=pdf_file,
                file_name=f"Relatorio_ASCbet_{date.today()}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Nenhum jogo com probabilidade acima de 70% encontrado.")

st.caption("Observação: OVER 0.5 HT = % de jogos que saiu pelo menos 1 gol no 1º tempo")
