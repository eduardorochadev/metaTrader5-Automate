import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Meu Robô DayTrade", layout="wide")
st.title("📈 Monitor de Ativos")
placeholder = st.empty()

# Tenta conectar
if not mt5.initialize():
    st.error("❌ ERRO: O MetaTrader 5 não está aberto ou não foi inicializado!")
else:
    st.success("✅ Conectado ao MetaTrader 5 com sucesso!")

    # Tenta pegar os dados uma única vez primeiro
    simbolo = "EURUSD"
    rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, 100)

    if rates is None or len(rates) == 0:
        st.warning(f"⚠️ O ativo {simbolo} não foi encontrado. Verifique se ele está na 'Observação do Mercado' do MT5.")
    else:
       # Transformar dados em DataFrame (Tabela)
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # --- ENGENHARIA DE PROBABILIDADES ---
        # Calcula a média dos últimos 20 candles
        df['media_20'] = df['close'].rolling(window=20).mean()
        
        preco_atual = df['close'].iloc[-1]
        media_atual = df['media_20'].iloc[-1]
        # ------------------------------------

        with placeholder.container():
            col1, col2 = st.columns(2)
            col1.metric("Preço Atual", f"{preco_atual:.5f}")
            col2.metric("Média (20 min)", f"{media_atual:.5f}", delta=f"{preco_atual - media_atual:.5f}")

            fig = go.Figure()
            # Desenha as velas
            fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preço"))
            
            # DESENHA A LINHA DA MÉDIA (A nossa referência estatística)
            fig.add_trace(go.Scatter(x=df['time'], y=df['media_20'], line=dict(color='yellow', width=2), name="Média 20"))
            
            fig.update_layout(template="plotly_dark", height=600)
            st.plotly_chart(fig, use_container_width=True)
# Botão para atualizar manualmente
if st.button('Atualizar Dados'):
    st.rerun()