import requests
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# SUA KEY
API_KEY = "n9LSMA3Cq2j28W8oMcliM9LpHbpfRCZkjIrpjgAnXCxLTME2FwCCkWfSlrHb"
BASE_URL = "https://api.sportmonks.com/v3/football"

def get_fixtures_today():
    """Pega jogos de hoje"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures/date/{today}"
    params = {
        "api_token": API_KEY,
        "include": "league,localTeam,visitorTeam,scores"
    }
    r = requests.get(url, params=params)
    return r.json().get("data", [])

def get_team_last_10(team_id):
    """Pega últimos 10 jogos do time"""
    url = f"{BASE_URL}/teams/{team_id}/fixtures"
    params = {
        "api_token": API_KEY,
        "include": "scores",
        "per_page": 10
    }
    r = requests.get(url, params=params)
    return r.json().get("data", [])

def check_over_05_ht(fixtures):
    """Analisa OVER 0.5 HT"""
    resultados = []

    for jogo in fixtures:
        home_id = jogo["localTeam"]["id"]
        away_id = jogo["visitorTeam"]["id"]
        home_name = jogo["localTeam"]["name"]
        away_name = jogo["visitorTeam"]["name"]

        # Pega últimos 10 de cada
        home_games = get_team_last_10(home_id)
        away_games = get_team_last_10(away_id)

        # Conta quantos tiveram gol no 1º tempo
        home_over_ht = 0
        for g in home_games:
            if g.get("scores") and len(g["scores"]) > 0:
                ht_score = g["scores"][0] # 1º tempo
                if ht_score.get("home") + ht_score.get("away") > 0:
                    home_over_ht += 1

        away_over_ht = 0
        for g in away_games:
            if g.get("scores") and len(g["scores"]) > 0:
                ht_score = g["scores"][0]
                if ht_score.get("home") + ht_score.get("away") > 0:
                    away_over_ht += 1

        # Calcula %
        home_pct = (home_over_ht / len(home_games)) * 100 if home_games else 0
        away_pct = (away_over_ht / len(away_games)) * 100 if away_games else 0

        # Média dos 2
        media = (home_pct + away_pct) / 2

        if media >= 70:
            resultados.append({
                "Jogo": f"{home_name} x {away_name}",
                "Casa 10j": f"{home_pct:.0f}%",
                "Fora 10j": f"{away_pct:.0f}%",
                "Média": f"{media:.0f}%",
                "Status": "APROVADO 70%+"
            })

    return resultados

def gerar_pdf(dados):
    """Gera PDF do relatório"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "RELATORIO ASCbet V16 - OVER 0.5 HT", 0, 1, "C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, "C")
    pdf.ln(5)

    for item in dados:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, item["Jogo"], 0, 1)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Casa 10j: {item['Casa 10j']} | Fora 10j: {item['Fora 10j']} | Media: {item['Média']}", 0, 1)
        pdf.cell(0, 6, f"Status: {item['Status']}", 0, 1)
        pdf.ln(2)

    pdf.output("Relatorio_ASCbet_V16.pdf")
    print("PDF gerado: Relatorio_ASCbet_V16.pdf")

# EXECUTAR
print("Buscando jogos de hoje...")
jogos = get_fixtures_today()
print(f"Analisando {len(jogos)} jogos...")

aprovados = check_over_05_ht(jogos)

if aprovados:
    print("\n=== JOGOS APROVADOS 70%+ ===")
    for j in aprovados:
        print(j)
    gerar_pdf(aprovados)
else:
    print("Nenhum jogo com 70%+ encontrado hoje")
