# -*- coding: utf-8 -*-

import backtrader as bt
import numpy as np
import pandas as pd


class BollingerRsiMacdStrategy(bt.Strategy):
    """
    结合布林带、RSI和MACD的交易策略。
    
    指标参数：
    - 布林带：20周期，2倍标准差
    - RSI：14周期，超买65，超卖35
    - MACD：快线12，慢线26，信号线9
    """
    
    # 添加signal作为lines
    lines = ('signal',)
    
    params = (
        ('bb_period', 20),      # 布林带周期
        ('bb_devfactor', 2),    # 布林带标准差倍数
        ('rsi_period', 14),     # RSI周期
        ('rsi_overbought', 65),   # RSI超买阈值
        ('rsi_oversold', 35),    # RSI超卖阈值
        ('macd_fast', 12),      # MACD快线周期
        ('macd_slow', 26),      # MACD慢线周期
        ('macd_signal', 9),     # MACD信号线周期
        ('printlog', True),     # 是否打印日志
        ('investment_fraction', 0.8),  # 每次交易使用可用资金的比例
        ('min_trade_unit', 100),      # 最小交易单位
    )

    def log(self, txt, dt=None):
        """日志函数"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def __init__(self):
        # 初始化指标
        # 布林带
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_devfactor
        )
        
        # RSI
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )
        
        # MACD
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        # 用于追踪交叉
        self.rsi_cross_up = bt.indicators.CrossUp(
            self.rsi, self.params.rsi_oversold
        )
        self.rsi_cross_down = bt.indicators.CrossDown(
            self.rsi, self.params.rsi_overbought
        )
        self.macd_cross_up = bt.indicators.CrossUp(
            self.macd.macd, self.macd.signal
        )
        self.macd_cross_down = bt.indicators.CrossDown(
            self.macd.macd, self.macd.signal
        )
        
        # 交易状态
        self.order = None
        self.trades = []  # 交易记录
        
        # 添加调试标志
        self.debug_count = 0
        print("\n策略初始化完成，开始运行回测...")
        print("初始参数设置:")
        print(f"RSI超买/超卖阈值: {self.params.rsi_overbought}/{self.params.rsi_oversold}")
        print(f"布林带周期/标准差: {self.params.bb_period}/{self.params.bb_devfactor}")
        print(f"MACD参数(快/慢/信号): {self.params.macd_fast}/{self.params.macd_slow}/{self.params.macd_signal}")
        print(f"投资比例/最小交易单位: {self.params.investment_fraction}/{self.params.min_trade_unit}")
        print("-------------------")
        
        # 不再需要单独初始化signal，因为已经定义为lines
        self.reason = ""  # 添加reason属性用于记录交易原因

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行: 价格={order.executed.price:.2f}, '
                    f'成本={order.executed.value:.2f}, '
                    f'手续费={order.executed.comm:.2f}'
                )
            else:
                self.log(
                    f'卖出执行: 价格={order.executed.price:.2f}, '
                    f'成本={order.executed.value:.2f}, '
                    f'手续费={order.executed.comm:.2f}'
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        self.order = None

    def notify_trade(self, trade):
        """交易状态通知"""
        if trade.isclosed:
            self.log(
                f'交易利润, 毛利润={trade.pnl:.2f}, '
                f'净利润={trade.pnlcomm:.2f}'
            )
            
            # 直接存储 Trade 对象而不是字典
            self.trades.append(trade)

    def next(self):
        """策略核心逻辑"""
        if self.order:
            return

        # 重置信号
        self.lines.signal[0] = 0
        self.reason = "无交易信号，当前市场趋势不明确。"
        
        # 每20个交易日打印一次当前市场状况
        self.debug_count += 1
        if self.debug_count % 20 == 0:
            print("\n当前市场状况:")
            print(f"日期: {self.data.datetime.date(0)}")
            print(f"收盘价: {self.data.close[0]:.2f}")
            print(f"RSI值: {self.rsi[0]:.2f}")
            print(f"布林带上轨/中轨/下轨: {self.boll.lines.top[0]:.2f}/{self.boll.lines.mid[0]:.2f}/{self.boll.lines.bot[0]:.2f}")
            print(f"MACD: {self.macd.macd[0]:.2f}, Signal: {self.macd.signal[0]:.2f}")
            print(f"当前现金: {self.broker.getcash():.2f}")
            print(f"当前持仓: {self.position.size if self.position else 0}")
            print("-------------------")

        # 当前价格
        current_close = self.data.close[0]
        
        # 计算交易数量并打印详情
        available_cash = self.broker.getcash() * self.params.investment_fraction
        stake = int(available_cash / current_close)
        stake = (stake // self.params.min_trade_unit) * self.params.min_trade_unit
        
        if stake < self.params.min_trade_unit:
            if self.debug_count % 20 == 0:
                print(f"可用资金不足，无法交易。需要: {self.params.min_trade_unit * current_close:.2f}, 当前可用: {available_cash:.2f}")
            return

        # 没有持仓时寻找入场机会
        if not self.position:
            # 检查各个买入条件并打印
            rsi_buy = self.rsi[0] < self.params.rsi_oversold
            boll_buy = current_close < self.boll.lines.bot[0]
            macd_buy = self.macd_cross_up[0]
            
            if self.debug_count % 20 == 0:
                print("\n买入条件检查:")
                print(f"RSI条件({self.rsi[0]:.2f} < {self.params.rsi_oversold}): {rsi_buy}")
                print(f"布林带条件({current_close:.2f} < {self.boll.lines.bot[0]:.2f}): {boll_buy}")
                print(f"MACD金叉: {macd_buy}")

            should_buy = rsi_buy or boll_buy or macd_buy
                
            if should_buy:
                if rsi_buy:
                    self.lines.signal[0] = 1
                    self.reason = "RSI超卖且MACD金叉，价格突破布林带下轨。"
                elif boll_buy:
                    self.lines.signal[0] = 2
                    self.reason = "趋势向上，价格在布林带中轨上方。"
                self.order = self.buy(size=stake)

        # 有持仓时寻找出场机会
        else:
            # 检查各个卖出条件并打印
            rsi_sell = self.rsi[0] > self.params.rsi_overbought
            boll_sell = current_close > self.boll.lines.top[0]
            macd_sell = self.macd_cross_down[0]
            
            if self.debug_count % 20 == 0:
                print("\n卖出条件检查:")
                print(f"RSI条件({self.rsi[0]:.2f} > {self.params.rsi_overbought}): {rsi_sell}")
                print(f"布林带条件({current_close:.2f} > {self.boll.lines.top[0]:.2f}): {boll_sell}")
                print(f"MACD死叉: {macd_sell}")

            should_sell = rsi_sell or boll_sell or macd_sell
                
            if should_sell:
                if rsi_sell:
                    self.lines.signal[0] = -1
                    self.reason = "RSI超买且MACD死叉，价格突破布林带上轨。"
                elif boll_sell:
                    self.lines.signal[0] = -2
                    self.reason = "趋势向下，价格在布林带中轨下方。"
                self.order = self.sell(size=self.position.size)


def run_backtest(symbol, start_date, end_date, printlog=False, **strategy_params):
    """运行回测"""
    # 获取股票数据
    from data_fetch import get_stock_data
    data_df = get_stock_data(symbol, start_date, end_date)
    
    # 添加数据检查
    print("\n数据检查:")
    print(f"数据列: {data_df.columns.tolist()}")
    print(f"前5行数据:\n{data_df.head()}")
    print(f"后5行数据:\n{data_df.tail()}")
    print("-------------------")
    
    # 检查数据是否有缺失值
    missing_data = data_df.isnull().sum()
    if missing_data.any():
        print("\n警告：数据中存在缺失值:")
        print(missing_data[missing_data > 0])
    
    # 检查价格数据的范围
    print("\n价格数据范围:")
    print(f"最高价范围: {data_df['High'].min():.2f} - {data_df['High'].max():.2f}")
    print(f"最低价范围: {data_df['Low'].min():.2f} - {data_df['Low'].max():.2f}")
    print(f"收盘价范围: {data_df['Close'].min():.2f} - {data_df['Close'].max():.2f}")
    print("-------------------")
    
    # 初始化 Cerebro
    cerebro = bt.Cerebro()

    # 添加策略
    cerebro.addstrategy(
        BollingerRsiMacdStrategy,
        printlog=printlog,
        **strategy_params
    )

    # 准备数据
    data = bt.feeds.PandasData(
        dataname=data_df,
        fromdate=pd.to_datetime(start_date),
        todate=pd.to_datetime(end_date),
        plot=False
    )
    cerebro.adddata(data)

    # 设置初始资金
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% 手续费

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    # 运行回测
    results = cerebro.run()
    strat = results[0]

    # 计算和打印结果
    final_value = cerebro.broker.getvalue()
    pnl = final_value - initial_cash
    roi = (pnl / initial_cash) * 100

    print('\n回测结果:')
    print(f'初始资金: {initial_cash:.2f}')
    print(f'最终资金: {final_value:.2f}')
    print(f'净收益: {pnl:.2f}')
    print(f'收益率: {roi:.2f}%')

    # 计算胜率
    if strat.trades:
        winning_trades = len([t for t in strat.trades if t.pnlcomm > 0])
        win_rate = (winning_trades / len(strat.trades)) * 100
        print(f'交易次数: {len(strat.trades)}')
        print(f'胜率: {win_rate:.2f}%')

    # 打印夏普比率
    sharpe = strat.analyzers.sharpe.get_analysis()
    if sharpe.get('sharperatio'):
        print(f'夏普比率: {sharpe["sharperatio"]:.2f}')

    # 打印最大回撤
    drawdown = strat.analyzers.drawdown.get_analysis()
    if drawdown.get('max'):
        print(f'最大回撤: {drawdown["max"]["drawdown"]:.2f}%')

    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='布林带-RSI-MACD策略回测')
    parser.add_argument('symbol', type=str, help='股票代码')
    parser.add_argument(
        '--start_date',
        type=str,
        default='2023-01-01',
        help='回测开始日期 (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end_date',
        type=str,
        default='2023-12-31',
        help='回测结束日期 (YYYY-MM-DD)'
    )
    args = parser.parse_args()

    print(f"开始回测股票: {args.symbol}")
    
    # 运行回测
    run_backtest(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        bb_period=20,
        bb_devfactor=2,
        rsi_period=14,
        rsi_overbought=65,
        rsi_oversold=35,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        investment_fraction=0.8,
        min_trade_unit=100,
        printlog=True
    ) 