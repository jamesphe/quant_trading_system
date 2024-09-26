# strategies/swing_strategy.py

import backtrader as bt
import logging

class SwingStrategy(bt.Strategy):
    params = (
        ('ma_short', 10),
        ('ma_long', 30),
        ('rsi_low', 30),
        ('rsi_high', 70),
        ('stop_loss', 0.95),
        ('take_profit', 1.10),
        ('printlog', False),  # 可选参数，用于控制日志打印
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.ma_short = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.params.ma_short)
        self.ma_long = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.params.ma_long)
        self.rsi = bt.indicators.RSI(self.datas[0], period=14)  # 修正为 bt.indicators.RSI
        self.crossover = bt.indicators.CrossOver(self.ma_short, self.ma_long)
        self.order = None  # 记录订单状态
        self.closed_trades = []  # 用于存储已关闭的交易
    
    def log(self, txt, dt=None):
        ''' 日志记录函数 '''
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
        logging.info(f'{dt.isoformat() if dt else ""} {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或接受，尚未成交
            return
    
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'卖出执行: {order.executed.price:.2f}')
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
    
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
    
        self.log(f'交易利润, 毛利 {trade.pnl:.2f}, 净利 {trade.pnlcomm:.2f}')
        # 将已关闭的交易添加到列表中
        self.closed_trades.append({
            'datetime': trade.closed.datetime.date(0),
            'type': 'Sell' if trade.pnl > 0 else 'Buy',
            'price': trade.price,
            'pnl': trade.pnl,
            'pnlcomm': trade.pnlcomm
        })
    
    def next(self):
        if self.order:
            return  # 如果有订单正在执行，跳过
    
        self.log(f'当前收盘价: {self.dataclose[0]:.2f}')
        self.log(f'MA Short ({self.params.ma_short}): {self.ma_short[0]:.2f}')
        self.log(f'MA Long ({self.params.ma_long}): {self.ma_long[0]:.2f}')
        self.log(f'RSI: {self.rsi[0]:.2f}')
    
        if not self.position:
            # 没有持仓情况下，判断买入信号
            if self.crossover > 0 and self.rsi < self.params.rsi_low:
                self.log('买入信号触发')
                self.order = self.buy()
        else:
            # 持仓情况下，判断卖出信号
            if self.crossover < 0 or self.rsi > self.params.rsi_high:
                self.log('卖出信号触发')
                self.order = self.sell()