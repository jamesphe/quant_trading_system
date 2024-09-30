from strategies.chandelier_zlsma_strategy import ChandelierZlSmaStrategy
import backtrader as bt
import pandas as pd
from data_fetch import get_stock_data
import os

def run_backtest(symbol, start_date, end_date, printlog=False, **strategy_params):
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
    data_df = get_stock_data(symbol, start_date, end_date)

    if data_df.empty:
        print(f"股票 {symbol} 没有可用的数据进行回测。")
        return

    # 添加调试信息
    print("数据框的列名:")
    print(data_df.columns)
    print("\n数据框的前几行:")
    print(data_df.head())

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
    initial_cash = 20000.0
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
        # print(f"  平仓价格: {trade.barclose:.2f}")
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
        latest_zlsma = strat.zlsma[-1]
    else:
        latest_zlsma = None

    print("\n最新交易日交易建议:")
    print(f"日期: {latest_date.strftime('%Y-%m-%d')}")
    print(f"收盘价: {latest_close:.2f}")
    
    if latest_chandelier_exit_long is not None:
        print(f"多头止损: {latest_chandelier_exit_long:.2f}")
    else:
        print("多头止损: 无法获取")
    
    if latest_chandelier_exit_short is not None:
        print(f"空头止损: {latest_chandelier_exit_short:.2f}")
    else:
        print("空头止损: 无法获取")
    
    if latest_zlsma is not None:
        print(f"ZLSMA: {latest_zlsma:.2f}")
    else:
        print("ZLSMA: 无法获取")

    if latest_chandelier_exit_long is not None and latest_zlsma is not None:
        if latest_close > latest_chandelier_exit_long and latest_close > latest_zlsma:
            print("建议: 买入或持有")
        elif latest_close < latest_chandelier_exit_short and latest_close < latest_zlsma:
            print("建议: 卖出或观望")
        else:
            print("建议: 观望")
    else:
        print("无法给出建议：缺少必要的指标数据")

    # 可选：绘制结果
    # cerebro.plot(style='candlestick', volume=False, barup='green', bardown='red')[0][0]

if __name__ == '__main__':
    import argparse
    import sys
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='股票回测程序')
    parser.add_argument('symbol', type=str, help='股票代码')
    parser.add_argument('-s', '--start', type=str, default='2024-01-01', help='开始日期')
    parser.add_argument('-e', '--end', type=str, default='2024-09-28', help='结束日期')
    parser.add_argument('-l', '--len', type=int, default=14, help='ATR和CE周期')
    parser.add_argument('-m', '--mult', type=float, default=2, help='ATR倍数')
    parser.add_argument('-z', '--zlsma', type=int, default=14, help='ZLSMA周期')
    parser.add_argument('-i', '--inv', type=float, default=0.8, help='资比例')
    parser.add_argument('-p', '--pyr', type=int, default=0, help='最大加仓次数')
    parser.add_argument('--log', action='store_true', help='打印日志')
    args = parser.parse_args()

    print(f"开始回测股票: {args.symbol}")

    # 检查是否存在优化结果文件
    optimization_file = f"{args.symbol}_optimization_results.csv"
    if os.path.exists(optimization_file) and len(sys.argv) == 2:
        print(f"发现优化结果文件：{optimization_file}，正在加载参数...")
        opt_results = pd.read_csv(optimization_file)
        if not opt_results.empty:
            best_params = opt_results.iloc[0]
            args.start = args.start  # 保持默认值
            args.end = args.end  # 保持默认值
            args.len = int(best_params['length'])
            args.mult = float(best_params['mult'])
            args.zlsma = int(best_params['zlsma_length'])
            args.inv = float(best_params['investment_fraction'])
            args.pyr = int(best_params['max_pyramiding'])
            args.log = bool(best_params['printlog'])
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
        length=args.len,
        mult=args.mult,
        zlsma_length=args.zlsma,
        investment_fraction=args.inv,
        max_pyramiding=args.pyr,
        printlog=True
    )