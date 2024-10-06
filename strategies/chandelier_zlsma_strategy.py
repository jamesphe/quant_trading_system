# chandelier_zlsma_strategy.py

# -*- coding: utf-8 -*-

import backtrader as bt
import numpy as np
import pandas as pd
from data_fetch import get_a_share_list, get_stock_data

class LinearRegression(bt.Indicator):
    """
    自定义线性回归指标。
    计算给定周期内的线性回归预测值。
    """
    lines = ('linreg',)
    params = (
        ('period', 32),  # 回归周期
    )

    def __init__(self):
        # 确保有足够的数据进行回归计算
        self.addminperiod(self.p.period)

    def next(self):
        # 获取当前周期的索引（0为最新）
        y = np.array([self.data[i] for i in range(-self.p.period + 1, 1)])
        x = np.arange(-self.p.period + 1, 1)
        # 计算线性回归系数（斜率和截距）
        slope, intercept = np.polyfit(x, y, 1)
        # 预测当前周期的y值（x = 0）
        linreg_value = intercept
        self.lines.linreg[0] = linreg_value
        
class ZLSMA(bt.Indicator):
    """
    Zero Lag Smoothed Moving Average (ZLSMA) 指标实现。
    计算方法基于两次指数移动平均（EMA）的差值。
    """
    lines = ('zlsma',)
    params = (
        ('period', 20),  # 计算周期
        ('lag', 0),      # 延迟期数
    )

    def __init__(self):
        # 使用内置的 linreg_indicator 或自定义线性回归
        self.lsma = LinearRegression(self.data, period=self.p.period)
        self.lsma2 = LinearRegression(self.lsma, period=self.p.period)
        self.zlsma = self.lsma + (self.lsma - self.lsma2)
        
        if self.p.lag > 0:
            self.zlsma = self.zlsma(-self.p.lag)
        
        self.lines.zlsma = self.zlsma

class ChandelierZlSmaStrategy(bt.Strategy):
    """
    基于 Chandelier Exit 和 ZLSMA 的交易策略。
    """
    lines = ('signal',)  # 添加这行

    params = (
        ('length', 14),         # ATR 和 Chandelier Exit 的周期
        ('mult', 2),            # ATR 的倍数
        ('use_close', True),    # 是否使用收盘价计算最高/最低
        ('zlsma_length', 14),   # ZLSMA 的周期
        ('printlog', False),    # 是否打印日志
        ('investment_fraction', 0.8), # 每次交易使用可用资金的比例
        ('max_pyramiding', 0),        # 允许的最大加仓次数
        ('min_trade_unit', 100),  # 添加新参数,设置最小交易单位
    )

    def log(self, txt, dt=None):
        """ 日志函数，用于输出策略执行信息 """
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def __init__(self):
        # 计算 ATR 指标
        self.atr = bt.ind.ATR(self.datas[0], period=self.p.length)


        # 根据 use_close 参数决定使用收盘价还是高低价计算最高/最低
        if self.p.use_close:
            self.highest = bt.ind.Highest(self.datas[0].close, period=self.p.length)
            self.lowest = bt.ind.Lowest(self.datas[0].close, period=self.p.length)
        else:
            self.highest = bt.ind.Highest(self.datas[0].high, period=self.p.length)
            self.lowest = bt.ind.Lowest(self.datas[0].low, period=self.p.length)

        # 计算 Long_Stop 和 Short_Stop
        self.long_stop = self.highest - (self.p.mult * self.atr)
        self.long_stop_prev = self.long_stop(-1)
        self.long_stop = bt.If(
            self.data.close(-1) > self.long_stop_prev,
            bt.Max(self.long_stop, self.long_stop_prev),
            self.long_stop
        )
        
        self.chandelier_exit_long = self.long_stop

        self.short_stop = self.lowest + (self.p.mult * self.atr)
        self.short_stop_prev = self.short_stop(-1)
        self.short_stop = bt.If(
            self.data.close(-1) < self.short_stop_prev,
            bt.Min(self.short_stop, self.short_stop_prev),
            self.short_stop
        )
        
        self.chandelier_exit_short = self.short_stop

        # 初始化方向变量
        self.direction = 0  # 1 表示多头，-1 表示空头，0 表示中立

        # 计算 ZLSMA 指标
        self.zlsma = ZLSMA(self.datas[0].close, period=self.p.zlsma_length)

        # 初始化买入信号变量
        self.buy_signal = False
        
        # 设置允许的最大加仓次数
        self.max_pyramiding = self.params.max_pyramiding
        self.current_pyramiding = 0  # 当前加仓次数

        self.trades = []  # Initialize the trades list

        self.signal = self.lines.signal  # 如果需要，可以添加这行

    def next(self):
        """
        每个时间步执行的逻辑。
        """
        # 打印当前的日期、收盘价和ZLSMA价格
        #current_date = self.datas[0].datetime.date(0)
        #self.log(f'当前日期: {current_date}, 收盘价: {self.datas[0].close[0]:.2f}, ZLSMA价格: {self.zlsma[0]:.2f}')
        # 当前收盘价
        current_close = self.datas[0].close[0]

        # 前一周期的收盘价
        prev_close = self.datas[0].close[-1]

        # 前一周期的 Long_Stop 和 Short_Stop
        prev_long_stop = self.long_stop[-1]
        prev_short_stop = self.short_stop[-1]
        
        # 当前持仓数量
        current_positions = self.position.size

        # 计算每次交易的资金量,考虑加仓次数
        remaining_pyramiding = self.params.max_pyramiding - self.current_pyramiding
        available_cash = self.broker.getcash() * self.params.investment_fraction
        available_cash_per_trade = available_cash / max(1, remaining_pyramiding)
        stake = int(available_cash_per_trade / current_close)
        # 确保交易数量是最小交易单位的倍数
        stake = (stake // self.params.min_trade_unit) * self.params.min_trade_unit
        
        # 添加调试代码
        self.log(f'调试信息:')
        self.log(f'  剩余加仓次数: {remaining_pyramiding}')
        self.log(f'  可用资金: {available_cash:.2f}')
        self.log(f'  每次交易可用资金: {available_cash_per_trade:.2f}')
        self.log(f'  计算得到的交易数量: {stake}')
        self.log(f'  当前收盘价: {current_close:.2f}')
        self.log(f'  最小交易单位: {self.params.min_trade_unit}')

        # 计算当前方向
        
        # 计算当前方向
        if current_close > prev_short_stop:
            current_direction = 1  # 转为多头
            self.log(f'日期: {self.datas[0].datetime.date(0)}, 当前方向: 多头, 原因: 收盘价 {current_close:.2f} 高于 Short_Stop {prev_short_stop:.2f}')
        elif current_close < prev_long_stop:
            current_direction = -1  # 转为空头
            self.log(f'日期: {self.datas[0].datetime.date(0)}, 当前方向: 空头, 原因: 收盘价 {current_close:.2f} 低于 Long_Stop {prev_long_stop:.2f}')
        else:
            current_direction = self.direction  # 维持原有方向
            direction_name = '多头' if self.direction == 1 else '空头' if self.direction == -1 else '中立'
            self.log(f'日期: {self.datas[0].datetime.date(0)}, 当前方向: {direction_name}, '
                     f'原因: 维持原有方向 (收盘价 {current_close:.2f} 介于 '
                     f'Long_Stop {prev_long_stop:.2f} 和 Short_Stop {prev_short_stop:.2f} 之间)')

        # 检查方向是否发生变化
        # 打印方向和价格信息
        #self.log(f'当前方向: {self.direction}, 新方向: {current_direction}, '
        #         f'当前收盘价: {current_close:.2f}, ZLSMA当前值: {self.zlsma[0]:.2f}')
        direction_change = False
        self.buy_signal = False
        if (self.direction == -1 and current_direction == 1):
            # 方向从空头转为多头，进一步检查收盘价是否高于 ZLSMA
            if current_close > self.zlsma[0]:
                self.buy_signal = True
                self.signal[0] = 1
                direction_change = True
                self.log(f'买入信号产生: 方向从空头转为多头，且收盘价 {current_close:.2f} 高于 ZLSMA {self.zlsma[0]:.2f}')
        elif (self.direction == 1 and current_direction == -1):
            # 方向从多头转为空头，可以设置卖出信号
            self.buy_signal = False
            self.signal[0] = -1
            direction_change = True
            self.log(f'卖出信号产生: 方向从多头转为空头。当前收盘价 {current_close:.2f} 低于 Long_Stop {prev_long_stop:.2f}')
        elif (self.direction == 1 and current_direction == 1):
            if self.zlsma[-1] < self.zlsma[0]:
                self.buy_signal = True
                self.signal[0] = 1
                self.log(f'买入信号产生: 多头趋势中，ZLSMA上升（前值: {self.zlsma[-1]:.2f}, 当前值: {self.zlsma[0]:.2f}）')
        else:
            self.buy_signal = False
            self.signal[0] = 0
            self.log('无交易信号')

        # 打印当前信息
        #current_date = self.datas[0].datetime.date(0)
        #self.log(f'当前日期: {current_date}, 持仓: {current_positions}, 方向: {self.direction}, '
        #         f'方向变化: {"是" if direction_change else "否"}, '
        #         f'买入信息: {"是" if self.buy_signal else "否"}, '
        #         f'当前收盘价: {current_close:.2f}, ZLSMA当前值: {self.zlsma[0]:.2f}')
        # 执行买入信号
        if not self.position:
            if self.buy_signal:
                self.log(f'买入信号 - 价格: {current_close:.2f}, 首次建仓, 买入数量: {stake}')
                self.buy(size=stake)
                self.current_pyramiding = 0
        else:
            # 根据策略逻辑决定何时卖出
            if self.direction == 1:
                if direction_change:
                    self.log('卖出信号触发：方向变化，执行卖出操作')
                    self.sell(size=current_positions)
                    self.current_pyramiding = 0
                elif self.zlsma[-1] > self.zlsma[0] and current_close < self.zlsma[0] and self.zlsma[-2] > self.zlsma[-1]:
                    self.log('卖出信号触发：ZLSMA下降且当前价格低于ZLSMA（ZLSMA前值: {:.2f}, 当前值: {:.2f}，当前价格: {:.2f}），执行卖出操作'.format(self.zlsma[-1], self.zlsma[0], current_close))
                    self.sell(size=current_positions)
                    self.current_pyramiding = 0
                elif current_close > self.position.price * 1.03:
                    if self.current_pyramiding < self.max_pyramiding:
                        self.buy(size=stake)
                        self.current_pyramiding += 1
                        self.log(f'加仓信号 - 价格: {current_close:.2f}, 加仓次数: {self.current_pyramiding}')
     

        # 更新方向
        self.direction = current_direction

    def notify_order(self, order):
        """
        订单通知，用于跟踪订单状态。
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/被接受，尚未执行
            self.log(f'订单状态: {"已提交" if order.status == order.Submitted else "已接受"}')
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买单执行，价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.log(f'当前持仓: {self.position.size}')
            elif order.issell():
                self.log(f'卖单执行，价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.log(f'当前持仓: {self.position.size}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单状态: {"已取消" if order.status == order.Canceled else "保证金不足" if order.status == order.Margin else "被拒绝"}')
            self.log(f'订单详情: {order}')

        # 添加调试信息
        self.log(f'当前账户价值: {self.broker.getvalue():.2f}')
        self.log(f'当前现金: {self.broker.getcash():.2f}')
        self.log(f'当前ZLSMA值: {self.zlsma[0]:.2f}')
        self.log(f'当前Chandelier Exit Long: {self.chandelier_exit_long[0]:.2f}')
        self.log(f'当前Chandelier Exit Short: {self.chandelier_exit_short[0]:.2f}')

    def notify_trade(self, trade):
        """
        交易通知，用于跟踪交易结果。
        """
        if not trade.isclosed:
            return

        self.log(f'交易结束，毛利: {trade.pnl:.2f}, 净利: {trade.pnlcomm:.2f}')
        self.trades.append(trade)  # Record closed trades

def run_backtest(symbol, start_date, end_date, printlog=False, **strategy_params):
    """
    运行回测

    参数：
    - symbol: 股票代码，例如 '600519'
    - start_date: 回测开始日期，格式 'YYYY-MM-DD'
    - end_date: 回测结束日期，格式 'YYYY-MM-DD'
    - printlog: 是否打印日志
    - **strategy_params: 策略参数，用于初始化策略
    """
    # 获取股票数据
    data_df = get_stock_data(symbol, start_date, end_date)

    if data_df.empty:
        print(f"股票 {symbol} 没有可用的数据进行回测。")
        return

    # 初始化 Cerebro 引擎
    cerebro = bt.Cerebro()

    # 添加策略，并传入策略参数
    cerebro.addstrategy(ChandelierZlSmaStrategy, printlog=printlog, **strategy_params)

    # 将 Pandas DataFrame 转换为 Backtrader 数据格式
    data_bt = bt.feeds.PandasData(
        dataname=data_df,
        fromdate=pd.to_datetime(start_date),
        todate=pd.to_datetime(end_date),
        plot=False
    )
    cerebro.adddata(data_bt, name=symbol)

    # 设置初始资金
    initial_cash = 20000.0
    cerebro.broker.setcash(initial_cash)

    # 设置交易佣金（例如 0.1%）
    cerebro.broker.setcommission(commission=0.001)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                        timeframe=bt.TimeFrame.Days, compression=1)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    # 打印初始资金
    print(f'初始资金: {initial_cash:.2f}')

    # 运行策略，并获取策略实例列表
    results = cerebro.run()

    # 获取第一个策略实例
    strat = results[0]

    # 打印最终资金
    final_cash = cerebro.broker.getvalue()
    total_profit = sum(trade.pnlcomm for trade in strat.trades if trade.isclosed)
    roi = (total_profit / initial_cash) * 100

    print(f'最终资金: {final_cash:.2f}')
    print(f'总收益: {total_profit:.2f}')
    print(f'收益率: {roi:.2f}%')

    # 计算夏普比率
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe_analysis.get('sharperatio', None)
    if sharpe_ratio is not None:
        print(f'夏普比率: {sharpe_ratio:.2f}')
    else:
        print('夏普比率无法计算。')

    # 计算最大回撤
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', None)
    if max_drawdown is not None:
        print(f'最大回撤: {max_drawdown:.2f}%')
    else:
        print('最大回撤无法计算。')
        
    # 打印交易记录
    print("\n交易记录:")
    for i, trade in enumerate(strat.trades):
        print(f"交易 {i+1}:")
        print(f"  开仓日期: {bt.num2date(trade.dtopen)}")
        print(f"  开仓价格: {trade.price:.2f}")
        print(f"  开仓数量: {trade.size}")
        print(f"  平仓日期: {bt.num2date(trade.dtclose)}")
        # print(f"  平仓价格: {trade.barclose:.2f}")
        print(f"  交易盈亏: {trade.pnl:.2f}")
        print(f"  交易佣金: {trade.commission:.2f}")
        print(f"  净盈亏: {trade.pnlcomm:.2f}")
        print()

    # 可选：绘制结果
    # cerebro.plot(style='candlestick', volume=False, barup='green', bardown='red')[0][0]

if __name__ == '__main__':
    # 获取A股列表
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='股票回测程序')
    parser.add_argument('symbol', type=str, help='股票代码')
    parser.add_argument('--start_date', type=str, default='2024-05-01', help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2024-09-28', help='回测结束日期 (YYYY-MM-DD)')
    args = parser.parse_args()

    print(f"开始回测股票: {args.symbol}")
    

    # 运行回测
    run_backtest(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        length=10,
        mult=1.5,
        zlsma_length=10,
        investment_fraction=0.55,
        max_pyramiding=1,
        min_trade_unit=100,  # 添加新参数
        printlog=False
    )