import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Relatório ASCbet 70%+", layout="wide")

st.title("Relatório Automático ASCbet 70%+")
st.write("App conectado na API de Futebol")

# PEGA A CHAVE DOS SECRETS - JÁ CORRIGIDO
try:
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Chave API_KEY não encontrada nos Secrets. \n\n Vá em Settings > Secrets e adicione: \n API_KEY = \"sua_chave\"")
    st.stop()

# FUNÇÃO PARA BUSCAR CAMPEONATOS
@st.cache_data(ttl=3600)
def buscar_campeonatos():
    url = "https://api.api-futebol.com.br/v1/campeonatos"
    headers = {"Authorization": f"Bearer {API_KEY}"}  # Padrão da API-Futebol
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            st.error(f"Erro 401: Chave inválida. Verifique se a chave {API_KEY[:5]}... está ativa no site da API-Futebol")
        else:
            st.error(f"Erro HTTP {response.status_code}: {e}")
        return None
    except Exception as e:
        st.error(f"Erro ao conectar na API: {e}")
        return None

# BOTÃO
if st.button("Buscar Campeonatos"):
    with st.spinner("Buscando dados da API..."):
        dados = buscar_campeonatos()
    
    if dados:
        st.success(f"{len(dados)} campeonatos encontrados!")
        
        # MOSTRA EM TABELA
        df = pd.DataFrame(dados)
        colunas = ['campeonato_id', 'nome', 'nome_popular', 'slug']
        df = df[[c for c in colunas if c in df.columns]]
        st.dataframe(df, use_container_width=True)
        
        st.write("Última atualização:", datetime.now().strftime("%d/%m/%Y %H:%M"))


