# Protocolo de Teste do Robo (7 dias)

Objetivo: validar se o robo esta estavel, seguro e consistente antes de operar em conta real.

## Regras do Teste

1. Ambiente: conta demo.
2. Timeframe: M1 (o mesmo do robo atual).
3. Ativo: manter fixo por todo o teste (exemplo: EURUSD).
4. Risco: usar lote minimo no inicio.
5. Janela de teste: 7 dias corridos, cobrindo horarios diferentes.
6. Nao mudar parametros no meio do dia. Se mudar, registrar no campo observacoes.

## Checklist Diario (operacional)

Marque Sim ou Nao para cada item:

1. MT5 conectado sem erros.
2. Dados do ativo carregando normal.
3. Auto-Trading ativado somente no horario planejado.
4. Bloqueio por spread funcionou quando spread ficou alto.
5. Bloqueio por SL/TP invalido funcionou (se aplicavel).
6. Cooldown impediu entradas repetidas.
7. Meta diaria respeitada quando atingida.
8. Logs registrados sem erro de leitura.
9. Nao houve ordem duplicada inesperada.
10. Painel e historico do MT5 batem entre si.

## Registro Diario (preencher ao fim de cada dia)

Use o arquivo REGISTRO_TESTE_ROBO.csv para preencher os dados.

Campos principais:

1. date: data do teste.
2. session: horario/sessao operada (exemplo: Londres, NY).
3. symbol: ativo testado.
4. trades_total: total de trades fechados no dia.
5. wins: trades positivos.
6. losses: trades negativos.
7. gross_profit: soma dos ganhos.
8. gross_loss: soma das perdas (valor negativo).
9. net_profit: resultado liquido do dia.
10. win_rate_pct: taxa de acerto.
11. max_dd_day: maior drawdown do dia.
12. blocked_spread_count: quantas entradas foram bloqueadas por spread.
13. blocked_stops_count: quantas entradas foram bloqueadas por stops invalidos.
14. duplicate_order_incidents: incidentes de ordem duplicada.
15. errors_count: erros tecnicos observados.
16. notes: observacoes relevantes.

## Criterios Objetivos de Aprovacao

Aprovado para fase seguinte (demo avancada ou lote maior na demo) somente se TODOS os criterios forem atendidos:

1. Estabilidade tecnica:
- 0 incidentes de ordem duplicada.
- 0 travamentos criticos.
- 0 dias sem log.

2. Controle de risco:
- Drawdown diario maximo dentro do limite definido por voce.
- Nenhum dia com perda extrema fora do limite.

3. Consistencia:
- Pelo menos 5 de 7 dias com execucao limpa (sem erro tecnico relevante).
- Resultado liquido acumulado nao negativo.

4. Qualidade de execucao:
- Bloqueios de spread/stops funcionando quando acionados.
- Sem sinais fora da logica esperada.

## Criterios de Reprovacao

1. Ordens duplicadas em qualquer dia.
2. Divergencia entre painel e historico do MT5 sem explicacao.
3. Drawdown acima do limite definido.
4. Erros tecnicos recorrentes (2 dias ou mais com falhas graves).

## Plano de Acao se Reprovar

1. Identificar causa principal (sinal, risco, execucao, conectividade).
2. Corrigir UMA variavel por vez.
3. Rodar novo ciclo de 7 dias com os mesmos criterios.
4. Comparar resultados entre ciclos.

## Recomendacao de Evolucao

1. Ciclo 1: lote minimo, 7 dias.
2. Ciclo 2: mesmo lote, mais 7 dias em horario diferente.
3. Ciclo 3: ajuste pequeno de parametro, mais 7 dias.
4. Conta real somente com consistencia em ciclos consecutivos.
