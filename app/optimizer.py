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
import importlib.util
import os

from data_fetch import get_stock_data, get_etf_data, get_us_stock_data
from strategies import (
    MeanReversionStrategy, 
    ChandelierZlSmaStrategy,
    BollingerRsiMacdStrategy
)

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
    """
    运行回测并返回优化结果

    参数：
    - strategy: 策略类
    - params: 策略参数字典
    - data_feed: 数据源
    """
    # 初始化 Cerebro 引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(strategy, **params)
    
    # 添加数据
    cerebro.adddata(data_feed)
    
    # 设置初始资金
    initial_cash = 50000.0
    cerebro.broker.setcash(initial_cash)
    
    # 设置交易佣金（0.1%）
    cerebro.broker.setcommission(commission=0.001)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, 
        _name='sharpe',
        timeframe=bt.TimeFrame.Days, 
        compression=1,
        riskfreerate=0.02,  # 设置年化无风险利率为2%
        annualize=True,     # 年化处理
        factor=252          # 设置年交易日数
    )
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')  # 添加收益率分析器
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # 运行回测
    results = cerebro.run()
    strat = results[0]
    
    # 获取最新信号
    signals = strat.signal.array if hasattr(strat, 'signal') else []
    last_signal = signals[-1] if signals else 0
    
    # 获取分析结果
    sharpe_ratio = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    returns_analysis = strat.analyzers.returns.get_analysis()
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    trades_analysis = strat.analyzers.trades.get_analysis()
    
    # 计算各项指标
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_cash) / initial_cash
    annual_return = returns_analysis.get('rnorm100', 0) / 100
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0)
    
    # 计算交易相关指标
    total_trades = trades_analysis.get('total', {}).get('total', 0)
    won_trades = trades_analysis.get('won', {}).get('total', 0)
    win_rate = (won_trades / total_trades) if total_trades > 0 else 0
    
    # 安全地获取盈利和亏损的PNL
    won_pnl = float(trades_analysis.get('won', {}).get('pnl', {}).get('total', 0))
    lost_pnl = float(trades_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
    
    # 计算盈亏比
    profit_factor = abs(won_pnl / lost_pnl) if lost_pnl != 0 else 0
    
    # 安全地获取平均交易收益和最大盈亏
    avg_trade = float(trades_analysis.get('pnl', {}).get('net', {}).get('average', 0))
    largest_win = float(trades_analysis.get('won', {}).get('pnl', {}).get('max', 0))
    largest_loss = float(trades_analysis.get('lost', {}).get('pnl', {}).get('max', 0))
    
    # 返回优化结果
    return {
        'final_value': final_value,
        'total_return': total_return,
        'annual_return': annual_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'params': params,
        'won_trades': won_trades,
        'lost_trades': total_trades - won_trades if total_trades > 0 else 0,
        'initial_cash': initial_cash,
        'profit_factor': profit_factor,
        'avg_trade': avg_trade,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'last_signal': last_signal,
    }


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
        mult = trial.suggest_float('mult', 1.5, 2.5, step=0.1)
        inv_fraction = trial.suggest_float('investment_fraction', 0.5, 1.0)
        max_pyramiding = trial.suggest_int('max_pyramiding', 0, 3)
        params = {
            'period': period,
            'mult': mult,
            'investment_fraction': inv_fraction,
            'max_pyramiding': max_pyramiding,
            'printlog': False
        }
    elif strategy == BollingerRsiMacdStrategy:
        # 布林带参数
        bb_period = trial.suggest_int('bb_period', 15, 25)
        bb_devfactor = trial.suggest_float('bb_devfactor', 1.5, 2.5)
        
        # RSI参数
        rsi_period = trial.suggest_int('rsi_period', 10, 20)
        rsi_overbought = trial.suggest_int('rsi_overbought', 60, 75)
        rsi_oversold = trial.suggest_int('rsi_oversold', 25, 40)
        
        # MACD参数
        macd_fast = trial.suggest_int('macd_fast', 8, 16)
        macd_slow = trial.suggest_int('macd_slow', 20, 30)
        macd_signal = trial.suggest_int('macd_signal', 7, 12)
        
        # 资金管理参数
        investment_fraction = trial.suggest_float('investment_fraction', 0.5, 0.9)
        
        params = {
            'bb_period': bb_period,
            'bb_devfactor': bb_devfactor,
            'rsi_period': rsi_period,
            'rsi_overbought': rsi_overbought,
            'rsi_oversold': rsi_oversold,
            'macd_fast': macd_fast,
            'macd_slow': macd_slow,
            'macd_signal': macd_signal,
            'investment_fraction': investment_fraction,
            'min_trade_unit': 100,
            'printlog': False
        }
    else:
        params = {}

    results = run_backtest(strategy, params, data_feed)
    
    # 从结果字典中获取需要的值
    trial.set_user_attr('win_rate', results['win_rate'])
    trial.set_user_attr('max_drawdown', results['max_drawdown'])
    trial.set_user_attr('total_return', results['total_return'])
    trial.set_user_attr('last_signal', results['last_signal'])
    
    # 返回负的夏普率作为优化目标（因为optuna默认最小化目标）
    return -results['sharpe_ratio'] if results['sharpe_ratio'] else 0.0


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
    parser.add_argument(
        '--strategy',
        type=str,
        default='ChandelierZlSmaStrategy',
        choices=['ChandelierZlSmaStrategy', 'BollingerRsiMacdStrategy', 'MeanReversionStrategy'],
        help='选择要使用的策略'
    )
    args = parser.parse_args()

    # 策略映射字典
    strategy_mapping = {
        'ChandelierZlSmaStrategy': ChandelierZlSmaStrategy,
        'BollingerRsiMacdStrategy': BollingerRsiMacdStrategy,
        'MeanReversionStrategy': MeanReversionStrategy
    }

    # 获取选择的策略
    selected_strategy = strategy_mapping[args.strategy]
    
    start_date = args.start_date
    end_date = args.end_date
    
    # 存储所有股票的优化结果
    all_optimization_results = []
    
    # 确定要处理的股票列表
    if args.symbol:
        stocks_to_process = [{'code': args.symbol, 'name': '单只股票'}]
    else:
        # 修改导入逻辑
        stock_list_date = args.end_date.replace('-', '')
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            module_path = os.path.join(
                current_dir,
                f'../stock_pool/stock_list_{stock_list_date}.py'
            )
            
            stocks_to_process = STOCK_LIST  # 设置默认值
            
            if os.path.exists(module_path):
                try:
                    spec = importlib.util.spec_from_file_location(
                        "stock_list_module",
                        module_path
                    )
                    stock_list_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(stock_list_module)
                    
                    if not hasattr(stock_list_module, 'STOCK_LIST'):
                        print("导入的模块中没有找到 STOCK_LIST，使用默认列表")
                    else:
                        # 处理不同的数据格式
                        imported_list = stock_list_module.STOCK_LIST
                        if isinstance(imported_list, dict):
                            # 如果是字典格式，转换为列表格式
                            stocks_to_process = [
                                {'code': code, 'name': name}
                                for code, name in imported_list.items()
                            ]
                        elif isinstance(imported_list, list):
                            if imported_list and isinstance(imported_list[0], str):
                                # 如果是字符串列表
                                stocks_to_process = [
                                    {'code': code, 'name': code} 
                                    for code in imported_list
                                ]
                            else:
                                # 如果已经是字典列表格式
                                stocks_to_process = imported_list
                            print(f"成功处理列表格式的股票列表，包含 {len(stocks_to_process)} 只股票")
                        else:
                            print(f"未知的 STOCK_LIST 格式: {type(imported_list)}，使用默认列表")
                            
                except Exception as e:
                    print(f"处理导入的股票列表时出错: {str(e)}")
                    print(f"错误类型: {type(e)}")
                    print("使用默认股票列表...")
            else:
                print(f"未找到股票列表文件: {module_path}，使用默认列表")
                
        except Exception as e:
            print(f"导入股票列表时出错: {str(e)}")
            print(f"错误类型: {type(e)}")
            print("使用默认股票列表...")
        
        print(f"最终使用的股票列表: {stocks_to_process}")
        print(f"将对 {len(stocks_to_process)} 只股票进行批量优化...")

    # 遍历处理每只股票
    for stock in stocks_to_process:
        if isinstance(stock, str):
            # 如果是字符串，转换为字典格式
            symbol = stock
            stock = {'code': symbol, 'name': symbol}
        else:
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
        strategies = [selected_strategy]
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
            elif strat == BollingerRsiMacdStrategy:
                best_params = {
                    'bb_period': int(best_trial.params['bb_period']),
                    'bb_devfactor': round(best_trial.params['bb_devfactor'], 2),
                    'rsi_period': int(best_trial.params['rsi_period']),
                    'rsi_overbought': int(best_trial.params['rsi_overbought']),
                    'rsi_oversold': int(best_trial.params['rsi_oversold']),
                    'macd_fast': int(best_trial.params['macd_fast']),
                    'macd_slow': int(best_trial.params['macd_slow']),
                    'macd_signal': int(best_trial.params['macd_signal']),
                    'investment_fraction': round(
                        best_trial.params['investment_fraction'], 2
                    )
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
        for strategy_name in set(result['strategy'] for result in optimization_results):
            # 为每个策略筛选结果
            strategy_results = [
                r for r in optimization_results if r['strategy'] == strategy_name
            ]
            strategy_df = pd.DataFrame(strategy_results)
            
            # 创建 results 目录（如果不存在）
            os.makedirs('results', exist_ok=True)
            
            # 生成文件名
            filename = f'results/{symbol}_{strategy_name}_optimization_results.csv'
            
            # 保存到 CSV 文件
            strategy_df.to_csv(filename, index=False)
            print(f"已保存 {symbol} 的 {strategy_name} 优化结果到: {filename}")

        # 同时保存一个包含所有策略的汇总文件
        stock_df = pd.DataFrame(optimization_results)
        stock_df.to_csv(
            f'results/{symbol}_all_strategies_results.csv',
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
        }).round(4)
        
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
        params_columns = {
            'ChandelierZlSmaStrategy': ['period', 'mult', 'investment_fraction', 'max_pyramiding'],
            'BollingerRsiMacdStrategy': ['bb_period', 'bb_devfactor', 'rsi_period', 'investment_fraction']
        }

        for strategy_name, columns in params_columns.items():
            strategy_results = all_results_df[
                all_results_df['strategy'] == strategy_name
            ]
            if not strategy_results.empty:
                params_summary = strategy_results.groupby(['name', 'symbol']).agg({
                    col: 'first' for col in columns
                }).round(2)
                
                column_names = {
                    'bb_period': '布林周期',
                    'bb_devfactor': '标准差倍数',
                    'rsi_period': 'RSI周期',
                    'investment_fraction': '投资比例',
                    'period': '周期',
                    'mult': '倍数',
                    'max_pyramiding': '金字塔等级'
                }
                
                params_summary.columns = [
                    column_names.get(col, col) for col in columns
                ]
                
                print(f"\n【{strategy_name}最优参数】")
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
