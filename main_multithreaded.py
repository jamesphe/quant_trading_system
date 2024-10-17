# main_multithreaded.py

from data_fetch import get_a_share_list, get_stock_data
import backtrader as bt
import argparse
from datetime import datetime, timedelta
import pandas as pd
import os
import concurrent.futures

# 导入策略
from strategies.chandelier_zlsma_strategy import ChandelierZlSmaStrategy

class AccountValue(bt.Observer):
    lines = ('value',)
    
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()

def process_stock(stock_code, start_date, end_date, printlog):
    """
    处理单只股票，运行策略并记录买入信号。
    返回买入信号字典或None。
    """
    buy_signals = []
    # 获取数据
    stock_data = get_stock_data(stock_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    if stock_data.empty:
        return stock_code, buy_signals

    # 初始化 Cerebro 引擎
    cerebro = bt.Cerebro()

    # 定义数据源类
    class PandasData(bt.feeds.PandasData):
        params = (
            ('datetime', None),
            ('open', 'Open'),
            ('high', 'High'),
            ('low', 'Low'),
            ('close', 'Close'),
            ('volume', 'Volume'),
            ('openinterest', -1),
            # ('pct_change', 'Pct_change'),  # 如果需要，可以包含涨跌幅
        )

    # 创建数据源
    data_feed = PandasData(dataname=stock_data)

    # 添加数据到 Cerebro
    cerebro.adddata(data_feed)

    # 添加策略，并传递相关参数
    cerebro.addstrategy(
        ChandelierZlSmaStrategy,
        length=14,
        mult=2,
        use_close=True,
        zlsma_length=14,
        printlog=printlog,
        investment_fraction=0.8,  # 每次交易使用可用资金的比例
        max_pyramiding=2          # 允许最多加仓2次
    )

    # 设置初始资金
    cerebro.broker.setcash(100000.0)

    # 移除固定大小的 Sizer，让策略控制持仓大小
    # 如果您希望使用不同的 Sizer，可以在这里进行设置
    # 例如，使用百分比 Sizer：
    # cerebro.addsizer(bt.sizers.PercentSizer, percents=50)
    # 这里我们不添加 Sizer，让策略内部决定买入数量

    # 设置佣金
    cerebro.broker.setcommission(commission=0.001)  # 佣金率为千分之一

    # 添加账户价值观察器
    cerebro.addobserver(AccountValue)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                        timeframe=bt.TimeFrame.Days, compression=1)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # 添加 Value 观察器（显示账户价值变化）
    cerebro.addobserver(bt.observers.Value)

    # 运行回测
    try:
        results = cerebro.run()
    except Exception as e:
        print(f"回测运行失败，股票: {stock_code}, 错误: {e}")
        return stock_code, buy_signals

    strat_result = results[0]

    # 获取策略实例的买入信号
    buy_signals = getattr(strat_result, 'buy_signals', [])

    if buy_signals:
        print(f"股票 {stock_code} 有买入信号")  # 调试信息
        print(f"买入信号列表: {buy_signals}")  # 调试信息
        # 检查是否有买入信号在最新交易日
        latest_date = stock_data.index[-1].date()
        print(f"最新交易日: {latest_date}")  # 调试信息
        latest_buy_signals = [
            signal for signal in buy_signals if signal['Date'] == latest_date
        ]
        print(f"最新交易日的买入信号: {latest_buy_signals}")  # 调试信息
        if latest_buy_signals:
            # 假设每只股票在同一日期只有一个买入信号
            buy_signals_dict = {
                'Date': latest_buy_signals[0]['Date'],
                'Buy Price': latest_buy_signals[0]['Buy Price']
            }
            print(f"股票 {stock_code} 产生买入信号: {buy_signals_dict}")  # 调试信息
            return stock_code, buy_signals_dict
    else:
        print(f"股票 {stock_code} 没有买入信号")  # 调试信息

    return stock_code, None

def main_multithreaded(start_date, end_date, printlog=False):
    # 从当前目录下的all_strategy_results.csv文件中获取股票清单
    stock_info = pd.read_csv('all_strategy_results.csv')
    if stock_info.empty:
        print("未能获取股票清单。")
        return

    symbols = stock_info['股票代码'].tolist()

    buy_signals_dict = {}

    # 使用 ThreadPoolExecutor 进行并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有股票的处理任务
        futures = {executor.submit(process_stock, stock_code, start_date, end_date, printlog): stock_code for stock_code in symbols}
        for future in concurrent.futures.as_completed(futures):
            stock_code = futures[future]
            try:
                code, signal = future.result()
                if signal:
                    buy_signals_dict[code] = signal
                    print(f"股票 {code} 在最新交易日产生了买入信号。")
                else:
                    print(f"股票 {code} 在最新交易日未产生任何买入信号。")
            except Exception as e:
                print(f"处理股票 {stock_code} 时发生异常: {e}")

    # 输出买入信号结果
    if buy_signals_dict:
        # 创建一个输出DataFrame
        output_data = []
        for stock_code, signal in buy_signals_dict.items():
            stock_name = stock_info[stock_info['code'] == stock_code]['name'].values[0]
            output_data.append({
                'Stock Code': stock_code,
                'Stock Name': stock_name,
                'Date': signal['Date'],
                'Buy Price': signal['Buy Price']
            })
        output_df = pd.DataFrame(output_data)
        # 保存到Excel文件
        output_filename = 'buy_signals_latest_day.xlsx'
        output_df.to_excel(output_filename, index=False)
        print(f"\n筛选完成，有买入信号的股票已保存到 {output_filename}")
    else:
        print("\n筛选完成，没有任何股票在最新交易日产生买入信号。")

if __name__ == '__main__':
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='A股 Chandelier ZLSMA 策略最新交易日买入信号筛选程序（多线程版）')
    parser.add_argument('--months', type=int, default=48, help='分析时长（月数）')
    parser.add_argument('--printlog', action='store_true', help='是否打印策略日志')
    args = parser.parse_args()

    # 设置日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.months * 30)

    # 运行主函数（多线程版）
    main_multithreaded(start_date, end_date, printlog=args.printlog)
