# generate_trade_signals.py

import backtrader as bt
import pandas as pd
import logging
import os

from data_fetch import get_stock_data  # 导入数据获取函数
from strategies import SwingStrategy, BreakoutStrategy, MeanReversionStrategy, MACDStrategy  # 导入策略类

# 设置日志配置
logging.basicConfig(
    filename='trade_signals.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

def load_best_parameters(csv_path='optimization_results.csv'):
    """
    从优化结果CSV文件中加载每个策略的最佳参数。
    
    参数：
    - csv_path: 优化结果的CSV文件路径
    
    返回：
    - best_parameters: 一个字典，键为策略名称，值为参数字典
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"优化结果文件不存在: {csv_path}")
    
    optimization_results = pd.read_csv(csv_path)
    best_parameters = {}
    strategies = optimization_results['strategy'].unique()

    for strat in strategies:
        strat_result = optimization_results[optimization_results['strategy'] == strat].sort_values(by='sharpe_ratio', ascending=False).iloc[0]
        # 移除 'strategy', 'sharpe_ratio', 'max_drawdown' 列
        params = strat_result.drop(['strategy', 'sharpe_ratio', 'max_drawdown']).to_dict()
        best_parameters[strat] = params

    return best_parameters

def get_latest_stock_data(symbol, start_date, end_date, count=100):
    """
    获取最新的N条股票行情数据。
    
    参数：
    - symbol: 股票代码，例如 '600519'
    - start_date: 开始日期，格式 'YYYY-MM-DD'
    - end_date: 结束日期，格式 'YYYY-MM-DD'
    - count: 获取最新的N条数据
    
    返回：
    - latest_data: 最新的N条行情数据的DataFrame
    """
    stock_data = get_stock_data(symbol, start_date, end_date)
    
    # 按日期排序
    stock_data.sort_index(inplace=True)
    
    # 获取最新的N条数据
    latest_data = stock_data.tail(count)
    
    return latest_data

def run_strategy(strategy, params, data_feed):
    """
    运行指定的策略，并返回已关闭的交易、夏普比率和最大回撤。
    
    参数：
    - strategy: 策略类
    - params: 策略参数字典
    - data_feed: Backtrader的数据源
    
    返回：
    - trades: 已关闭的交易列表
    - sharpe: 夏普比率
    - drawdown: 最大回撤
    """
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)
    cerebro.addstrategy(strategy, **params)
    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, compression=1)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    try:
        results = cerebro.run()
        strat = results[0]
        
        # 提取已关闭的交易
        trades = strat.closed_trades  # 访问策略实例的 closed_trades 列表
        
        # 提取夏普比率和最大回撤
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
        drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
        
        logging.info(f"Strategy: {strategy.__name__}, Params: {params}, Sharpe Ratio: {sharpe}, Max Drawdown: {drawdown}")
        
        return trades, sharpe, drawdown
    except Exception as e:
        logging.error(f"Backtest failed for strategy: {strategy.__name__}, Params: {params}, Error: {e}")
        return [], 0.0, 0.0

def generate_trade_signals(symbol='600519', optimization_csv='optimization_results.csv', count=100):
    """
    生成当前的交易信号，并保存到CSV文件。
    
    参数：
    - symbol: 股票代码，例如 '600519'
    - optimization_csv: 优化结果CSV文件路径
    - count: 获取最新的N条数据用于生成交易信号
    
    返回：
    - suggestions_df: 包含交易建议的DataFrame
    """
    # 加载最佳参数
    best_parameters = load_best_parameters(optimization_csv)
    logging.info("加载的最佳参数：")
    logging.info(best_parameters)
    
    # 获取最新的行情数据
    latest_stock_data = get_latest_stock_data(symbol, start_date='2020-01-01', end_date='2023-12-31', count=count)
    
    # 定义数据源类
    class AkShareData(bt.feeds.PandasData):
        params = (
            ('datetime', None),
            ('open', 'Open'),
            ('high', 'High'),
            ('low', 'Low'),
            ('close', 'Close'),
            ('volume', 'Volume'),
            ('openinterest', -1),
        )
    
    data_feed = AkShareData(dataname=latest_stock_data)
    
    # 定义策略名称与类的映射
    strategy_map = {
        'SwingStrategy': SwingStrategy,
        'BreakoutStrategy': BreakoutStrategy,
        'MeanReversionStrategy': MeanReversionStrategy,
        'MACDStrategy': MACDStrategy
    }
    
    # 记录交易建议
    trade_suggestions = []
    
    for strat_name, params in best_parameters.items():
        strategy = strategy_map.get(strat_name, None)
        if not strategy:
            logging.warning(f"策略 {strat_name} 未定义。")
            continue
        
        logging.info(f"运行策略：{strat_name}，参数：{params}")
        trades, sharpe, drawdown = run_strategy(strategy, params, data_feed)
        
        # 根据策略运行结果生成交易建议
        if trades:
            for trade in trades:
                suggestion = {
                    'strategy': strat_name,
                    'datetime': trade['datetime'],
                    'action': '买入' if trade['type'] == 'Buy' else '卖出',
                    'price': trade['price'],
                    'pnl': trade['pnl'],
                    'pnlcomm': trade['pnlcomm'],
                    'sharpe_ratio': sharpe,
                    'max_drawdown': drawdown
                }
                trade_suggestions.append(suggestion)
        else:
            # 如果没有交易信号，建议持有
            latest_date = latest_stock_data.index[-1].date()
            latest_price = latest_stock_data['Close'][-1]
            suggestion = {
                'strategy': strat_name,
                'datetime': latest_date,
                'action': '持有',
                'price': latest_price,
                'pnl': 0,
                'pnlcomm': 0,
                'sharpe_ratio': sharpe,
                'max_drawdown': drawdown
            }
            trade_suggestions.append(suggestion)
    
    # 转换为 DataFrame
    suggestions_df = pd.DataFrame(trade_suggestions)
    
    # 打印交易建议
    print("\n当前交易建议：")
    print(suggestions_df)
    logging.info("当前交易建议：")
    logging.info(suggestions_df)
    
    # 保存到CSV
    suggestions_df.to_csv('current_trade_suggestions.csv', index=False)
    logging.info("交易信号已生成并保存到 'current_trade_suggestions.csv'。")
    
    return suggestions_df

if __name__ == '__main__':
    generate_trade_signals(symbol='600519', optimization_csv='optimization_results.csv', count=100)