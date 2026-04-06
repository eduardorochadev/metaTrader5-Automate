import MetaTrader5 as mt5

if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
else:
    print("MT5 initialized successfully")
# Puxa o preço do EURUSD que está na sua tela
    moeda = "EURUSD"
    preco = mt5.symbol_info_tick(moeda)
    
    if preco:
        print(f"O preço atual do {moeda} é: {preco.bid}")
    else:
        print(f"Ativo {moeda} não encontrado. Verifique se ele está na 'Observação do Mercado'.")

mt5.shutdown()