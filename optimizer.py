# optimizer.py

import backtrader as bt
import optuna
import logging
import pandas as pd
from datetime import datetime, timedelta
import random
import numpy as np
import optuna.logging
import argparse

from data_fetch import get_stock_data, get_etf_data, get_us_stock_data
from strategies import MeanReversionStrategy, ChandelierZlSmaStrategy

# 设置日志配置
logging.basicConfig(filename='backtrader_optimizer.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# 设置固定的随机种子
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

def run_backtest(strategy, params, data_feed):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data_feed)
    cerebro.addstrategy(strategy, **params)
    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, compression=1)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    try:
        results = cerebro.run()
        strat = results[0]

        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
        
        # 计算总收益率
        total_return = strat.analyzers.returns.get_analysis()['rtot']

        signals = strat.signal.array if hasattr(strat, 'signal') else []
        last_signal = signals[-1] if len(signals) > 0 else 0

        total_trades = len(strat.trades)
        winning_trades = sum(1 for trade in strat.trades if trade.pnlcomm > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        logging.info(f"策略: {strategy.__name__}, 参数: {params}, 夏普比率: {sharpe}, 最大回撤: {drawdown}, 胜率: {win_rate}, 总收益率: {total_return}, 最后信号: {last_signal}")

        return sharpe, drawdown, win_rate, total_return, last_signal
    except Exception as e:
        logging.error(f"回测失败，策略: {strategy.__name__}, 参数: {params}, 错误: {e}")
        return 0.0, 0.0, 0.0, 0.0, 0

def objective(trial, strategy, data_feed):
    if strategy == MeanReversionStrategy:
        period = trial.suggest_int('period', 10, 30)
        devfactor = trial.suggest_float('devfactor', 1.5, 3.0)
        portion = trial.suggest_float('portion', 0.05, 0.2)
        stop_loss = trial.suggest_float('stop_loss', 0.01, 0.05)
        take_profit = trial.suggest_float('take_profit', 0.02, 0.08)
        params = {
            'period': period,
            'devfactor': devfactor,
            'portion': portion,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
    elif strategy == ChandelierZlSmaStrategy:
        period = trial.suggest_int('period', 10, 20)
        mult = trial.suggest_float('mult', 1.5, 2.5)
        investment_fraction = trial.suggest_float('investment_fraction', 0.5, 1.0)
        max_pyramiding = trial.suggest_int('max_pyramiding', 0, 3)
        params = {
            'period': period,
            'mult': mult,
            'investment_fraction': investment_fraction,
            'max_pyramiding': max_pyramiding,
            'printlog': False
        }
    else:
        params = {}

    sharpe, drawdown, win_rate, total_return, last_signal = run_backtest(strategy, params, data_feed)

    trial.set_user_attr('win_rate', win_rate)
    trial.set_user_attr('max_drawdown', drawdown)
    trial.set_user_attr('total_return', total_return)
    trial.set_user_attr('last_signal', last_signal)

    return -sharpe if sharpe else 0.0

def optimize_strategy(strategy, data_feed, n_trials=50, n_jobs=1):
    def objective_wrapper(trial):
        return objective(trial, strategy, data_feed)
    
    optuna.logging.set_verbosity(optuna.logging.ERROR)
    sampler = optuna.samplers.TPESampler(seed=RANDOM_SEED)
    study = optuna.create_study(direction='minimize', sampler=sampler)
    study.optimize(objective_wrapper, n_trials=n_trials, n_jobs=n_jobs)
    
    return study

def main():
    parser = argparse.ArgumentParser(description='股票回测优化程序')
    parser.add_argument('symbol', type=str, help='股票代码')
    parser.add_argument('--start_date', type=str, default=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'), help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default=datetime.now().strftime('%Y-%m-%d'), help='回测结束日期 (YYYY-MM-DD)')
    args = parser.parse_args()

    symbol = args.symbol
    start_date = args.start_date
    end_date = args.end_date
    
        # 获取股票数据
    if symbol.startswith(('51', '159')):  # ETF
        stock_data = get_etf_data(symbol, start_date, end_date)
    elif symbol.isdigit():  # A股
        stock_data = get_stock_data(symbol, start_date, end_date)
    else:  # 美股
        stock_data = get_us_stock_data(symbol, start_date, end_date)

    if stock_data.empty:
        print(f"股票 {symbol} 没有可用的数据进行回测。")
        return

    # 打印数据范围和样本
    # print(f"数据范围: {stock_data.index.min()} 至 {stock_data.index.max()}")
    # print(stock_data.head())
    # print(stock_data.tail())

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

    strategies = [ChandelierZlSmaStrategy]

    # 记录优化结果
    optimization_results = []

    for strat in strategies:
        strategy_name = strat.__name__
        print('\n' + '-'*50)
        print(f'策略: {strategy_name}')
        print('-'*50)
        
        study = optimize_strategy(strat, data_feed, n_trials=50, n_jobs=1)
        best_trial = study.best_trial

        if strat == MeanReversionStrategy:
            best_params = {
                'period': int(best_trial.params['period']),
                'devfactor': round(best_trial.params['devfactor'], 2),
                'portion': round(best_trial.params['portion'], 2),
                'stop_loss': round(best_trial.params['stop_loss'], 2),
                'take_profit': round(best_trial.params['take_profit'], 2)
            }
        elif strat == ChandelierZlSmaStrategy:
            best_params = {
                'period': int(best_trial.params['period']),
                'mult': round(best_trial.params['mult'], 2),
                'investment_fraction': round(best_trial.params['investment_fraction'], 2),
                'max_pyramiding': int(best_trial.params['max_pyramiding'])
            }

        print('\n最优参数:')
        for param, value in best_params.items():
            print(f'  {param:<12}: {value}')
        
        print('\n回测结果:')
        print(f'  夏普比率    : {best_trial.value * -1:.2f}')
        print(f'  最大回撤    : {best_trial.user_attrs["max_drawdown"]:.2f}%')
        print(f'  胜率        : {best_trial.user_attrs["win_rate"]*100:.2f}%')
        print(f'  总收益率    : {best_trial.user_attrs["total_return"]*100:.2f}%')
        print(f'  最后信号    : {best_trial.user_attrs["last_signal"]:.2f}')
        print('-'*50)

        optimization_results.append({
            'symbol': symbol,
            'strategy': strategy_name,
            **best_params,
            'sharpe_ratio': round(best_trial.value * -1, 2),
            'max_drawdown': round(best_trial.user_attrs['max_drawdown'], 2),
            'win_rate': round(best_trial.user_attrs['win_rate'], 2),
            'total_return': round(best_trial.user_attrs['total_return'], 4),
            'last_signal': best_trial.user_attrs['last_signal']
        })

    # 转换为 DataFrame 便于分析
    results_df = pd.DataFrame(optimization_results)
    
    # 对浮点数列进行四舍五入
    float_columns = results_df.select_dtypes(include=['float64']).columns
    results_df[float_columns] = results_df[float_columns].round(2)

    print("优化结果汇总：")
    print(results_df)

    # 导出优化结果到 CSV
    results_df.to_csv(f'results/{symbol}_optimization_results.csv', index=False)

if __name__ == '__main__':
    main()
