# test_best_parameters.py

import backtrader as bt
import pandas as pd
import logging
import os

from data_fetch import get_stock_data
from strategies.swing_strategy import SwingStrategy
from strategies.macd_strategy import MACDStrategy  # 确保正确导入
# 导入其他策略类如 BreakoutStrategy, MeanReversionStrategy

# 设置日志配置
logging.basicConfig(
    filename='test_best_parameters.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

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

def main():
    # 设定股票代码和日期范围
    symbol = '600519'
    start_date = '2022-01-01'
    end_date = '2023-12-31'
    
    # 获取数据
    stock_data = get_stock_data(symbol, start_date, end_date)
    
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
    
    data_feed = AkShareData(dataname=stock_data)
    
    # 定义策略与参数
    strategies = {
        'SwingStrategy': {
            'strategy': SwingStrategy,
            'params': {
                'ma_short': 10,
                'ma_long': 30,
                'rsi_low': 30,
                'rsi_high': 70,
                'printlog': True
            }
        },
        'MACDStrategy': {
            'strategy': MACDStrategy,
            'params': {
                'macd1': 12,
                'macd2': 26,
                'signal': 9,
                'stake': 1,
                'printlog': True
            }
        },
        # 添加其他策略及其最佳参数
    }
    
    # 运行并记录策略
    for strat_name, strat_info in strategies.items():
        strategy = strat_info['strategy']
        params = strat_info['params']
        trades, sharpe, drawdown = run_strategy(strategy, params, data_feed)
        
        print(f"策略: {strat_name}")
        print(f"参数: {params}")
        print(f"夏普比率: {sharpe}")
        print(f"最大回撤: {drawdown}")
        print(f"交易记录: {trades}\n")

if __name__ == '__main__':
    main()