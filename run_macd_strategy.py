# run_macd_strategy.py

import backtrader as bt
import logging
from datetime import datetime
from strategies.macd_strategy import MACDStrategy  # 导入策略
from data_fetch import get_stock_data      # 导入数据获取函数

class PandasData(bt.feeds.PandasData):
    """
    自定义Pandas数据源，以匹配Backtrader的数据格式。
    """
    params = (
        ('datetime', None),
        ('open', 'Open'),
        ('high', 'High'),
        ('low', 'Low'),
        ('close', 'Close'),
        ('volume', 'Volume'),
        ('openinterest', None),
    )

if __name__ == '__main__':
    # 配置日志记录
    logging.basicConfig(
        filename='macd_strategy_optimized.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 获取股票数据
    symbol = '300687'  # 例如，贵州茅台
    start_date = '2023-01-01'
    end_date = '2024-12-31'
    
    stock_data = get_stock_data(symbol, start_date, end_date)
    
    # 检查数据是否成功获取
    if stock_data.empty:
        print(f"未能获取到股票代码 {symbol} 的数据。请检查代码和日期范围。")
        exit(1)
    
    # 打印数据的前几行和最后几行
    print("数据预览（前5行）:")
    print(stock_data.head())
    print("\n数据预览（后5行）:")
    print(stock_data.tail())
    
    # 仅保留Backtrader需要的列
    stock_data = stock_data[['Open', 'High', 'Low', 'Close', 'Volume']]
    
    # 检查是否有缺失值
    if stock_data.isnull().values.any():
        print("数据中存在缺失值，请检查数据源。")
        exit(1)
    
    # 初始化Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加策略，启用日志
    cerebro.addstrategy(MACDStrategy, printlog=True)
    
    # 将Pandas DataFrame转换为Backtrader的数据源
    data_feed = PandasData(dataname=stock_data)
    cerebro.adddata(data_feed)
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    
    # 设置佣金和滑点
    cerebro.broker.setcommission(commission=0.001)  # 0.1%佣金
    cerebro.broker.set_slippage_perc(perc=0.001)   # 0.1%的滑点
    
    # 添加夏普比率分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    
    # 运行策略
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('最终资金: %.2f' % cerebro.broker.getvalue())
    
    # 打印夏普比率
    for strat in results:
        sharpe = strat.analyzers.sharpe.get_analysis()
        if sharpe and 'sharperatio' in sharpe and sharpe['sharperatio'] is not None:
            print(f'夏普比率: {sharpe["sharperatio"]:.2f}')
        else:
            print('夏普比率无法计算')
    
    # 绘制策略结果
    #cerebro.plot()