def gerar_pdf(df):
    pdf = FPDF(orientation='L') # Deitado A4
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Relatorio Analisador V23.9 - {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(3)
    
    # CABEÇALHO DA TABELA
    pdf.set_font("Arial", "B", 6) # Fonte menor pra caber tudo
    pdf.cell(22, 8, "Data", 1)
    pdf.cell(40, 8, "Liga", 1)
    pdf.cell(12, 8, "Rod", 1, 0, 'C')
    pdf.cell(75, 8, "Jogo", 1)
    pdf.cell(18, 8, "Pos", 1, 0, 'C')
    pdf.cell(15, 8, "H2H", 1, 0, 'C')
    pdf.cell(15, 8, "GC U8", 1, 0, 'C') # Gols Casa U8
    pdf.cell(15, 8, "GF U8", 1, 0, 'C') # Gols Fora U8
    pdf.cell(18, 8, "Prob 2.5", 1, 0, 'C')
    pdf.cell(15, 8, "Prob %", 1, 1, 'C') # 1 = quebra linha
    
    # LINHAS DA TABELA
    pdf.set_font("Arial", "", 6)
    for i, row in df.iterrows():
        data = row.get('Data', 'N/A')
        liga = row.get('Liga', 'N/A')[:22]
        rodada = str(row.get('Rodada', 'N/A'))
        jogo = row.get('Jogo', 'N/A')[:38]
        pos = str(row.get('Pos', 'N/A'))
        h2h = str(row.get('Media H2H 5J', 0))
        gols_casa = str(row.get('Gols Casa U8', 0))
        gols_fora = str(row.get('Gols Fora U8', 0))
        p25 = str(row.get('Prob 2.5 FT', '0%'))
        prob = str(row.get('Prob %', 0)) + "%"
        
        # Zebra
        if i % 2 == 0:
            pdf.set_fill_color(240, 240, 240)
            fill = True
        else:
            fill = False
            
        pdf.cell(22, 6, data.encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(40, 6, liga.encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(12, 6, rodada, 1, 0, 'C', fill)
        pdf.cell(75, 6, jogo.encode('latin-1', 'replace').decode('latin-1'), 1, 0, '', fill)
        pdf.cell(18, 6, pos, 1, 0, 'C', fill)
        pdf.cell(15, 6, h2h, 1, 0, 'C', fill)
        pdf.cell(15, 6, gols_casa, 1, 0, 'C', fill)
        pdf.cell(15, 6, gols_fora, 1, 0, 'C', fill)
        pdf.cell(18, 6, p25, 1, 0, 'C', fill)
        pdf.cell(15, 6, prob, 1, 1, 'C', fill) # 1 = quebra linha
    
    pdf_output = pdf.output()
    return bytes(pdf_output)
