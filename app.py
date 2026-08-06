import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime

VERSAO = "V26.7.5"
MARCA_DAGUA = "asc.bet"

st.set_page_config(page_title=f"Analisador asc.bet {VERSAO}", layout="wide")
st.title(f"Relatorio Analisador asc.bet {VERSAO} - TOP 20")

# ============================================
# DADOS DA SUA PRINT - 05/08/2026
# ============================================
DADOS_EXEMPLO = [
    # BRASILEIRAO SERIE A
    {"Liga": "BRASILEIRAO SERIE A", "Data": "05/08/2026", "Casa": "Palmeiras", "Fora": "Flamengo", "Prob 0.5FT": "95%", "Prob 1.5FT": "82%", "Prob 2.5FT": "55%"},
    {"Liga": "BRASILEIRAO SERIE A", "Data": "05/08/2026", "Casa": "Sao Paulo", "Fora": "Corinthians", "Prob 0.5FT": "93%", "Prob 1.5FT": "78%", "Prob 2.5FT": "49%"},
    
    # ELITESERIEN
    {"Liga": "ELITESERIEN", "Data": "05/08/2026", "Casa": "Bodo/Glimt", "Fora": "Estrela Vermelha", "Prob 0.5FT": "92%", "Prob 1.5FT": "75%", "Prob 2.5FT": "45%"},
    
    # K-LEAGUE 1
    {"Liga": "K-LEAGUE 1", "Data": "05/08/2026", "Casa": "Ulsan HD", "Fora": "Jeonbuk", "Prob 0.5FT": "70%", "Prob 1.5FT": "45%", "Prob 2.5FT": "18%"},
    
    # LIGA PORTUGAL
    {"Liga": "LIGA PORTUGAL", "Data": "05/08/2026", "Casa": "FC Porto", "Fora": "Arouca", "Prob 0.5FT": "88%", "Prob 1.5FT": "69%", "Prob 2.5FT": "38%"},
    {"Liga": "LIGA PORTUGAL", "Data": "05/08/2026", "Casa": "Santa Clara", "Fora": "Nacional", "Prob 0.5FT": "85%", "Prob 1.5FT": "64%", "Prob 2.5FT": "32%"},
]
# ============================================

def get_cor_prob(prob_str):
    """Regra: >=80 Verde, 76-79 Amarelo, <=75 Preto"""
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
    """Marca d'agua centralizada"""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 100)
    canvas.setFillColor(colors.HexColor("#E5E5E5"))
    canvas.setFillAlpha(0.05)
    canvas.drawCentredString(landscape(A4)[0] / 2.0, landscape(A4)[1] / 2.0, MARCA_DAGUA)
    canvas.restoreState()

def gerar_pdf_buffer(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=20, alignment=1, fontName='Helvetica-Bold', textColor=colors.HexColor("#1A365D"), spaceAfter=4))
    styles.add(ParagraphStyle(name='SubTitulo', fontSize=10, alignment=1, spaceAfter=15, textColor=colors.grey))
    styles.add(ParagraphStyle(name='LigaTitulo', fontSize=14, fontName='Helvetica-Bold', spaceBefore=15, spaceAfter=8, textColor=colors.HexColor("#2C5282")))

    elementos = []
    elementos.append(Paragraph(f"Relatorio Analisador asc.bet {VERSAO} - TOP 20", styles['Titulo']))
    elementos.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['SubTitulo']))

    # Agrupa por Liga
    for liga, grupo in df.groupby('Liga'):
        elementos.append(Paragraph(f"LIGA: {liga}", styles['LigaTitulo']))

        colunas = ["Data", "Casa", "Fora", "Prob 0.5FT", "Prob 1.5FT", "Prob 2.5FT"]
        dados_tabela = [colunas]
        dados_tabela.extend(grupo[colunas].values.tolist())

        larguras = [2.5*cm, 5.5*cm, 5.5*cm, 2.8*cm, 2.8*cm, 2.8*cm]
        tabela = Table(dados_tabela, colWidths=larguras, repeatRows=1)

        estilo = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")])
        ])

        # Aplica cor nas 3 colunas de Prob
        colunas_prob_idx = [3, 4, 5]
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
    buffer.seek(0)
    return buffer


# ================= LÓGICA DO APP =================
df = pd.DataFrame(DADOS_EXEMPLO)

if not df.empty:
    # Ordena por Prob 1.5FT e pega TOP 20
    df['Prob 1.5FT Num'] = df['Prob 1.5FT'].str.replace('%','').astype(int)
    df = df.sort_values(by='Prob 1.5FT Num', ascending=False).head(20)
    df = df.drop(columns=['Prob 1.5FT Num'])
    
    st.subheader("Pré-visualização dos Dados")
    st.dataframe(df, use_container_width=True)
    
    st.subheader("Gerar PDF")
    pdf_buffer = gerar_pdf_buffer(df)
    
    st.download_button(
        label="📥 Baixar PDF do Relatorio",
        data=pdf_buffer,
        file_name=f"Relatorio_Analisador_{VERSAO}_{datetime.now().strftime('%d%m%Y')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
else:
    st.warning("Nenhum dado para gerar relatorio.")
