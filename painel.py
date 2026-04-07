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
CSS_COMPACTO_FILE = "styles_compacto.css"

# --- FUNÇÕES ---
def registrar_log(mensagem):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {mensagem}\n")


def enviar_ordem(simbolo, volume, tipo_ordem, sl_pts, tp_pts):
    info = mt5.symbol_info(simbolo)
    if info is None:
        registrar_log(f"FALHA AO ENVIAR ORDEM: ativo {simbolo} nao encontrado.")
        return None

    if not info.visible:
        mt5.symbol_select(simbolo, True)

    tick = mt5.symbol_info_tick(simbolo)
    if tick is None:
        registrar_log(f"FALHA AO ENVIAR ORDEM: sem tick para {simbolo}.")
        return None

    ponto = info.point
    if tipo_ordem == "COMPRA":
        tipo, preco = mt5.ORDER_TYPE_BUY, tick.ask
        sl, tp = preco - (sl_pts * ponto), preco + (tp_pts * ponto)
    else:
        tipo, preco = mt5.ORDER_TYPE_SELL, tick.bid
        sl, tp = preco + (sl_pts * ponto), preco - (tp_pts * ponto)

    filling_mode = getattr(info, "filling_mode", mt5.ORDER_FILLING_FOK)
    if filling_mode not in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN):
        filling_mode = mt5.ORDER_FILLING_FOK

    solicitacao = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": float(volume),
        "type": tipo,
        "price": preco,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123456,
        "comment": "Execucao Python",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }

    resultado = mt5.order_send(solicitacao)
    if resultado is None:
        registrar_log(f"ERRO mt5.order_send: {mt5.last_error()}")
        return None

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        registrar_log(f"ORDEM ABERTA: {tipo_ordem} | Preço: {preco} | SL: {sl} | TP: {tp}")
    else:
        registrar_log(f"ORDEM REJEITADA ({tipo_ordem}): retcode={resultado.retcode} | comentario={resultado.comment}")

    return resultado


def preparar_fechamentos(historico, simbolo):
    if not historico:
        return pd.DataFrame()

    df_hist = pd.DataFrame(list(historico), columns=historico[0]._asdict().keys())
    if "symbol" in df_hist.columns:
        df_hist = df_hist[df_hist["symbol"] == simbolo]

    if "entry" in df_hist.columns:
        df_fechadas = df_hist[df_hist["entry"] == mt5.DEAL_ENTRY_OUT].copy()
    else:
        df_fechadas = df_hist[df_hist["profit"] != 0].copy()

    if df_fechadas.empty:
        return df_fechadas

    if "time" in df_fechadas.columns:
        df_fechadas["time"] = pd.to_datetime(df_fechadas["time"], unit="s")

    return df_fechadas.sort_values("time", ascending=False)


def carregar_css(arquivo_css):
    if not os.path.exists(arquivo_css):
        return
    with open(arquivo_css, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# --- INICIALIZAÇÃO ---
if not mt5.initialize():
    st.error("Erro ao conectar no MT5")
    st.stop()
else:
    if not os.path.exists(LOG_FILE):
        registrar_log("=== SISTEMA INICIADO ===")

    if "ultimo_trade_ts" not in st.session_state:
        st.session_state.ultimo_trade_ts = 0.0

    # Sidebar
    st.sidebar.header("Configuracoes")
    simbolo = st.sidebar.text_input("Ativo", "EURUSD").strip().upper()
    modo_compacto = st.sidebar.toggle("Modo compacto", value=True)
    meta_lucro = st.sidebar.number_input("Meta Diária ($)", value=10.0)
    lote = st.sidebar.number_input("Volume (Lote)", 0.01, 1.0, 0.01, 0.01)
    sl_input = st.sidebar.number_input("Stop Loss (Pts)", value=200)
    tp_input = st.sidebar.number_input("Take Profit (Pts)", value=400)
    autotrade = st.sidebar.toggle("Ativar Auto-Trading", value=False)
    cooldown_seg = st.sidebar.number_input("Cooldown entre ordens (s)", min_value=5, max_value=300, value=30, step=5)
    refresh_seg = st.sidebar.slider("Atualizar a cada (s)", min_value=1, max_value=30, value=3)
    auto_refresh = st.sidebar.toggle("Atualização automática", value=True)

    if modo_compacto:
        carregar_css(CSS_COMPACTO_FILE)

    altura_grafico = 260 if modo_compacto else 420
    altura_tabela = 180 if modo_compacto else 300
    qtd_logs = 8 if modo_compacto else 20

    st.title("Terminal Quant Pro - Live")
    st.caption(f"Ativo no display: {simbolo}")

    # 1. PERFORMANCE (24H)
    agora = datetime.now()
    desde_24h = agora - timedelta(hours=24)
    historico = mt5.history_deals_get(desde_24h, agora)
    df_fechadas = preparar_fechamentos(historico, simbolo)

    lucro_24h = float(df_fechadas["profit"].sum()) if not df_fechadas.empty else 0.0
    ganhos = float(df_fechadas[df_fechadas["profit"] > 0]["profit"].sum()) if not df_fechadas.empty else 0.0
    perdas = float(df_fechadas[df_fechadas["profit"] < 0]["profit"].sum()) if not df_fechadas.empty else 0.0
    acertos = int((df_fechadas["profit"] > 0).sum()) if not df_fechadas.empty else 0
    erros = int((df_fechadas["profit"] < 0).sum()) if not df_fechadas.empty else 0
    win_rate = (acertos / (acertos + erros) * 100) if (acertos + erros) > 0 else 0.0

    # 2. DADOS DE MERCADO
    rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, 100)
    if rates is None or len(rates) == 0:
        st.warning(f"Sem dados para {simbolo}. Verifique se o ativo esta na Observacao do Mercado.")
        mt5.shutdown()
        st.stop()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df["media_20"] = df["close"].rolling(window=20).mean()
    preco_atual = float(df["close"].iloc[-1])
    media_atual = float(df["media_20"].iloc[-1])

    posicoes = mt5.positions_get(symbol=simbolo)
    posicoes = list(posicoes) if posicoes else []

    # Linha 1: mercado e status
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Preco Atual", f"{preco_atual:.5f}")
    m2.metric("Media (20 min)", f"{media_atual:.5f}", delta=f"{preco_atual - media_atual:.5f}")
    m3.metric("Status Robo", "LIGADO" if autotrade else "MANUAL")
    m4.metric("Hora Local", agora.strftime("%H:%M:%S"))

    # Linha 2: resultados do robo
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Resultado 24h", f"${lucro_24h:.2f}")
    p2.metric("Ganhos", f"${ganhos:.2f}")
    p3.metric("Perdas", f"${perdas:.2f}")
    p4.metric("Win Rate", f"{win_rate:.1f}%")

    # Lógica de automação com trava de cooldown
    meta_batida = lucro_24h >= meta_lucro
    agora_ts = time.time()
    em_cooldown = (agora_ts - st.session_state.ultimo_trade_ts) < cooldown_seg

    if autotrade and not posicoes and not meta_batida and not em_cooldown:
        sinal = None
        if preco_atual > media_atual:
            sinal = "COMPRA"
        elif preco_atual < media_atual:
            sinal = "VENDA"

        if sinal:
            res = enviar_ordem(simbolo, lote, sinal, sl_input, tp_input)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                st.session_state.ultimo_trade_ts = agora_ts
                st.success(f"Ordem {sinal} executada pelo robo.")
            elif res:
                st.error(f"Falha ao executar {sinal}: {res.comment}")

    if meta_batida:
        st.success("Meta diaria atingida. Auto-trading pausado.")
    elif em_cooldown and autotrade:
        restante = int(cooldown_seg - (agora_ts - st.session_state.ultimo_trade_ts))
        st.info(f"Cooldown ativo: aguarde {max(restante, 0)}s para nova entrada.")

    # Execução manual
    c1, c2 = st.columns(2)
    if c1.button("COMPRAR", use_container_width=True):
        res = enviar_ordem(simbolo, lote, "COMPRA", sl_input, tp_input)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            st.session_state.ultimo_trade_ts = time.time()
            st.success("Compra executada.")
        elif res:
            st.error(f"Erro na compra: {res.comment}")
        else:
            st.error("Erro na compra: sem retorno da corretora.")

    if c2.button("VENDER", use_container_width=True):
        res = enviar_ordem(simbolo, lote, "VENDA", sl_input, tp_input)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            st.session_state.ultimo_trade_ts = time.time()
            st.success("Venda executada.")
        elif res:
            st.error(f"Erro na venda: {res.comment}")
        else:
            st.error("Erro na venda: sem retorno da corretora.")

    # Gráfico
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Preco",
        )
    )
    fig.add_trace(go.Scatter(x=df["time"], y=df["media_20"], line=dict(color="yellow"), name="Media 20"))
    fig.update_layout(
        template="plotly_dark",
        title=f"{simbolo} - M1",
        height=altura_grafico,
        margin=dict(l=0, r=0, b=0, t=40),
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True, key="grafico_principal")

    # Tabelas de abertas e fechadas
    tab_abertas, tab_fechadas, tab_logs = st.tabs(["Operacoes Abertas", "Operacoes Fechadas", "Diario de Bordo"])

    with tab_abertas:
        if posicoes:
            df_pos = pd.DataFrame(list(posicoes), columns=posicoes[0]._asdict().keys())
            cols = ["symbol", "type", "volume", "price_open", "sl", "tp", "profit"]
            cols = [c for c in cols if c in df_pos.columns]
            st.dataframe(df_pos[cols], use_container_width=True, height=altura_tabela)
        else:
            st.info("Nenhuma operacao aberta no momento.")

    with tab_fechadas:
        st.write("Resultado das operacoes fechadas do robo nas ultimas 24h.")
        if not df_fechadas.empty:
            cols = ["time", "symbol", "type", "volume", "price", "profit"]
            cols = [c for c in cols if c in df_fechadas.columns]
            st.dataframe(df_fechadas[cols], use_container_width=True, height=altura_tabela)
        else:
            st.info("Nenhuma operacao fechada encontrada nas ultimas 24h para este ativo.")

    with tab_logs:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                linhas = [linha.strip() for linha in f.readlines() if linha.strip()]
            if linhas:
                for linha in linhas[-qtd_logs:]:
                    st.caption(linha)
            else:
                st.info("Log vazio.")
        else:
            st.info("Arquivo de log ainda nao foi criado.")

    # Controles de atualização
    if st.button("Atualizar agora"):
        mt5.shutdown()
        st.rerun()

    mt5.shutdown()

    if auto_refresh:
        time.sleep(refresh_seg)
        st.rerun()