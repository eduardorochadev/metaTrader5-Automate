import os
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd


ROBOT_MAGIC = 123456
ROBOT_COMMENT = "Execucao Python"


def registrar_log(mensagem, log_file):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {mensagem}\n")


def garantir_log(log_file):
    if not os.path.exists(log_file):
        registrar_log("=== SISTEMA INICIADO ===", log_file)


def normalizar_volume(volume, info):
    min_vol = float(getattr(info, "volume_min", 0.01) or 0.01)
    max_vol = float(getattr(info, "volume_max", 100.0) or 100.0)
    step = float(getattr(info, "volume_step", 0.01) or 0.01)

    vol_clamp = max(min_vol, min(float(volume), max_vol))
    # Ajusta para o passo do ativo
    passos = round((vol_clamp - min_vol) / step)
    vol_norm = min_vol + (passos * step)
    vol_norm = max(min_vol, min(vol_norm, max_vol))
    return round(vol_norm, 8)


def validar_stops(info, preco, sl, tp):
    stop_level = float(getattr(info, "trade_stops_level", 0) or 0)
    if stop_level <= 0:
        return True, ""

    dist_min = stop_level * info.point
    if abs(preco - sl) < dist_min:
        return False, f"SL muito proximo. Distancia minima: {stop_level} pts"
    if abs(tp - preco) < dist_min:
        return False, f"TP muito proximo. Distancia minima: {stop_level} pts"
    return True, ""


def enviar_ordem(simbolo, volume, tipo_ordem, sl_pts, tp_pts, log_file, max_spread_pts=None):
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

    if max_spread_pts is not None and max_spread_pts > 0:
        spread_pts = (tick.ask - tick.bid) / info.point
        if spread_pts > float(max_spread_pts):
            registrar_log(
                f"ORDEM BLOQUEADA ({tipo_ordem}): spread alto ({spread_pts:.1f} pts > {max_spread_pts} pts)",
                log_file,
            )
            return None

    ponto = info.point
    if tipo_ordem == "COMPRA":
        tipo, preco = mt5.ORDER_TYPE_BUY, tick.ask
        sl, tp = preco - (sl_pts * ponto), preco + (tp_pts * ponto)
    else:
        tipo, preco = mt5.ORDER_TYPE_SELL, tick.bid
        sl, tp = preco + (sl_pts * ponto), preco - (tp_pts * ponto)

    volume_norm = normalizar_volume(volume, info)
    ok_stops, motivo_stops = validar_stops(info, preco, sl, tp)
    if not ok_stops:
        registrar_log(f"ORDEM BLOQUEADA ({tipo_ordem}): {motivo_stops}", log_file)
        return None

    filling_mode = getattr(info, "filling_mode", mt5.ORDER_FILLING_FOK)
    if filling_mode not in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN):
        filling_mode = mt5.ORDER_FILLING_FOK

    solicitacao = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": float(volume_norm),
        "type": tipo,
        "price": preco,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": ROBOT_MAGIC,
        "comment": ROBOT_COMMENT,
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


def preparar_fechamentos(historico, simbolo, robot_magic=ROBOT_MAGIC, robot_comment=ROBOT_COMMENT):
    if not historico:
        return pd.DataFrame()

    df_hist = pd.DataFrame(list(historico), columns=historico[0]._asdict().keys())
    if "symbol" in df_hist.columns:
        df_hist = df_hist[df_hist["symbol"] == simbolo]

    # Mantem apenas operacoes do proprio robo para calculo de performance/meta.
    if not df_hist.empty:
        filtro_robo = pd.Series(False, index=df_hist.index)
        if "magic" in df_hist.columns:
            filtro_robo = filtro_robo | (df_hist["magic"] == robot_magic)
        if "comment" in df_hist.columns:
            filtro_robo = filtro_robo | (df_hist["comment"].astype(str) == str(robot_comment))
        if "magic" in df_hist.columns or "comment" in df_hist.columns:
            df_hist = df_hist[filtro_robo]

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


def avaliar_sinal(df):
    if df is None or len(df) < 21:
        return None

    anterior = df.iloc[-2]
    atual = df.iloc[-1]

    # Sinal por cruzamento confirmado do fechamento em relacao a media.
    if anterior["close"] <= anterior["media_20"] and atual["close"] > atual["media_20"]:
        return "COMPRA"
    if anterior["close"] >= anterior["media_20"] and atual["close"] < atual["media_20"]:
        return "VENDA"
    return None
