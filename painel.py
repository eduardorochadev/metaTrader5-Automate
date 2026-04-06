import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Meu Robô DayTrade", layout="wide")
st.title("🚀 Terminal de Execução Algorítmica")

# --- FUNÇÕES DE EXECUÇÃO (O MOTOR) ---
def enviar_ordem(simbolo, volume, tipo_ordem, stop_loss_pontos=200, take_profit_pontos=400):
    """
    Envia uma ordem para o MT5 com Stop Loss e Take Profit automáticos.
    """
    tick = mt5.symbol_info_tick(simbolo)
    ponto = mt5.symbol_info(simbolo).point
    
    if tipo_ordem == "COMPRA":
        tipo = mt5.ORDER_TYPE_BUY
        preco = tick.ask
        sl = preco - (stop_loss_pontos * ponto)
        tp = preco + (take_profit_pontos * ponto)
    else:
        tipo = mt5.ORDER_TYPE_SELL
        preco = tick.bid
        sl = preco + (stop_loss_pontos * ponto)
        tp = preco - (take_profit_pontos * ponto)

    solicitacao = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": float(volume),
        "type": tipo,
        "price": preco,
        "sl": sl,
        "tp": tp,
        "magic": 123456,
        "comment": "Execução Python",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    resultado = mt5.order_send(solicitacao)
    return resultado

# --- INICIALIZAÇÃO ---
if not mt5.initialize():
    st.error("❌ Falha ao conectar ao MetaTrader 5. Verifique se o terminal está aberto.")
else:
    simbolo = "EURUSD"
    
    # Barra Lateral para Controles
    st.sidebar.header("⚙️ Configurações de Risco")
    lote = st.sidebar.number_input("Volume (Lote)", min_value=0.01, max_value=1.0, value=0.01, step=0.01)
    sl_input = st.sidebar.number_input("Stop Loss (Pontos)", value=200)
    tp_input = st.sidebar.number_input("Take Profit (Pontos)", value=400)

    # Captura de Dados
    rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, 100)

    if rates is None or len(rates) == 0:
        st.warning(f"⚠️ Ativo {simbolo} não encontrado na 'Observação do Mercado'.")
    else:
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Cálculos Estatísticos
        df['media_20'] = df['close'].rolling(window=20).mean()
        preco_atual = df['close'].iloc[-1]
        media_atual = df['media_20'].iloc[-1]

        # --- CÉREBRO DO ROBÔ (AUTOMAÇÃO) ---
        st.subheader("🤖 Estado do Robô")
        
        # Verifica se já existe alguma posição aberta para não abrir várias
        posicoes_abertas = mt5.positions_get(symbol=simbolo)
        
        if not posicoes_abertas:
            st.write("Buscando oportunidade...")
            
            # Lógica simples de cruzamento
            if preco_atual > media_atual:
                st.warning("🚨 SINAL DE COMPRA IDENTIFICADO!")
                # Descomente a linha abaixo para automatizar 100%
                # enviar_ordem(simbolo, lote, "COMPRA", sl_input, tp_input)
                
            elif preco_atual < media_atual:
                st.warning("🚨 SINAL DE VENDA IDENTIFICADO!")
                # Descomente a linha abaixo para automatizar 100%
                # enviar_ordem(simbolo, lote, "VENDA", sl_input, tp_input)
        else:
            st.success(f"✅ Robô posicionado em {simbolo}. Aguardando fechamento da ordem.")
        
        # PAINEL DE MÉTRICAS E BOTÕES
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        
        col1.metric("Preço Atual", f"{preco_atual:.5f}")
        col2.metric("Média (20 min)", f"{media_atual:.5f}", delta=f"{preco_atual - media_atual:.5f}")
        
        # Botões de Execução Direta
        if col3.button("🟢 COMPRAR", use_container_width=True):
            res = enviar_ordem(simbolo, lote, "COMPRA", sl_input, tp_input)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                st.toast("Compra Executada!", icon="🚀")
            else:
                st.error(f"Erro: {res.comment}")

        if col4.button("🔴 VENDER", use_container_width=True):
            res = enviar_ordem(simbolo, lote, "VENDA", sl_input, tp_input)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                st.toast("Venda Executada!", icon="📉")
            else:
                st.error(f"Erro: {res.comment}")

        # GRÁFICO ATUALIZADO
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], 
                                     low=df['low'], close=df['close'], name="Preço"))
        fig.add_trace(go.Scatter(x=df['time'], y=df['media_20'], 
                                 line=dict(color='yellow', width=2), name="Média 20"))
        
        fig.update_layout(template="plotly_dark", height=600, margin=dict(l=0, r=0, b=0, t=30))
        st.plotly_chart(fig, use_container_width=True)

# Rodapé de controle
if st.button('🔄 Atualizar Gráfico'):
    st.rerun()
    
# --- MONITOR DE POSIÇÕES ABERTAS ---
st.subheader("💼 Minhas Operações Abertas")
posicoes = mt5.positions_get(symbol=simbolo)

if posicoes:
    df_pos = pd.DataFrame(list(posicoes), columns=posicoes[0]._asdict().keys())
    # Simplificando a tabela para você ver o que importa
    df_selecionado = df_pos[['symbol', 'type', 'volume', 'price_open', 'sl', 'tp', 'profit']]
    st.table(df_selecionado)
else:
    st.info("Nenhuma operação aberta no momento.")