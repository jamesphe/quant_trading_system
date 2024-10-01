# optimize_vgt.py

import argparse
from datetime import datetime
import pandas as pd
import backtrader as bt
from data_fetch import get_us_stock_data
from strategies.chandelier_zlsma_strategy import ChandelierZlSmaStrategy
from optimizer import optimize_strategy

def main():
    # 设置参数
    parser = argparse.ArgumentParser(description='优化股票策略')
    parser.add_argument('--symbol', type=str, default='VGT', help='股票代码，默认为VGT')
    args = parser.parse_args()
    symbol = args.symbol
    start_date = '2024-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')

    # 获取美股 VGT 数据
    stock_data = get_us_stock_data(symbol, start_date, end_date)

    # 打印数据范围和样本
    print(f"数据范围: {stock_data.index.min()} 至 {stock_data.index.max()}")
    print(stock_data.head())
    print(stock_data.tail())

    # 定义数据源类
    class USStockData(bt.feeds.PandasData):
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
    data_feed = USStockData(dataname=stock_data)

    # 优化策略
    print(f'优化策略：ChandelierZlSmaStrategy for {symbol}')
    study = optimize_strategy(ChandelierZlSmaStrategy, data_feed, n_trials=100, n_jobs=1)

    best_trial = study.best_trial

    # 提取最佳参数
    best_params = {
        'length': int(best_trial.params['length']),
        'mult': round(best_trial.params['mult'], 2),
        'zlsma_length': int(best_trial.params['zlsma_length']),
        'investment_fraction': round(best_trial.params['investment_fraction'], 2),
        'max_pyramiding': int(best_trial.params['max_pyramiding']),
        'printlog': True  # 设置为True以打印日志
    }

    # 记录结果
    optimization_result = {
        'symbol': symbol,
        'strategy': 'ChandelierZlSmaStrategy',
        **best_params,
        'sharpe_ratio': round(best_trial.value * -1, 2),
    }

    print(f'最佳参数组合：{best_params}')
    print(f'最佳夏普比率：{optimization_result["sharpe_ratio"]:.2f}\n')

    # 转换为 DataFrame 并导出到 CSV
    results_df = pd.DataFrame([optimization_result])
    results_df.to_csv(f'{symbol}_ChandelierZlSmaStrategy_optimization_result.csv', index=False)

    print("优化结果已保存到 CSV 文件。")

    # 使用最佳参数进行回测
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)
    cerebro.addstrategy(ChandelierZlSmaStrategy, **best_params)
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=best_params['investment_fraction'] * 100)

    print('开始回测...')
    results = cerebro.run()
    
    # 获取策略实例
    strategy = results[0]
    
    # 打印回测结果
    print(f'最终资金: {cerebro.broker.getvalue():.2f}')
    print(f'总回报率: {(cerebro.broker.getvalue() / 2000 - 1) * 100:.2f}%')

    # 获取最后一个交易日的止损价
    last_long_stop = strategy.long_stop[0]
    last_short_stop = strategy.short_stop[0]
    last_close = strategy.data.close[0]

    print('\n当前市场情况:')
    print(f'最新收盘价: ${last_close:.2f}')
    print(f'多头止损价 (Long Stop): ${last_long_stop:.2f}')
    print(f'空头止损价 (Short Stop): ${last_short_stop:.2f}')

    # 获取当前交易建议
    current_position = strategy.position.size
    current_signal = strategy.signal[0]

    print('\n当前交易建议:')
    if current_signal > 0:
        print(f'买入信号 - 建议买入 {symbol}，当前价格: ${last_close:.2f}')
    elif current_signal < 0:
        print(f'卖出信号 - 建议卖出 {symbol}，当前价格: ${last_close:.2f}')
    else:
        print(f'持仓信号 - 建议保持当前仓位，当前价格: ${last_close:.2f}')

    print(f'\n当前持仓: {current_position} 股')

if __name__ == '__main__':
    main()