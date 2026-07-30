import streamlit as st
import requests

st.set_page_config(page_title="ASCbet 70%+", layout="wide")

st.title("Relatório Automático ASCbet 70%+")
st.write("App conectado na API de Futebol")

# Pega a chave dos Secrets que você configurou
API_KEY = st.secrets["API_KEY"]

url = "https://api.api-futebol.com.br/v1/campeonatos"
headers = {"Authorization": f"{API_KEY}"}

if st.button("Buscar Campeonatos"):
    with st.spinner("Buscando dados..."):
        response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        dados = response.json()
        st.success("Conectado com sucesso!")
        st.write(f"Total de campeonatos: {len(dados)}")
        st.dataframe(dados) # mostra em tabela
    else:
        st.error(f"Erro {response.status_code}: {response.text}")
