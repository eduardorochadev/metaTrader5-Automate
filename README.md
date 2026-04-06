# Daytrade - Monitor MetaTrader 5

Projeto simples para conectar ao MetaTrader 5, consultar cotações e visualizar candles do EURUSD com Streamlit.

## O que tem aqui

- `painel.py`: painel web com gráfico de candles (M1) do EURUSD.
- `verificar.py`: teste rápido de conexão e leitura do preço atual (bid) do EURUSD.

## Pré-requisitos

- Python 3.10+
- MetaTrader 5 instalado e aberto
- Ativo `EURUSD` visível na *Observação do Mercado* do MT5

## Instalação

```bash
pip install streamlit plotly pandas MetaTrader5
```

## Como executar

### 1) Testar conexão e preço atual

```bash
python verificar.py
```

### 2) Abrir painel com gráfico

```bash
streamlit run painel.py
```

## Observações

- Se aparecer erro de inicialização, confirme se o MT5 está aberto.
- O projeto foi mantido enxuto para facilitar evolução para automações futuras.
