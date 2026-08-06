import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
import os

VERSAO = "V26.7.5"
MARCA_DAGUA = "asc.bet"

# ============================================
# 1. COLE AQUI OS DADOS DO ANALISADOR
# Formato: Lista de dicts. Cada dict = 1 jogo
# ============================================
DADOS_EXEMPLO = [
    {"Liga": "ELITESERIEN", "Data": "05/08/2026", "Casa": "Bodo/Glimt", "Fora": "Estrela Vermelha", "Prob 0.5FT": "92%", "Prob 1.5FT": "75%", "Prob 2.5FT": "45%"},
    {"Liga": "LIGA PORTUGAL", "Data": "05/08/2026", "Casa": "FC Porto", "Fora": "Arouca", "Prob 0.5FT": "88%", "Prob 1.5FT": "69%", "Prob 2.5FT": "38%"},
    {"Liga": "LIGA PORTUGAL", "Data": "05/08/2026", "Casa": "Santa Clara", "Fora": "Nacional", "Prob 0.5FT": "85%", "Prob 1.5FT": "64%", "Prob 2.5FT": "32%"},
    {"Liga": "BRASILEIRAO SERIE A", "Data": "05/08/2026", "Casa": "Palmeiras", "Fora": "Flamengo", "Prob 0.5FT": "95%", "Prob 1.5FT": "82%", "Prob 2.5FT": "55%"}, # VERDE
    {"Liga": "BRASILEIRAO SERIE A", "Data": "05/08/2026", "Casa": "Sao Paulo", "Fora": "Corinthians", "Prob 0.5FT": "93%", "Prob 1.5FT": "78%", "Prob 2.5FT": "49%"}, # AMARELO
]
# ============================================

def get_cor_prob(prob_str):
    """Regra de cor: >=80 Verde, 76-79 Amarelo, <=75 Preto"""
    try:
        valor = int(str(prob_str).replace('%', ''))
    except:
        return colors.black, colors.white

    if valor >= 80:
        return colors.HexColor("#0F5132"), colors.HexColor("#D1E7DD") # Verde
    elif valor > 75:
        return colors.HexColor("#664D03"), colors.HexColor("#FFF3CD") # Amarelo
    else:
        return colors.black, colors.white

def adicionar_marca_dagua(canvas, doc):
    """Marca d'agua centralizada em todas as paginas"""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 100)
    canvas.setFillColor(colors.HexColor("#E5E5E5"))
    canvas.setFillAlpha(0.05)
    canvas.drawCentredString(landscape(A4)[0] / 2.0, landscape(A4)[1] / 2.0, MARCA_DAGUA)
    canvas.restoreState()

def gerar_pdf_analisador(df, nome_arquivo):
    """Gera o PDF do Analisador separado por Liga"""
    doc = SimpleDocTemplate(
        nome_arquivo,
        pagesize=landscape(A4), # Paisagem fica melhor pra tabela
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=20, alignment=1, fontName='Helvetica-Bold', textColor=colors.HexColor("#1A365D")))
    styles.add(ParagraphStyle(name='SubTitulo', fontSize=10, alignment=1, spaceAfter=15, textColor=colors.grey))
    styles.add(ParagraphStyle(name='LigaTitulo', fontSize=14, fontName='Helvetica-Bold', spaceBefore=15, spaceAfter=8, textColor=colors.HexColor("#2C5282")))

    elementos = []
    elementos.append(Paragraph(f"Relatorio Analisador asc.bet {VERSAO} - TOP 20", styles['Titulo']))
    elementos.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['SubTitulo']))

    # Agrupa por Liga
    for liga, grupo in df.groupby('Liga'):
        elementos.append(Paragraph(f"LIGA: {liga}", styles['LigaTitulo']))

        # Colunas da tabela
        colunas = ["Data", "Casa", "Fora", "Prob 0.5FT", "Prob 1.5FT", "Prob 2.5FT"]
        dados_tabela = [colunas]
        dados_tabela.extend(grupo[colunas].values.tolist())

        # Largura das colunas
        larguras = [2.5*cm, 5.5*cm, 5.5*cm, 2.8*cm, 2.8*cm, 2.8*cm]
        tabela = Table(dados_tabela, colWidths=larguras, repeatRows=1)

        # Estilo base
        estilo = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")])
        ])

        # Aplicar cor em todas as colunas de Prob
        colunas_prob_idx = [3, 4, 5] # indices de Prob 0.5, 1.5, 2.5
        for i in range(1, len(dados_tabela)):
            for col_idx in colunas_prob_idx:
                cor_texto, cor_fundo = get_cor_prob(dados_tabela[i][col_idx])
                estilo.add('TEXTCOLOR', (col_idx, i), (col_idx, i), cor_texto)
                estilo.add('FONTNAME', (col_idx, i), (col_idx, i), 'Helvetica-Bold')
                if cor_fundo!= colors.white:
                    estilo.add('BACKGROUND', (col_idx, i), (col_idx, i), cor_fundo)

        tabela.setStyle(estilo)
        elementos.append(tabela)

    doc.build(elementos, onFirstPage=adicionar_marca_dagua, onLaterPages=adicionar_marca_dagua)
    print(f"✅ PDF Gerado: {nome_arquivo}")

def main():
    print(f"Iniciando Analisador asc.bet {VERSAO}...")

    # 1. Carregar dados
    df = pd.DataFrame(DADOS_EXEMPLO)
    if df.empty:
        print("Nenhum dado para gerar relatorio.")
        return

    # 2. Ordenar por Prob 1.5FT e pegar TOP 20
    df['Prob 1.5FT Num'] = df['Prob 1.5FT'].str.replace('%','').astype(int)
    df = df.sort_values(by='Prob 1.5FT Num', ascending=False).head(20)
    df = df.drop(columns=['Prob 1.5FT Num'])

    # 3. Gerar PDF
    nome_pdf = f"Relatorio_Analisador_{VERSAO}_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf"
    gerar_pdf_analisador(df, nome_pdf)

if __name__ == "__main__":
    main()
