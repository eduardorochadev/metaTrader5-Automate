import os
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd


def registrar_log(mensagem, log_file):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {mensagem}\n")


def garantir_log(log_file):
    if not os.path.exists(log_file):
        registrar_log("=== SISTEMA INICIADO ===", log_file)


def enviar_ordem(simbolo, volume, tipo_ordem, sl_pts, tp_pts, log_file):
    info = mt5.symbol_info(simbolo)
    if info is None:
        registrar_log(f"FALHA AO ENVIAR ORDEM: ativo {simbolo} nao encontrado.", log_file)
        return None

    if not info.visible:
        mt5.symbol_select(simbolo, True)

    tick = mt5.symbol_info_tick(simbolo)
    if tick is None:
        registrar_log(f"FALHA AO ENVIAR ORDEM: sem tick para {simbolo}.", log_file)
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
        registrar_log(f"ERRO mt5.order_send: {mt5.last_error()}", log_file)
        return None

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        registrar_log(f"ORDEM ABERTA: {tipo_ordem} | Preco: {preco} | SL: {sl} | TP: {tp}", log_file)
    else:
        registrar_log(
            f"ORDEM REJEITADA ({tipo_ordem}): retcode={resultado.retcode} | comentario={resultado.comment}",
            log_file,
        )

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


def calcular_performance(df_fechadas):
    if df_fechadas.empty:
        return {
            "lucro_24h": 0.0,
            "ganhos": 0.0,
            "perdas": 0.0,
            "acertos": 0,
            "erros": 0,
            "win_rate": 0.0,
        }

    lucro_24h = float(df_fechadas["profit"].sum())
    ganhos = float(df_fechadas[df_fechadas["profit"] > 0]["profit"].sum())
    perdas = float(df_fechadas[df_fechadas["profit"] < 0]["profit"].sum())
    acertos = int((df_fechadas["profit"] > 0).sum())
    erros = int((df_fechadas["profit"] < 0).sum())
    win_rate = (acertos / (acertos + erros) * 100) if (acertos + erros) > 0 else 0.0

    return {
        "lucro_24h": lucro_24h,
        "ganhos": ganhos,
        "perdas": perdas,
        "acertos": acertos,
        "erros": erros,
        "win_rate": win_rate,
    }


def obter_dados_mercado(simbolo, candles=100):
    rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, candles)
    if rates is None or len(rates) == 0:
        return None, None, None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df["media_20"] = df["close"].rolling(window=20).mean()

    preco_atual = float(df["close"].iloc[-1])
    media_atual = float(df["media_20"].iloc[-1])
    return df, preco_atual, media_atual


def listar_posicoes(simbolo):
    posicoes = mt5.positions_get(symbol=simbolo)
    return list(posicoes) if posicoes else []


def avaliar_sinal(preco_atual, media_atual):
    if preco_atual > media_atual:
        return "COMPRA"
    if preco_atual < media_atual:
        return "VENDA"
    return None
