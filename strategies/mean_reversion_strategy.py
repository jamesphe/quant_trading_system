# strategies/mean_reversion_strategy.py

import backtrader as bt
import backtrader.indicators as btind

class MeanReversionStrategy(bt.Strategy):
    params = (
        ('period', 20),
        ('devfactor', 2),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        # 定义布林带指标
        self.boll = btind.BollingerBands(self.datas[0], period=self.params.period, devfactor=self.params.devfactor)
        self.order = None
    
    def next(self):
        if self.order:
            return

        if not self.position:
            # 当价格低于布林带下轨，买入
            if self.dataclose[0] < self.boll.lines.bot[0]:
                self.order = self.buy()
        else:
            # 当价格高于布林带中轨，卖出
            if self.dataclose[0] > self.boll.lines.mid[0]:
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