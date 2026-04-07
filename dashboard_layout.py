import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def ler_linhas_log(log_file):
    # Faz fallback para codificacoes legadas para nao quebrar a tela.
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            with open(log_file, "r", encoding=encoding) as f:
                return [linha.strip() for linha in f.readlines() if linha.strip()]
        except UnicodeDecodeError:
            continue

    with open(log_file, "rb") as f:
        conteudo = f.read().decode("utf-8", errors="replace")
    return [linha.strip() for linha in conteudo.splitlines() if linha.strip()]


def carregar_css(arquivo_css):
    if not os.path.exists(arquivo_css):
        return
    with open(arquivo_css, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_sidebar():
    st.sidebar.header("Configuracoes")
    simbolo = st.sidebar.text_input("Ativo", "EURUSD").strip().upper()
    modo_compacto = st.sidebar.toggle("Modo compacto", value=True)
    meta_lucro = st.sidebar.number_input("Meta Diaria ($)", value=10.0)
    lote = st.sidebar.number_input("Volume (Lote)", 0.01, 1.0, 0.01, 0.01)
    sl_input = st.sidebar.number_input("Stop Loss (Pts)", value=200)
    tp_input = st.sidebar.number_input("Take Profit (Pts)", value=400)
    max_spread_pts = st.sidebar.number_input("Spread maximo (pts)", min_value=0.0, value=20.0, step=1.0)
    autotrade = st.sidebar.toggle("Ativar Auto-Trading", value=False)
    cooldown_seg = st.sidebar.number_input("Cooldown entre ordens (s)", min_value=5, max_value=300, value=30, step=5)
    refresh_seg = st.sidebar.slider("Atualizar a cada (s)", min_value=1, max_value=30, value=3)
    auto_refresh = st.sidebar.toggle("Atualizacao automatica", value=True)

    return {
        "simbolo": simbolo,
        "modo_compacto": modo_compacto,
        "meta_lucro": meta_lucro,
        "lote": lote,
        "sl_input": sl_input,
        "tp_input": tp_input,
        "max_spread_pts": max_spread_pts,
        "autotrade": autotrade,
        "cooldown_seg": cooldown_seg,
        "refresh_seg": refresh_seg,
        "auto_refresh": auto_refresh,
    }


def render_header(simbolo):
    st.title("Terminal Quant Pro - Live")
    st.caption(f"Ativo no display: {simbolo}")


def render_metricas(preco_atual, media_atual, autotrade, agora, perf):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Preco Atual", f"{preco_atual:.5f}")
    m2.metric("Media (20 min)", f"{media_atual:.5f}", delta=f"{preco_atual - media_atual:.5f}")
    m3.metric("Status Robo", "LIGADO" if autotrade else "MANUAL")
    m4.metric("Hora Local", agora.strftime("%H:%M:%S"))

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Resultado 24h", f"${perf['lucro_24h']:.2f}")
    p2.metric("Ganhos", f"${perf['ganhos']:.2f}")
    p3.metric("Perdas", f"${perf['perdas']:.2f}")
    p4.metric("Win Rate", f"{perf['win_rate']:.1f}%")


def render_alertas(meta_batida, em_cooldown, cooldown_seg, ultimo_trade_ts, agora_ts, autotrade):
    if meta_batida:
        st.success("Meta diaria atingida. Auto-trading pausado.")
    elif em_cooldown and autotrade:
        restante = int(cooldown_seg - (agora_ts - ultimo_trade_ts))
        st.info(f"Cooldown ativo: aguarde {max(restante, 0)}s para nova entrada.")


def render_botoes_execucao():
    c1, c2 = st.columns(2)
    comprar = c1.button("COMPRAR", use_container_width=True)
    vender = c2.button("VENDER", use_container_width=True)
    return comprar, vender


def render_grafico(df, simbolo, altura_grafico):
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


def render_tabelas_e_logs(posicoes, df_fechadas, log_file, altura_tabela, qtd_logs):
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
        if os.path.exists(log_file):
            linhas = ler_linhas_log(log_file)
            if linhas:
                for linha in linhas[-qtd_logs:]:
                    st.caption(linha)
            else:
                st.info("Log vazio.")
        else:
            st.info("Arquivo de log ainda nao foi criado.")
