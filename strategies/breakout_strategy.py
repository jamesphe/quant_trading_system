# strategies/breakout_strategy.py

import backtrader as bt
import backtrader.indicators as btind

class BreakoutStrategy(bt.Strategy):
    params = (
        ('period', 20),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        # 定义布林带指标
        self.boll = btind.BollingerBands(self.datas[0], period=self.params.period)
        self.order = None  # 记录订单状态
    
    def next(self):
        if self.order:
            return  # 如果有订单正在执行，跳过

        if not self.position:
            # 没有持仓情况下，判断买入信号
            if self.dataclose[0] > self.boll.lines.top[0]:
                self.order = self.buy()
        else:
            # 持仓情况下，判断卖出信号
            if self.dataclose[0] < self.boll.lines.bot[0]:
                self.order = self.sell()
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f'买入执行: {order.executed.price:.2f}')
            elif order.issell():
                print(f'卖出执行: {order.executed.price:.2f}')
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('订单取消/保证金不足/拒绝')
            self.order = None