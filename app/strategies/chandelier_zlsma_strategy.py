# chandelier_zlsma_strategy.py

# -*- coding: utf-8 -*-

import backtrader as bt
import numpy as np
import pandas as pd
from data_fetch import get_a_share_list, get_stock_data
from datetime import datetime, timedelta

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
    计算方法基于两次线性回归的差值，消除滞后。
    """
    lines = ('zlsma',)
    params = (
        ('period', 20),  # 计算周期
    )

    def __init__(self):
        # 计算两次线性回归指标
        self.lsma = LinearRegression(self.data, period=self.p.period)
        self.lsma2 = LinearRegression(self.lsma, period=self.p.period)
        
        # 计算 ZLSMA 值
        self.zlsma = self.lsma + (self.lsma - self.lsma2)
        
        # 将计算结果赋值给指标线
        self.lines.zlsma = self.zlsma

class ChandelierZlSmaStrategy(bt.Strategy):
    """
    基于 Chandelier Exit 和 ZLSMA 的交易策略。
    """
    lines = ('signal',)

    params = (
        ('period', 14),         # Chandelier Exit 和 ZLSMA 的统一周期
        ('mult', 2),            # ATR 的倍数
        ('use_close', True),    # 是否使用收盘价计算最高/最低
        ('printlog', True),     # 是否打印日志
        ('investment_fraction', 0.8), # 每次交易使用可用资金的比例
        ('max_pyramiding', 0),        # 允许的最大加仓次数
        ('min_trade_unit', 100),      # 最小交易单位
    )

    def log(self, txt, dt=None):
        """ 日志函数，用于输出策略执行信息 """
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def __init__(self):
        # 计算 ATR 指标
        self.atr = bt.ind.ATR(self.datas[0], period=self.p.period)

        # 根据 use_close 参数决定使用收盘价还是高低价计算最高/最低
        if self.p.use_close:
            self.highest = bt.ind.Highest(self.datas[0].close, period=self.p.period)
            self.lowest = bt.ind.Lowest(self.datas[0].close, period=self.p.period)
        else:
            self.highest = bt.ind.Highest(self.datas[0].high, period=self.p.period)
            self.lowest = bt.ind.Lowest(self.datas[0].low, period=self.p.period)

        # 计算 Long_Stop 和 Short_Stop
        self.long_stop = self.highest - (self.p.mult * self.atr)
        self.long_stop_prev = self.long_stop(-1)
        
        self.long_stop = bt.If(
            self.data.close(0) > self.long_stop_prev,
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
        self.reason = ''

        # 计算 ZLSMA 指标，移除了 lag 参数
        self.zlsma = ZLSMA(self.datas[0].close, period=self.p.period)

        # 初始化买入信号变量
        self.buy_signal = False
        
        # 设置允许的最大加仓次数
        self.max_pyramiding = self.params.max_pyramiding
        self.current_pyramiding = 0  # 当前加仓次数

        self.trades = []  # 初始化交易记录列表

        self.signal = self.lines.signal  # 如果需要，可以添加这行

    def next(self):
        """
        每个时间步执行的逻辑。
        """
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

        # 方向判断
        if current_close < prev_long_stop:
            current_direction = -1
            direction_name = '空头'
            self.reason = f'收盘价 {current_close:.2f} 低于多头止损价 {prev_long_stop:.2f}'
        elif current_close > prev_short_stop:
            current_direction = 1 if current_close > prev_long_stop else 2
            direction_name = '多头' if current_direction == 1 else '建仓预警'
            self.reason = f'收盘价 {current_close:.2f} 高于 空头止损价 {prev_short_stop:.2f}'
            if current_direction == 1:
                self.reason += f' 和 多头止损价 {prev_long_stop:.2f}'
        else:
            current_direction = self.direction
            direction_map = {1: '多头', -1: '空头', 2: '建仓预警', -2: '清仓预警', 0: '中立'}
            direction_name = direction_map.get(self.direction, '中立')
            self.reason = (f'收盘价 {current_close:.2f} 介于 多头止损价 {prev_long_stop:.2f} '
                     f'和 空头止损价 {prev_short_stop:.2f} 之间, 维持原有方向')

        # 记录日志
        self.log(f'日期: {self.datas[0].datetime.date(0)}, 当前方向: {direction_name}, 原因: {self.reason}')

        # 检查方向是否发生变化
        direction_change = False
        self.buy_signal = False

        if self.direction != current_direction:
            direction_change = True
            if current_direction == 1:  # 转为多头
                if current_close > self.zlsma[0]:
                    self.buy_signal = True
                    self.signal[0] = 1
                    self.log(
                        f'建仓信号: 方向转多头，收盘价{current_close:.2f} > '
                        f'ZLSMA {self.zlsma[0]:.2f}'
                    )
                else:
                    self.signal[0] = 0
                    self.log('建仓信号: 方向转多头，但价格未高于ZLSMA，无交易')
            elif current_direction == -1:  # 转为空头
                self.buy_signal = False
                self.signal[0] = -1
                self.log(
                    f'清仓信号: 转空头，价格{current_close:.2f} < '
                    f'止损价{prev_long_stop:.2f}'
                )
            elif current_direction == 2:  # 建仓预警
                self.buy_signal = False
                self.signal[0] = 3
                self.log(
                    f'建仓预警: 价格{current_close:.2f} > 空头止损价 {prev_short_stop:.2f}'
                )
            elif current_direction == -2:  # 减仓预警
                self.buy_signal = False
                self.signal[0] = -3
                self.log(
                    f'减仓预警: 价格{current_close:.2f} < 多头止损价 {prev_long_stop:.2f}'
                )
        elif self.direction == 1 and current_direction == 1:  # 保持多头
            if self.zlsma[-1] < self.zlsma[0]:  # ZLSMA上升
                self.buy_signal = True
                if not self.position:
                    self.signal[0] = 1
                    self.log(
                        f'建仓信号: 多头趋势，ZLSMA上升 '
                        f'({self.zlsma[-1]:.2f}->{self.zlsma[0]:.2f})'
                    )
                else:
                    self.signal[0] = 2
                    self.log(
                        f'加仓信号: 多头趋势，ZLSMA上升 '
                        f'({self.zlsma[-1]:.2f}->{self.zlsma[0]:.2f})'
                    )
            else:
                self.signal[0] = -2
                self.log('减仓预警: 多头趋势，但ZLSMA未上升')
        elif self.direction == -1 and current_direction == -1:  # 保持空头
            self.signal[0] = -1
            self.log('清仓信号: 持续空头')
            if self.position:
                self.buy_signal = False
                self.log('清仓信号: 持续空头状态')
        elif self.direction == 2 and current_direction == 2:  # 保持建仓预警
            self.signal[0] = 2
            self.log(
                f'建仓预警: 价格{current_close:.2f} > '
                f'空头止损价{prev_short_stop:.2f}'
            )
        elif self.direction == -2 and current_direction == -2:  # 保持减仓预警
            self.signal[0] = -3
            self.log(
                f'减仓预警: 价格{current_close:.2f} < '
                f'多头止损价{prev_long_stop:.2f}'
            )
        else:
            self.signal[0] = 0
            self.log('无交易信号')

        # 执行交易
        if not self.position:
            if self.buy_signal:
                self.log(f'买入信号 - 价格: {current_close:.2f}, 首次建仓, 买入数量: {stake}')
                self.buy(size=stake)
                self.current_pyramiding = 0
        else:
            if self.direction == 1:
                if direction_change:
                    self.log('**卖出信号触发**：方向变化，执行卖出操作')
                    self.sell(size=current_positions)
                    self.current_pyramiding = 0
                elif self.zlsma[-1] > self.zlsma[0] and current_close < self.zlsma[0] and self.zlsma[-2] > self.zlsma[-1]:
                    self.log('**卖出信号触发**：ZLSMA下降且当前价格低于ZLSMA，执行卖出操作')
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
        # 检查是否已存在相同的交易
        for i, existing_trade in enumerate(self.trades):
            if existing_trade.ref == trade.ref:
                # 如果找到相同的交易引用,则更新它
                self.trades[i] = trade
                if trade.isclosed:
                    self.log(f'交易结束，毛利: {trade.pnl:.2f}, 净利: {trade.pnlcomm:.2f}')
                return
                
        # 如果是新交易则添加到列表
        self.trades.append(trade)
        if trade.isclosed:
            self.log(f'交易结束，毛利: {trade.pnl:.2f}, 净利: {trade.pnlcomm:.2f}')

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
    initial_cash = 50000.0
    cerebro.broker.setcash(initial_cash)

    # 设置交易佣金（例如 0.1%）
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

    # 打印初始资金
    print(f'初始资金: {initial_cash:.2f}')

    # 运行策略，并获取策略实例列表
    results = cerebro.run()

    # 获取第一个策略实例
    strat = results[0]
    
    # 获取分析器结果
    sharpe_ratio = strat.analyzers.sharpe.get_analysis()['sharperatio']
    returns_analysis = strat.analyzers.returns.get_analysis()
    
    # 计算年化收益率
    annual_return = returns_analysis.get('rnorm100', 0)  # 年化收益率（百分比）
    
    # 打印最终资金和收益信息
    final_cash = cerebro.broker.getvalue()
    total_profit = sum(trade.pnlcomm for trade in strat.trades if trade.isclosed)
    roi = (total_profit / initial_cash) * 100

    print(f'最终资金: {final_cash:.2f}')
    print(f'总收益: {total_profit:.2f}')
    print(f'收益率: {roi:.2f}%')
    print(f'年化收益率: {annual_return:.2f}%')
    
    print(f"交易总数: {len(strat.trades)}")
    print(f"盈利交易数: {len([trade for trade in strat.trades if trade.pnl > 0])}")
    
    # 计算胜率
    if len(strat.trades) > 0:  # 添加防御性检查
        win_rate = (len([trade for trade in strat.trades if trade.pnl > 0]) / len(strat.trades)) * 100
        print(f'胜率: {win_rate:.2f}%')
    else:
        print('无交易记录，无法计算胜率')

    # 打印夏普比率
    if sharpe_ratio is not None:
        print(f'夏普比率: {sharpe_ratio:.2f}')
    else:
        print('夏普比率无法计算')

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

def calculate_annualized_sharpe(returns, risk_free=0.02):
    """
    计算年化夏普比率
    returns: 日收益率列表
    risk_free: 年化无风险利率
    """
    returns = np.array(returns)
    if len(returns) == 0:
        return 0
        
    # 计算日化无风险利率
    daily_rf = (1 + risk_free) ** (1/252) - 1
    
    # 计算超额收益
    excess_returns = returns - daily_rf
    
    # 计算年化超额收益均值
    annual_excess_return = np.mean(excess_returns) * 252
    
    # 计算年化波动率（使用总体标准差）
    annual_volatility = np.std(excess_returns, ddof=0) * np.sqrt(252)
    
    # 避免除以零
    if annual_volatility == 0:
        return 0
        
    # 计算夏普比率
    sharpe = annual_excess_return / annual_volatility
    
    return sharpe

if __name__ == '__main__':
    # 获取A股列表
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='股票回测程序')
    parser.add_argument('symbol', type=str, help='股票代码')
    parser.add_argument('--start_date', type=str, 
                       default=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
                       help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str,
                       default=datetime.now().strftime('%Y-%m-%d'),
                       help='回测结束日期 (YYYY-MM-DD)')
    args = parser.parse_args()

    print(f"开始回测股票: {args.symbol}")

    # 运行回测
    run_backtest(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        period=14,  # 使用统一的周期参数
        mult=1.5,
        investment_fraction=0.55,
        max_pyramiding=1,
        min_trade_unit=100,
        printlog=False
    )