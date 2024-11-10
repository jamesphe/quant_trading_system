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
        return {'error': f"股票 {symbol} 没有可用的数据进行回测。"}

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

    # 运行策略，并获取策略实例列表
    results = cerebro.run()

    # 获取第一个策略实例
    strat = results[0]

    # 计算基本指标
    final_cash = cerebro.broker.getvalue()
    total_profit = sum(trade.pnlcomm for trade in strat.trades if trade.isclosed)
    roi = (total_profit / initial_cash) * 100
    win_rate = (len([trade for trade in strat.trades if trade.pnl > 0]) / len(strat.trades)) * 100 if strat.trades else 0

    # 计算夏普比率
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe_analysis.get('sharperatio', None)

    # 计算最大回撤
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', None)

    # 获取交易记录
    trades_list = []
    # 记录已关闭的交易
    for i, trade in enumerate(strat.trades):
        try:
            close_date = bt.num2date(trade.dtclose).strftime('%Y-%m-%d') if trade.dtclose > 0 else None
            trades_list.append({
                'trade_number': i + 1,
                'status': 'closed' if close_date else 'open',
                'open_date': bt.num2date(trade.dtopen).strftime('%Y-%m-%d'),
                'open_price': float(trade.price),
                'size': int(trade.size),
                'close_date': close_date,
                'pnl': float(trade.pnl) if close_date else 0.0,
                'commission': float(trade.commission),
                'net_pnl': float(trade.pnlcomm) if close_date else 0.0
            })
        except (ValueError, AttributeError) as e:
            print(f"警告: 处理交易记录时出错: {e}")
            print(f"交易详情: dtclose={trade.dtclose}, dtopen={trade.dtopen}")
            continue

    
    # 记录未关闭的交易
    open_trades = strat._trades  # 获取当前未关闭的交易
    for i, trade in enumerate(open_trades, start=len(trades_list)+1):
        if trade is not None and hasattr(trade, 'isclosed') and not trade.isclosed:
            try:
                trades_list.append({
                    'trade_number': i,
                    'status': 'open',
                    'open_date': bt.num2date(trade.dtopen).strftime('%Y-%m-%d'),
                    'open_price': float(trade.price),
                    'size': int(trade.size),
                    'close_date': None,
                    'pnl': 0.0,
                    'commission': float(trade.commission),
                    'net_pnl': 0.0
                })
            except (ValueError, AttributeError) as e:
                print(f"警告: 处理未完成交易记录时出错: {e}")
                continue
    

    # 获取最新交易日数据
    latest_date = data_df.index[-1]
    latest_close = data_df['Close'].iloc[-1]
    
    # 获取最新指标值
    latest_chandelier_exit_long = None
    previous_chandelier_exit_long = None
    if hasattr(strat, 'chandelier_exit_long') and len(strat.chandelier_exit_long) > 0:
        latest_chandelier_exit_long = strat.chandelier_exit_long[0]
        previous_chandelier_exit_long = strat.chandelier_exit_long[-1] if len(strat.chandelier_exit_long) > 1 else None

    latest_chandelier_exit_short = None
    previous_chandelier_exit_short = None
    if hasattr(strat, 'chandelier_exit_short') and len(strat.chandelier_exit_short) > 0:
        latest_chandelier_exit_short = strat.chandelier_exit_short[0]
        previous_chandelier_exit_short = strat.chandelier_exit_short[-1] if len(strat.chandelier_exit_short) > 1 else None

    latest_zlsma = None
    previous_zlsma = None
    if hasattr(strat, 'zlsma') and len(strat.zlsma) > 0:
        latest_zlsma = strat.zlsma[0]
        previous_zlsma = strat.zlsma[-1] if len(strat.zlsma) > 1 else None

    # 获取信号类型
    signal_type = "无交易信号"
    if len(strat.signal) > 0:
        last_signal = strat.signal[0]
        signal_map = {
            1: "买入，方向从空头转为多头，且收盘价高于ZLSMA线。",
            2: "买入，多头趋势中，ZLSMA上升。",
            3: "建仓预警，收盘价高于空头止损价，但没有高于多头止损价。",
            -1: "清仓，因为方向从多头转为空头。",
            -2: "减仓预警，多头趋势中，但ZLSMA未上升。",
            -3: "减仓或清仓，收盘价低于多头止损价，但没有低于空头止损价。"
        }
        signal_type = signal_map.get(last_signal, "无交易信号，当前市场趋势不明确。")

    # 获取当前持仓信息和持仓订单列表
    current_position = None
    current_orders = []
    
    if strat.position.size != 0:
        # 基本持仓信息
        current_position = {
            'size': strat.position.size,
            'price': strat.position.price,
            'value': strat.position.size * latest_close,
            'unrealized_pnl': (latest_close - strat.position.price) * strat.position.size,
            'unrealized_pnl_pct': ((latest_close - strat.position.price) / 
                                 strat.position.price) * 100
        }
        
        # 获取当前未完成的订单
        for order in strat.broker.orders:
            if order.status not in [order.Completed, order.Canceled, order.Expired]:
                current_orders.append({
                    'order_id': order.ref,
                    'type': 'buy' if order.isbuy() else 'sell',
                    'status': order.getstatusname(),
                    'size': order.size,
                    'price': order.price,
                    'created_date': bt.num2date(order.created.dt).strftime('%Y-%m-%d'),
                    'valid_until': (bt.num2date(order.valid.dt).strftime('%Y-%m-%d') 
                                  if order.valid else None)
                })

    print("\n最新交易日交易建议:")
    print(f"日期: {latest_date.strftime('%Y-%m-%d')}")
    print(f"收盘价: {latest_close:.2f}")
    print(f"开盘价: {data_df['Open'].iloc[-1]:.2f}")
    print(f"最高价: {data_df['High'].iloc[-1]:.2f}")
    print(f"最低价: {data_df['Low'].iloc[-1]:.2f}")
    print(f"涨跌幅: {(latest_close - data_df['Close'].iloc[-2]) / data_df['Close'].iloc[-2] * 100:.2f}%")
    
    return {
        'basic_info': {
            'initial_cash': initial_cash,
            'final_cash': final_cash,
            'total_profit': total_profit,
            'roi': roi,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown
        },
        'trades': trades_list,
        'latest_data': {
            'date': latest_date.strftime('%Y-%m-%d'),
            'close': latest_close,
            'open': data_df['Open'].iloc[-1],
            'high': data_df['High'].iloc[-1],
            'low': data_df['Low'].iloc[-1],
            'change_pct': ((latest_close - data_df['Close'].iloc[-2]) / 
                         data_df['Close'].iloc[-2] * 100)
        },
        'indicators': {
            'chandelier_exit_long': {
                'current': latest_chandelier_exit_long,
                'previous': previous_chandelier_exit_long
            },
            'chandelier_exit_short': {
                'current': latest_chandelier_exit_short,
                'previous': previous_chandelier_exit_short
            },
            'zlsma': {
                'current': latest_zlsma,
                'previous': previous_zlsma
            }
        },
        'signal': signal_type,
        'current_position': current_position,
        'current_orders': current_orders
    }

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
    results = run_backtest(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        period=args.period,
        mult=args.mult,
        investment_fraction=args.inv,
        max_pyramiding=args.pyr,
        printlog=True
    )
    
    if results:
        print("\n回测结果:")
        print(f"初始资金: {results['basic_info']['initial_cash']:.2f}")
        print(f"最终资金: {results['basic_info']['final_cash']:.2f}")
        print(f"总收益: {results['basic_info']['total_profit']:.2f}")
        print(f"收益率: {results['basic_info']['roi']:.2f}%")
        print(f"胜率: {results['basic_info']['win_rate']:.2f}%")
        print(f"夏普比率: {results['basic_info']['sharpe_ratio']:.2f}")
        print(f"最大回撤: {results['basic_info']['max_drawdown']:.2f}%")
        
        if results.get('current_position'):
            print("\n当前持仓信息:")
            print(f"  持仓数量: {results['current_position']['size']}")
            print(f"  持仓成本: {results['current_position']['price']:.2f}")
            
        if results.get('current_orders'):
            print("\n未完成订单:")
            for order in results['current_orders']:
                print(f"  订单类型: {'买入' if order['type'] == 'buy' else '卖出'}")
                print(f"  订单数量: {order['size']}")
                # 添加价格检查
                if order['price'] is not None:
                    print(f"  订单价格: {order['price']:.2f}")
                else:
                    print("  订单价格: 市价单")
                print(f"  创建时间: {order['created_date']}")
        print("\n交易记录:")
        for trade in results['trades']:
            print(f"\n交易 {trade['trade_number']}:")
            print(f"  状态: {trade['status']}")
            print(f"  开仓日期: {trade['open_date']}")
            print(f"  开仓价格: {trade['open_price']:.2f}")
            print(f"  开仓数量: {trade['size']}")
            if trade['status'] == 'closed':
                print(f"  平仓日期: {trade['close_date']}")
                print(f"  交易盈亏: {trade['pnl']:.2f}")
                print(f"  交易佣金: {trade['commission']:.2f}")
                print(f"  净盈亏: {trade['net_pnl']:.2f}")
                
        print(f"\n交易建议: {results['signal']}")

        
        