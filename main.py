# main.py

from data_fetch import get_stock_data
import backtrader as bt
import logging
import argparse
from datetime import datetime, timedelta

# 仅导入需要使用的策略
from strategies import ChandelierZlSmaStrategy

# 设置日志配置
logging.basicConfig(
    filename='backtrader.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

class AccountValue(bt.Observer):
    lines = ('value',)
    
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()

if __name__ == '__main__':
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='股票回测程序')
    parser.add_argument('symbol', type=str, help='股票代码')
    parser.add_argument('months', type=int, help='分析时长（月数）')
    args = parser.parse_args()

    # 设置股票代码和日期范围
    symbol = args.symbol
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.months * 30)

    # 获取数据
    stock_data = get_stock_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    # 确保数据按日期排序
    stock_data = stock_data.sort_index()

    # 打印数据范围
    print(f"\n{'='*50}")
    print(f"股票代码: {symbol}")
    print(f"数据范围: {stock_data.index.min().date()} 至 {stock_data.index.max().date()}")
    print(f"{'='*50}\n")
    
    # 定义策略列表
    strategies = [ChandelierZlSmaStrategy]

    # 记录策略结果
    strategy_results = []

    for strat in strategies:
        # 初始化新的 Cerebro 引擎
        cerebro = bt.Cerebro()

        # 定义数据源类
        class AkShareData(bt.feeds.PandasData):
            params = (
                ('length', 14),         # ATR 和 Chandelier Exit 的周期
                ('mult', 2),            # ATR 的倍数
                ('use_close', True),    # 是否使用收盘价计算最高/最低
                ('zlsma_length', 20),   # ZLSMA 的周期
                ('printlog', False),    # 是否打印日志
            )

        # 为每个策略创建独立的数据源实例
        data_feed = AkShareData(dataname=stock_data)

        # 添加数据到 Cerebro
        cerebro.adddata(data_feed)

        # 添加策略，传递相关参数
        cerebro.addstrategy(
            strat,
            length=14,
            mult=2.0,
            use_close=True,
            printlog=True,
            zlsma_length=20,
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

        # 打印当前策略名称
        print(f'运行策略：{strat.__name__}')

        # 运行回测
        results = cerebro.run()
        strat_result = results[0]

        # 获取回测结束时的资金
        final_value = cerebro.broker.getvalue()

        # 获取夏普比率
        sharpe_analysis = strat_result.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_analysis.get('sharperatio', None)

        # 获取最大回撤
        drawdown_analysis = strat_result.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown_analysis.max.drawdown  # 以百分比表示

        # 获取交易分析结果
        trade_analysis = strat_result.analyzers.trades.get_analysis()

        # 初始化变量
        total_trades = 0
        won_trades = 0
        win_rate = 0.0

        # 安全地获取交易数据
        if trade_analysis:
            total_trades = trade_analysis.get('total', {}).get('closed', 0)
            won_trades = trade_analysis.get('won', {}).get('total', 0)
            win_rate = won_trades / total_trades if total_trades > 0 else 0

        print("----------------------------------------")
        print(f"策略 {strat_result.__class__.__name__} 完成回测")
        print(f"总交易次数: {total_trades}")
        print(f"最终资金: {final_value:.2f}")
        print(f"夏普比率: {sharpe_ratio:.2f}" if sharpe_ratio else "夏普比率: N/A")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"胜率    : {win_rate * 100:.2f}%" if total_trades > 0 else "胜率: 0.00%")
        initial_value = cerebro.broker.startingcash
        cumulative_return = (final_value - initial_value) / initial_value * 100
        print(f"累计收益率: {cumulative_return:.2f}%")
        print("----------------------------------------")

        # 使用这个替代方法
        closed_trades = trades_analyzer.total.closed

        # 然后遍历并打印交易记录
        for trade in closed_trades:
            print(f"开仓时间: {trade.dtopen}, 平仓时间: {trade.dtclose}, 收益: {trade.pnl}")

        # 记录结果
        strategy_results.append({
            'strategy': strat_result.__class__.__name__,
            'final_value': final_value,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': total_trades
        })
        
        # 创建一个新的图表，使用绿色代表上涨的蜡烛图
        fig = cerebro.plot(style='candlestick', volume=False, barup='green', bardown='red')[0][0]
        
        # 获取策略实例
        strat = cerebro.runstrats[0][0]
        
        # 获取止损线数据
        long_stop = strat.long_stop.array
        
        # 在主图上添加止损线
        ax1 = fig.axes[0]
        ax1.plot(cerebro.datas[0].datetime.plot(), long_stop, color='red', label='止损线')
        
        # 添加图例
        ax1.legend()
        
        # 创建一个浮窗
        annotation = ax1.annotate('', xy=(0, 0), xytext=(20, 20),
                                  textcoords='offset points',
                                  bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                                  arrowprops=dict(arrowstyle='->'))
        annotation.set_visible(False)
        
        # 添加鼠标右键点击事件处理
        def on_right_click(event):
            if event.inaxes == ax1 and event.button == 3:  # 3 表示鼠标右键
                x = event.xdata
                y = event.ydata
                date = matplotlib.dates.num2date(x).strftime('%Y-%m-%d')
                price = y
                
                # 获取当前日期对应的数据
                idx = cerebro.datas[0].datetime.plot().get_loc(date)
                open_price = cerebro.datas[0].open[idx]
                high_price = cerebro.datas[0].high[idx]
                low_price = cerebro.datas[0].low[idx]
                close_price = cerebro.datas[0].close[idx]
                volume = cerebro.datas[0].volume[idx]
                
                # 获取止损线的值
                stop_loss = strat.long_stop[idx]
                
                text = (f'日期: {date}\n价格: {price:.2f}\n'
                        f'开盘: {open_price:.2f}\n最高: {high_price:.2f}\n'
                        f'最低: {low_price:.2f}\n收盘: {close_price:.2f}\n'
                        f'成交量: {volume:.0f}\n止损线: {stop_loss:.2f}')
                
                annotation.xy = (x, y)
                annotation.set_text(text)
                annotation.set_visible(True)
                fig.canvas.draw()
        
        fig.canvas.mpl_connect('button_press_event', on_right_click)
        
        # 显示图表
        #plt.show()

    # 打印所有策略的结果
    print("\n策略回测结果总览：")
    for res in strategy_results:
        print(f"\n{'='*40}")
        print(f"策略名称: {res['strategy']}")
        print(f"{'-'*40}")
        print(f"最终资金: {res['final_value']:.2f}")
        print(f"夏普比率: {res['sharpe_ratio'] if res['sharpe_ratio'] is not None else 'N/A'}")
        print(f"最大回撤: {res['max_drawdown']:.2f}%")
        print(f"胜率    : {res['win_rate']:.2%}")
        print(f"总交易次数: {res['total_trades']}")
        print(f"{'='*40}")
