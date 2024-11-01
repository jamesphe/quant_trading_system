from strategies.chandelier_zlsma_strategy import ChandelierZlSmaStrategy
import backtrader as bt
import pandas as pd
from data_fetch import get_stock_data, get_etf_data, get_us_stock_data
import os
from datetime import datetime, timedelta
import argparse
import sys

def run_backtest(symbol, start_date, end_date, printlog=True, **strategy_params):
    """
    运行回测

    参数：
    - symbol: 股票代码，例如 '600519'
    - start_date: 回测开始日期，格式 'YYYY-MM-DD'
    - end_date: 回测结束日期，格式 'YYYY-MM-DD'
    - printlog: 是否打印日志
    - **strategy_params: 策略参数，用于初始化策略
    """
    # 获取股票数据
    if symbol.startswith(('51', '159')):  # ETF
        data_df = get_etf_data(symbol, start_date, end_date)
    elif symbol.isdigit():  # A股
        data_df = get_stock_data(symbol, start_date, end_date)
    else:  # 美股
        data_df = get_us_stock_data(symbol, start_date, end_date)

    if data_df.empty:
        print(f"股票 {symbol} 没有可用的数据进行回测。")
        return

    # 初始化 Cerebro 引擎
    cerebro = bt.Cerebro()

    # 添加策略，并传入策略参数
    cerebro.addstrategy(ChandelierZlSmaStrategy, printlog=printlog, **strategy_params)

    # 将 Pandas DataFrame 转为 Backtrader 数据格式
    data_bt = bt.feeds.PandasData(
        dataname=data_df,
        fromdate=pd.to_datetime(start_date),
        todate=pd.to_datetime(end_date),
        plot=False
    )
    cerebro.adddata(data_bt, name=symbol)

    # 设置初始资金
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)

    # 设置交易佣金（例如 0.1%）
    cerebro.broker.setcommission(commission=0.001)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                        timeframe=bt.TimeFrame.Days, compression=1)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    # 打印初始资金
    print(f'初始资金: {initial_cash:.2f}')

    # 运行策略，并获取策略实例列表
    results = cerebro.run()

    # 获取第一个策略实例
    strat = results[0]

    # 打印最终资金
    final_cash = cerebro.broker.getvalue()
    total_profit = sum(trade.pnlcomm for trade in strat.trades if trade.isclosed)
    roi = (total_profit / initial_cash) * 100

    print(f'最终资金: {final_cash:.2f}')
    print(f'总收益: {total_profit:.2f}')
    print(f'收益率: {roi:.2f}%')

    # 计算胜率
    win_rate = (len([trade for trade in strat.trades if trade.pnl > 0]) / len(strat.trades)) * 100
    print(f'胜率: {win_rate:.2f}%')
    # 计算夏普比率
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe_analysis.get('sharperatio', None)
    if sharpe_ratio is not None:
        print(f'夏普比率: {sharpe_ratio:.2f}')
    else:
        print('夏普比率无法计算。')

    # 计算最大回撤
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', None)
    if max_drawdown is not None:
        print(f'最大回撤: {max_drawdown:.2f}%')
    else:
        print('最大回撤无法计算。')
        
    # 打印交易记录
    print("\n交易记录:")
    for i, trade in enumerate(strat.trades):
        print(f"交易 {i+1}:")
        print(f"  开仓日期: {bt.num2date(trade.dtopen)}")
        print(f"  开仓价格: {trade.price:.2f}")
        print(f"  开仓数量: {trade.size}")
        print(f"  平仓日期: {bt.num2date(trade.dtclose)}")
        print(f"  交易盈亏: {trade.pnl:.2f}")
        print(f"  交易佣金: {trade.commission:.2f}")
        print(f"  净盈亏: {trade.pnlcomm:.2f}")
        print()

    # 输出最新交易日的交易建议
    latest_date = data_df.index[-1]
    latest_close = data_df['Close'].iloc[-1]

    # 获取策略中的指标值
    if hasattr(strat, 'chandelier_exit_long') and len(strat.chandelier_exit_long) > 0:
        latest_chandelier_exit_long = strat.chandelier_exit_long[-1]
    else:
        latest_chandelier_exit_long = None

    if hasattr(strat, 'chandelier_exit_short') and len(strat.chandelier_exit_short) > 0:
        latest_chandelier_exit_short = strat.chandelier_exit_short[-1]
    else:
        latest_chandelier_exit_short = None

    if hasattr(strat, 'zlsma') and len(strat.zlsma) > 0:
        latest_zlsma = strat.zlsma[0]
    else:
        latest_zlsma = None

    print("\n最新交易日交易建议:")
    print(f"日期: {latest_date.strftime('%Y-%m-%d')}")
    print(f"收盘价: {latest_close:.2f}")
    print(f"开盘价: {data_df['Open'].iloc[-1]:.2f}")
    print(f"最高价: {data_df['High'].iloc[-1]:.2f}")
    print(f"最低价: {data_df['Low'].iloc[-1]:.2f}")
    print(f"涨跌幅: {(latest_close - data_df['Close'].iloc[-2]) / data_df['Close'].iloc[-2] * 100:.2f}%")
    
    if hasattr(strat, 'chandelier_exit_long') and len(strat.chandelier_exit_long) > 0:
        latest_chandelier_exit_long = strat.chandelier_exit_long[0]
        previous_chandelier_exit_long = strat.chandelier_exit_long[-1] if len(strat.chandelier_exit_long) > 1 else None
        print(f"多头止损: 前值: {previous_chandelier_exit_long:.2f}, 最新值: {latest_chandelier_exit_long:.2f}")
    else:
        print("多头止损: 无法获取")
    
    if hasattr(strat, 'chandelier_exit_short') and len(strat.chandelier_exit_short) > 0:
        latest_chandelier_exit_short = strat.chandelier_exit_short[0]
        previous_chandelier_exit_short = strat.chandelier_exit_short[-1] if len(strat.chandelier_exit_short) > 1 else None
        print(f"空头止损: 前值: {previous_chandelier_exit_short:.2f}, 最新值: {latest_chandelier_exit_short:.2f}")
    else:
        print("空头止损: 无法获取")
    
    if latest_zlsma is not None:
        print(f"ZLSMA: 前值: {strat.zlsma[-1]:.2f}, 最新值: {latest_zlsma:.2f}")
    else:
        print("ZLSMA: 无法获取")
    
    if len(strat.signal) > 0:
        last_signal = strat.signal[0]
        if last_signal == 1:
            signal_type = "买入，方向从空头转为多头，且收盘价高于ZLSMA线。"
        elif last_signal == 2:
            signal_type = "买入，多头趋势中，ZLSMA上升。"
        elif last_signal == 3:
            signal_type = "建仓预警，收盘价高于空头止损价，但没有高于多头止损价。"
        elif last_signal == -1:
            signal_type = "清仓，因为方向从多头转为空头。"
        elif last_signal == -2:
            signal_type = "减仓预警，多头趋势中，但ZLSMA未上升。"
        elif last_signal == -3:
            signal_type = "减仓或清仓，收盘价低于多头止损价，但没有低于空头止损价。"
        else:
            signal_type = "无交易信号，当前市场趋势不明确。"
    else:
        signal_type = "无交易信号"
    
    print(f"交易建议: {signal_type}")

if __name__ == '__main__':

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='股票回测程序')
    parser.add_argument('symbol', type=str, help='股票代码')
    parser.add_argument('-s', '--start', type=str, default=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'), help='开始日期')
    parser.add_argument('-e', '--end', type=str, default=datetime.now().strftime('%Y-%m-%d'), help='结束日期')
    parser.add_argument('-p', '--period', type=int, default=14, help='ATR、CE和ZLSMA周期')
    parser.add_argument('-m', '--mult', type=float, default=2, help='ATR倍数')
    parser.add_argument('-i', '--inv', type=float, default=0.8, help='资金比例')
    parser.add_argument('-y', '--pyr', type=int, default=0, help='最大加仓次数')
    parser.add_argument('--log', action='store_true', help='打印日志')
    args = parser.parse_args()

    print(f"开始回测股票: {args.symbol}")

    # 检查是否存在优化结果文件
    optimization_file = f"results/{args.symbol}_optimization_results.csv"
    if os.path.exists(optimization_file) and len(sys.argv) == 2:
        print(f"发现优化结果文件：{optimization_file}，正在加载参数...")
        opt_results = pd.read_csv(optimization_file)
        if not opt_results.empty:
            best_params = opt_results.iloc[0]
            args.start = args.start  # 保持默认值
            args.end = args.end  # 保持默认值
            args.period = int(best_params['period'])
            args.mult = float(best_params['mult'])
            args.inv = float(best_params['investment_fraction'])
            args.pyr = int(best_params['max_pyramiding'])
            args.log = True
            print("已加载优化参数。")
        else:
            print("优化结果文件为空，使用默认参数。")
    else:
        print("未找到优化结果文件或提供了其他参数，使用命令行参数。")

    # 运行回测
    run_backtest(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        period=args.period,
        mult=args.mult,
        investment_fraction=args.inv,
        max_pyramiding=args.pyr,
        printlog=True
    )
