import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.graph_objects as go
import time
import os
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Terminal Quant Pro", layout="wide")
LOG_FILE = "log_operacoes.txt"

# --- FUNÇÕES ---
def registrar_log(mensagem):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {mensagem}\n")

def enviar_ordem(simbolo, volume, tipo_ordem, sl_pts, tp_pts):
    tick = mt5.symbol_info_tick(simbolo)
    ponto = mt5.symbol_info(simbolo).point
    if tipo_ordem == "COMPRA":
        tipo, preco = mt5.ORDER_TYPE_BUY, tick.ask
        sl, tp = preco - (sl_pts * ponto), preco + (tp_pts * ponto)
    else:
        tipo, preco = mt5.ORDER_TYPE_SELL, tick.bid
        sl, tp = preco + (sl_pts * ponto), preco - (tp_pts * ponto)

    solicitacao = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": float(volume),
        "type": tipo,
        "price": preco,
        "sl": sl, "tp": tp,
        "magic": 123456,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    resultado = mt5.order_send(solicitacao)
    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        registrar_log(f"ORDEM ABERTA: {tipo_ordem} | Preço: {preco} | SL: {sl} | TP: {tp}")
    return resultado

# --- INICIALIZAÇÃO ---
if not mt5.initialize():
    st.error("Erro ao conectar no MT5")
else:
    # Sidebar Estática
    st.sidebar.header("⚙️ Configurações")
    simbolo = st.sidebar.text_input("Ativo", "EURUSD")
    meta_lucro = st.sidebar.number_input("Meta Diária ($)", value=10.0)
    lote = st.sidebar.number_input("Volume (Lote)", 0.01, 1.0, 0.01, 0.01)
    sl_input = st.sidebar.number_input("Stop Loss (Pts)", value=200)
    tp_input = st.sidebar.number_input("Take Profit (Pts)", value=400)
    autotrade = st.sidebar.toggle("🤖 Ativar Auto-Trading", value=False)
    
    if not os.path.exists(LOG_FILE):
        registrar_log("=== SISTEMA INICIADO ===")

    dashboard = st.empty()

    while True:
        # 1. CÁLCULO DE PERFORMANCE (24H)
        desde_24h = datetime.now() - timedelta(hours=24)
        historico = mt5.history_deals_get(desde_24h, datetime.now())
        lucro_24h, acertos, erros = 0.0, 0, 0
        if historico:
            df_hist = pd.DataFrame(list(historico), columns=historico[0]._asdict().keys())
            df_fechadas = df_hist[df_hist['profit'] != 0]
            lucro_24h = df_fechadas['profit'].sum()
            acertos = len(df_fechadas[df_fechadas['profit'] > 0])
            erros = len(df_fechadas[df_fechadas['profit'] < 0])

        # 2. DADOS DO MERCADO
        rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, 100)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['media_20'] = df['close'].rolling(window=20).mean()
            preco_atual = df['close'].iloc[-1]
            media_atual = df['media_20'].iloc[-1]
            posicoes = mt5.positions_get(symbol=simbolo)

            with dashboard.container():
                st.title("🚀 Terminal Quant Pro - Live")
                
                # LINHA 1: MÉTRICAS DE PREÇO
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Preço Atual", f"{preco_atual:.5f}")
                m2.metric("Média (20 min)", f"{media_atual:.5f}", delta=f"{preco_atual - media_atual:.5f}")
                m3.metric("Status Robô", "LIGADO 🤖" if autotrade else "MANUAL ⚪")
                m4.metric("Hora Local", datetime.now().strftime("%H:%M:%S"))

                # LINHA 2: PERFORMANCE 24H
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Lucro 24h", f"${lucro_24h:.2f}")
                p2.metric("Acertos ✅", acertos)
                p3.metric("Erros ❌", erros)
                win_rate = (acertos / (acertos + erros) * 100) if (acertos + erros) > 0 else 0
                p4.metric("Win Rate", f"{win_rate:.1f}%")

                # LÓGICA DE AUTOMAÇÃO
                meta_batida = lucro_24h >= meta_lucro
                if autotrade and not posicoes and not meta_batida:
                    if preco_atual > media_atual:
                        enviar_ordem(simbolo, lote, "COMPRA", sl_input, tp_input)
                    elif preco_atual < media_atual:
                        enviar_ordem(simbolo, lote, "VENDA", sl_input, tp_input)
                
                if meta_batida:
                    st.success("🎯 META DIÁRIA ATINGIDA! Operações pausadas.")

                # GRÁFICO
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preço"))
                fig.add_trace(go.Scatter(x=df['time'], y=df['media_20'], line=dict(color='yellow')))
                fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True, key=f"c_{time.time()}")

                # RODAPÉ: POSIÇÕES E LOGS
                col_pos, col_log = st.columns([1.5, 1])
                
                with col_pos:
                    st.subheader("💼 Operações Abertas")
                    if posicoes:
                        df_pos = pd.DataFrame(list(posicoes), columns=posicoes[0]._asdict().keys())
                        st.table(df_pos[['symbol', 'type', 'volume', 'price_open', 'profit']])
                    else:
                        st.info("Nenhuma ordem aberta.")

                with col_log:
                    st.subheader("📝 Diário de Bordo")
                    if os.path.exists(LOG_FILE):
                        with open(LOG_FILE, "r") as f:
                            linhas = f.readlines()
                            for linha in linhas[-5:]: # Últimas 5
                                st.caption(linha.strip())

        time.sleep(1)