import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Meu Robô DayTrade", layout="wide")
st.title("📈 Monitor de Ativos")

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
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # Mostra o gráfico
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'],
            open=df['open'], high=df['high'],
            low=df['low'], close=df['close']
        )])
        fig.update_layout(template="plotly_dark", title=f"Gráfico de {simbolo}")
        st.plotly_chart(fig, use_container_width=True)

# Botão para atualizar manualmente
if st.button('Atualizar Dados'):
    st.rerun()