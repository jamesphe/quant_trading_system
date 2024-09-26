# optimizer.py

import backtrader as bt
import optuna
import logging
import pandas as pd
import os

from data_fetch import get_stock_data
from strategies import SwingStrategy, BreakoutStrategy, MeanReversionStrategy, MACDStrategy

# 设置日志配置
logging.basicConfig(filename='backtrader_optimizer.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

def run_backtest(strategy, params, data_feed):
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

        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)

        logging.info(f"Strategy: {strategy.__name__}, Params: {params}, Sharpe Ratio: {sharpe}, Max Drawdown: {drawdown}")

        return sharpe, drawdown
    except Exception as e:
        logging.error(f"Backtest failed for strategy: {strategy.__name__}, Params: {params}, Error: {e}")
        return 0.0, 0.0

def objective(trial, strategy, data_feed):
    # 根据策略类型定义参数空间
    if strategy == SwingStrategy:
        ma_short = trial.suggest_int('ma_short', 5, 15)
        ma_long = trial.suggest_int('ma_long', 20, 40)
        rsi_low = trial.suggest_int('rsi_low', 20, 40)
        rsi_high = trial.suggest_int('rsi_high', 60, 80)
        params = {
            'ma_short': ma_short,
            'ma_long': ma_long,
            'rsi_low': rsi_low,
            'rsi_high': rsi_high,
            'printlog': False  # 可选参数
        }
    elif strategy == MACDStrategy:
        macd1 = trial.suggest_int('macd1', 10, 20)
        macd2 = trial.suggest_int('macd2', 25, 35)
        signal = trial.suggest_int('signal', 5, 15)
        params = {
            'macd1': macd1,
            'macd2': macd2,
            'signal': signal,
            'stake': 1,  # 固定为1
            'printlog': False
        }
    elif strategy == BreakoutStrategy:
        # 定义 BreakoutStrategy 的参数空间
        period = trial.suggest_int('period', 10, 50)
        params = {
            'period': period
        }
    elif strategy == MeanReversionStrategy:
        # 定义 MeanReversionStrategy 的参数空间
        period = trial.suggest_int('period', 10, 30)
        devfactor = trial.suggest_float('devfactor', 1.5, 3.0)
        params = {
            'period': period,
            'devfactor': devfactor
        }
    else:
        params = {}

    sharpe, drawdown = run_backtest(strategy, params, data_feed)

    # Optuna 试图最小化目标函数，因此返回负的夏普比率
    return -sharpe if sharpe else 0.0

def optimize_strategy(strategy, data_feed, n_trials=50, n_jobs=1):
    def objective_wrapper(trial):
        return objective(trial, strategy, data_feed)
    
    study = optuna.create_study(direction='minimize')
    study.optimize(objective_wrapper, n_trials=n_trials, n_jobs=n_jobs)
    
    return study

def main():
    # 设置股票代码和日期范围
    symbol = '300687'  # 贵州茅台
    start_date = '2023-01-01'
    end_date = '2024-09-20'

    # 获取数据
    stock_data = get_stock_data(symbol, start_date, end_date)

    # 打印数据范围和样本
    print(f"数据范围: {stock_data.index.min()} 至 {stock_data.index.max()}")
    print(stock_data.head())
    print(stock_data.tail())

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

    # 实例化数据源
    data_feed = AkShareData(dataname=stock_data)

    # 定义策略列表
    strategies = [MACDStrategy]  # 您可以添加其他策略

    # 记录优化结果
    optimization_results = []

    for strat in strategies:
        strategy_name = strat.__name__
        print(f'优化策略：{strategy_name}')
        study = optimize_strategy(strat, data_feed, n_trials=50, n_jobs=1)  # 可以根据需要调整 n_trials 和 n_jobs

        best_trial = study.best_trial

        # 根据策略类型提取最佳参数
        if strat == SwingStrategy:
            best_params = {
                'ma_short': best_trial.params['ma_short'],
                'ma_long': best_trial.params['ma_long'],
                'rsi_low': best_trial.params['rsi_low'],
                'rsi_high': best_trial.params['rsi_high'],
                'printlog': False
            }
        elif strat == MACDStrategy:
            best_params = {
                'macd1': best_trial.params['macd1'],
                'macd2': best_trial.params['macd2'],
                'signal': best_trial.params['signal'],
                'stake': 1,
                'printlog': False
            }
        elif strat == BreakoutStrategy:
            best_params = {
                'period': best_trial.params['period']
            }
        elif strat == MeanReversionStrategy:
            best_params = {
                'period': best_trial.params['period'],
                'devfactor': best_trial.params['devfactor']
            }
        else:
            best_params = {}

        # 记录结果
        optimization_results.append({
            'strategy': strategy_name,
            **best_params,
            'sharpe_ratio': best_trial.value * -1,  # 恢复正值
            'max_drawdown': 0  # 可以扩展以记录实际的回撤
        })

        print(f'最佳参数组合：{best_params}')
        print(f'最佳夏普比率：{best_trial.value * -1:.2f}\n')

    # 转换为 DataFrame 便于分析
    results_df = pd.DataFrame(optimization_results)
    print("优化结果汇总：")
    print(results_df)

    # 导出优化结果到 CSV
    results_df.to_csv('optimization_results.csv', index=False)

if __name__ == '__main__':
    main()