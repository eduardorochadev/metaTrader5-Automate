import time
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import streamlit as st

from dashboard_layout import (
    carregar_css,
    render_alertas,
    render_botoes_execucao,
    render_grafico,
    render_header,
    render_metricas,
    render_sidebar,
    render_tabelas_e_logs,
)
from trading_logic import (
    avaliar_sinal,
    calcular_performance,
    enviar_ordem,
    garantir_log,
    listar_posicoes,
    obter_dados_mercado,
    preparar_fechamentos,
)

st.set_page_config(page_title="Terminal Quant Pro", layout="wide")

LOG_FILE = "log_operacoes.txt"
CSS_COMPACTO_FILE = "styles_compacto.css"

if not mt5.initialize():
    st.error("Erro ao conectar no MT5")
    st.stop()

garantir_log(LOG_FILE)

if "ultimo_trade_ts" not in st.session_state:
    st.session_state.ultimo_trade_ts = 0.0

cfg = render_sidebar()
if cfg["modo_compacto"]:
    carregar_css(CSS_COMPACTO_FILE)

altura_grafico = 260 if cfg["modo_compacto"] else 420
altura_tabela = 180 if cfg["modo_compacto"] else 300
qtd_logs = 8 if cfg["modo_compacto"] else 20

render_header(cfg["simbolo"])

agora = datetime.now()
desde_24h = agora - timedelta(hours=24)
historico = mt5.history_deals_get(desde_24h, agora)
df_fechadas = preparar_fechamentos(historico, cfg["simbolo"])
perf = calcular_performance(df_fechadas)

df, preco_atual, media_atual = obter_dados_mercado(cfg["simbolo"], candles=100)
if df is None:
    st.warning(f"Sem dados para {cfg['simbolo']}. Verifique se o ativo esta na Observacao do Mercado.")
    mt5.shutdown()
    st.stop()

posicoes = listar_posicoes(cfg["simbolo"])

render_metricas(preco_atual, media_atual, cfg["autotrade"], agora, perf)

meta_batida = perf["lucro_24h"] >= cfg["meta_lucro"]
agora_ts = time.time()
em_cooldown = (agora_ts - st.session_state.ultimo_trade_ts) < cfg["cooldown_seg"]

if cfg["autotrade"] and not posicoes and not meta_batida and not em_cooldown:
    sinal = avaliar_sinal(df)
    if sinal:
        res = enviar_ordem(
            cfg["simbolo"],
            cfg["lote"],
            sinal,
            cfg["sl_input"],
            cfg["tp_input"],
            LOG_FILE,
            cfg["max_spread_pts"],
        )
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            st.session_state.ultimo_trade_ts = agora_ts
            st.success(f"Ordem {sinal} executada pelo robo.")
        elif res:
            st.error(f"Falha ao executar {sinal}: {res.comment}")
        else:
            st.warning("Entrada automatica bloqueada por validacao (spread/stops/ativo).")

render_alertas(
    meta_batida,
    em_cooldown,
    cfg["cooldown_seg"],
    st.session_state.ultimo_trade_ts,
    agora_ts,
    cfg["autotrade"],
)

comprar, vender = render_botoes_execucao()
if comprar:
    res = enviar_ordem(
        cfg["simbolo"],
        cfg["lote"],
        "COMPRA",
        cfg["sl_input"],
        cfg["tp_input"],
        LOG_FILE,
        cfg["max_spread_pts"],
    )
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        st.session_state.ultimo_trade_ts = time.time()
        st.success("Compra executada.")
    elif res:
        st.error(f"Erro na compra: {res.comment}")
    else:
        st.error("Erro na compra: sem retorno da corretora.")

if vender:
    res = enviar_ordem(
        cfg["simbolo"],
        cfg["lote"],
        "VENDA",
        cfg["sl_input"],
        cfg["tp_input"],
        LOG_FILE,
        cfg["max_spread_pts"],
    )
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        st.session_state.ultimo_trade_ts = time.time()
        st.success("Venda executada.")
    elif res:
        st.error(f"Erro na venda: {res.comment}")
    else:
        st.error("Erro na venda: sem retorno da corretora.")

render_grafico(df, cfg["simbolo"], altura_grafico)
render_tabelas_e_logs(posicoes, df_fechadas, LOG_FILE, altura_tabela, qtd_logs)

if st.button("Atualizar agora"):
    mt5.shutdown()
    st.rerun()

mt5.shutdown()

if cfg["auto_refresh"]:
    time.sleep(cfg["refresh_seg"])
    st.rerun()