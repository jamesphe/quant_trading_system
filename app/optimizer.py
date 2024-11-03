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

# 股票清单
STOCK_LIST = [
    {'code': '601919', 'name': '中远海控'},
    {'code': '600789', 'name': '鲁抗医药'},
    {'code': '603799', 'name': '华友钴业'},
    {'code': '603129', 'name': '春风动力'},
    {'code': '600141', 'name': '兴发集团'},
]

# 设置日志配置
logging.basicConfig(
    filename='backtrader_optimizer.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# 设置固定的随机种子
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def run_backtest(strategy, params, data_feed):
    """运行回测并返回结果"""
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data_feed)
    cerebro.addstrategy(strategy, **params)
    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)
    cerebro.broker.setcommission(commission=0.001)
    
    # 添加分析器
    cerebro.addanalyzer(
        bt.analyzers.SharpeRatio,
        _name='sharpe',
        timeframe=bt.TimeFrame.Days,
        compression=1
    )
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    try:
        results = cerebro.run()
        strat = results[0]

        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = (strat.analyzers.drawdown.get_analysis()
                   .get('max', {}).get('drawdown', 0))
        
        # 计算总收益率
        total_return = strat.analyzers.returns.get_analysis()['rtot']

        signals = strat.signal.array if hasattr(strat, 'signal') else []
        last_signal = signals[-1] if len(signals) > 0 else 0

        total_trades = len(strat.trades)
        winning_trades = sum(1 for trade in strat.trades if trade.pnlcomm > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        log_msg = (
            f"策略: {strategy.__name__}, 参数: {params}, "
            f"夏普比率: {sharpe}, 最大回撤: {drawdown}, "
            f"胜率: {win_rate}, 总收益率: {total_return}, "
            f"最后信号: {last_signal}"
        )
        logging.info(log_msg)

        return sharpe, drawdown, win_rate, total_return, last_signal
    except Exception as e:
        logging.error(
            f"回测失败，策略: {strategy.__name__}, 参数: {params}, 错误: {e}"
        )
        return 0.0, 0.0, 0.0, 0.0, 0


def objective(trial, strategy, data_feed):
    """优化目标函数"""
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
        inv_fraction = trial.suggest_float('investment_fraction', 0.5, 1.0)
        max_pyramiding = trial.suggest_int('max_pyramiding', 0, 3)
        params = {
            'period': period,
            'mult': mult,
            'investment_fraction': inv_fraction,
            'max_pyramiding': max_pyramiding,
            'printlog': False
        }
    else:
        params = {}

    results = run_backtest(strategy, params, data_feed)
    sharpe, drawdown, win_rate, total_return, last_signal = results

    trial.set_user_attr('win_rate', win_rate)
    trial.set_user_attr('max_drawdown', drawdown)
    trial.set_user_attr('total_return', total_return)
    trial.set_user_attr('last_signal', last_signal)

    return -sharpe if sharpe else 0.0


def optimize_strategy(strategy, data_feed, n_trials=50, n_jobs=1):
    """优化策略参数"""
    def objective_wrapper(trial):
        return objective(trial, strategy, data_feed)
    
    optuna.logging.set_verbosity(optuna.logging.ERROR)
    sampler = optuna.samplers.TPESampler(seed=RANDOM_SEED)
    study = optuna.create_study(direction='minimize', sampler=sampler)
    study.optimize(objective_wrapper, n_trials=n_trials, n_jobs=n_jobs)
    
    return study


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票回测优化程序')
    parser.add_argument(
        '--symbol',
        type=str,
        help='单只股票代码，不指定则批量优化股票列表'
    )
    parser.add_argument(
        '--start_date',
        type=str,
        default=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        help='回测开始日期 (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end_date',
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help='回测结束日期 (YYYY-MM-DD)'
    )
    args = parser.parse_args()

    start_date = args.start_date
    end_date = args.end_date
    
    # 存储所有股票的优化结果
    all_optimization_results = []
    
    # 确定要处理的股票列表
    if args.symbol:
        stocks_to_process = [{'code': args.symbol, 'name': '单只股票'}]
    else:
        stocks_to_process = STOCK_LIST
        print(f"将对 {len(STOCK_LIST)} 只股票进行批量优化...")

    # 遍历处理每只股票
    for stock in stocks_to_process:
        symbol = stock['code']
        print(f"\n{'='*60}")
        print(f"正在优化 {stock['name']}({symbol})")
        print(f"{'='*60}")
        
        # 获取股票数据
        if symbol.startswith(('51', '159')):
            stock_data = get_etf_data(symbol, start_date, end_date)
        elif symbol.isdigit():
            stock_data = get_stock_data(symbol, start_date, end_date)
        else:
            stock_data = get_us_stock_data(symbol, start_date, end_date)

        if stock_data.empty:
            print(f"股票 {symbol} 没有可用的数据进行回测。")
            continue

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
        strategies = [ChandelierZlSmaStrategy]
        optimization_results = []

        for strat in strategies:
            strategy_name = strat.__name__
            print(f'\n策略: {strategy_name}')
            print('-'*50)
            
            study = optimize_strategy(strat, data_feed, n_trials=50, n_jobs=1)
            best_trial = study.best_trial

            # 设置最优参数
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
                    'investment_fraction':
                        round(best_trial.params['investment_fraction'], 2),
                    'max_pyramiding': int(best_trial.params['max_pyramiding'])
                }

            # 打印结果
            print('\n最优参数:')
            for param, value in best_params.items():
                print(f'  {param:<12}: {value}')
            
            print('\n回测结果:')
            print(f'  夏普比率    : {best_trial.value * -1:.2f}')
            print(f'  最大回撤    : '
                  f'{best_trial.user_attrs["max_drawdown"]:.2f}%')
            print(f'  胜率        : '
                  f'{best_trial.user_attrs["win_rate"]*100:.2f}%')
            print(f'  总收益率    : '
                  f'{best_trial.user_attrs["total_return"]*100:.2f}%')
            print(f'  最后信号    : '
                  f'{best_trial.user_attrs["last_signal"]:.2f}')

            result = {
                'symbol': symbol,
                'name': stock['name'],
                'strategy': strategy_name,
                **best_params,
                'sharpe_ratio': round(best_trial.value * -1, 2),
                'max_drawdown':
                    round(best_trial.user_attrs['max_drawdown'], 2),
                'win_rate': round(best_trial.user_attrs['win_rate'], 2),
                'total_return':
                    round(best_trial.user_attrs['total_return'], 4),
                'last_signal': best_trial.user_attrs['last_signal']
            }
            optimization_results.append(result)
            all_optimization_results.append(result)

        # 保存当前股票的结果
        stock_df = pd.DataFrame(optimization_results)
        stock_df.to_csv(
            f'results/{symbol}_optimization_results.csv',
            index=False
        )

    # 处理所有股票的汇总结果
    if all_optimization_results:
        all_results_df = pd.DataFrame(all_optimization_results)
        
        # 对浮点数列进行四舍五入
        float_cols = all_results_df.select_dtypes(include=['float64']).columns
        all_results_df[float_cols] = all_results_df[float_cols].round(2)

        # 设置pandas显示选项
        pd.set_option('display.unicode.ambiguous_as_wide', True)
        pd.set_option('display.unicode.east_asian_width', True)
        pd.set_option('display.width', 180)
        pd.set_option('display.max_columns', None)
        
        print("\n" + "=" * 100)
        print("优化结果汇总表")
        print("=" * 100)
        
        # 1. 性能指标汇总
        performance_summary = all_results_df.groupby(['name', 'symbol']).agg({
            'sharpe_ratio': 'first',
            'max_drawdown': 'first',
            'win_rate': 'first',
            'total_return': 'first'
        }).round(2)
        
        performance_summary.columns = ['夏普比率', '最大回撤(%)', '胜率(%)', '总收益率(%)']
        performance_summary['胜率(%)'] = performance_summary['胜率(%)'] * 100
        performance_summary['总收益率(%)'] = performance_summary['总收益率(%)'] * 100
        
        print("\n【性能指标】")
        print("-" * 80)
        print(performance_summary.to_string(
            float_format=lambda x: '{:,.2f}'.format(x),
            justify='center'
        ))
        
        # 2. 最优参数汇总
        params_summary = all_results_df.groupby(['name', 'symbol']).agg({
            'period': 'first',
            'mult': 'first',
            'investment_fraction': 'first',
            'max_pyramiding': 'first'
        }).round(2)
        
        params_summary.columns = ['周期', '倍数', '投资比例', '金字塔等级']
        
        print("\n【最优参数】")
        print("-" * 80)
        print(params_summary.to_string(
            float_format=lambda x: '{:,.2f}'.format(x),
            justify='center'
        ))
        
        print("=" * 100)
        
        # 3. 统计摘要
        print("\n统计摘要：")
        print("-" * 40)
        print(f"最高夏普比率: {performance_summary['夏普比率'].max():.2f} "
              f"({performance_summary['夏普比率'].idxmax()[0]})")
        print(f"最高胜率: {performance_summary['胜率(%)'].max():.1f}% "
              f"({performance_summary['胜率(%)'].idxmax()[0]})")
        print(f"最高收益率: {performance_summary['总收益率(%)'].max():.1f}% "
              f"({performance_summary['总收益率(%)'].idxmax()[0]})")
        print(f"平均夏普比率: {performance_summary['夏普比率'].mean():.2f}")
        print(f"平均胜率: {performance_summary['胜率(%)'].mean():.1f}%")
        print(f"平均收益率: {performance_summary['总收益率(%)'].mean():.1f}%")
        print("-" * 40)

        # 保存汇总结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        all_results_df.to_csv(
            f'results/batch_optimization_results_{timestamp}.csv',
            index=False
        )


if __name__ == '__main__':
    main()
