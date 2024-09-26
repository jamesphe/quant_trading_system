# strategies/turtle_strategy.py

import backtrader as bt
import backtrader.indicators as btind

class TurtleStrategy(bt.Strategy):
    params = (
        ('entry_period', 20),       # 买入突破的时间窗口
        ('exit_period', 10),        # 卖出突破的时间窗口
        ('atr_period', 20),         # ATR计算周期
        ('risk_per_trade', 0.01),   # 每笔交易的风险比例（例如1%）
        ('stake', 1),                # 初始仓位大小
        ('printlog', False),        # 是否打印日志
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # 定义买入突破的最高价指标
        self.entry_high = btind.Highest(self.datahigh, period=self.params.entry_period)
        
        # 定义卖出突破的最低价指标
        self.exit_low = btind.Lowest(self.datalow, period=self.params.exit_period)
        
        # 定义ATR指标
        self.atr = btind.ATR(self.datas[0], period=self.params.atr_period)
        
        # 记录当前的止损价
        self.stop_price = None
        
        # 记录订单状态
        self.order = None
        
        # 初始化已关闭交易列表
        self.closed_trades = []
        
    def log(self, txt, dt=None):
        ''' 日志函数 '''
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
    
    def next(self):
        # 日志当前日期和价格
        self.log(f"当前日期: {self.datas[0].datetime.date(0)}, Close: {self.dataclose[0]:.2f}, "
                 f"High: {self.datahigh[0]:.2f}, Low: {self.datalow[0]:.2f}")
        
        # 日志指标值
        self.log(f"Entry High (过去 {self.params.entry_period} 天): {self.entry_high[0]:.2f}, "
                 f"Exit Low (过去 {self.params.exit_period} 天): {self.exit_low[0]:.2f}, "
                 f"ATR: {self.atr[0]:.2f}")
        
        if self.order:
            self.log("有未完成的订单，跳过本次循环。")
            return  # 如果有订单正在执行，跳过
        
        # 计算当前的仓位风险（ATR * 2）
        risk_amount = self.broker.getcash() * self.params.risk_per_trade
        atr_risk = self.atr[0] * 2
        
        # 计算需要买入的股数
        size = risk_amount / atr_risk
        size = int(size) if size > 0 else 1  # 至少买1股
        
        if not self.position:
            # 买入突破信号：当前最高价突破过去entry_period天的最高价
            if self.datahigh[0] > self.entry_high[0]:
                self.log(f'买入信号生成, 价格: {self.dataclose[0]:.2f}, 计算买入股数: {size}')
                self.order = self.buy(size=size)
            else:
                self.log("未触发买入信号。")
        else:
            # 卖出突破信号：当前最低价跌破过去exit_period天的最低价
            if self.datalow[0] < self.exit_low[0]:
                self.log(f'卖出信号生成, 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell(size=self.params.stake)
            else:
                # 动态止损
                new_stop = self.dataclose[0] - self.atr[0] * 2
                if self.stop_price is None:
                    self.stop_price = new_stop
                    self.log(f'初始止损价设定: {self.stop_price:.2f}')
                    self.order = self.sell(
                        exectype=bt.Order.Stop, price=self.stop_price, size=self.params.stake
                    )
                elif new_stop > self.stop_price:
                    self.log(f'新止损价: {new_stop:.2f} > 当前止损价: {self.stop_price:.2f}')
                    self.stop_price = new_stop
                    self.log(f'更新止损价为: {self.stop_price:.2f}')
                    # 取消之前的止损订单
                    if self.order and self.order.status in [bt.Order.Submitted, bt.Order.Accepted]:
                        self.cancel(self.order)
                        self.log("取消之前的止损订单。")
                    # 重新下止损订单
                    self.order = self.sell(
                        exectype=bt.Order.Stop, price=self.stop_price, size=self.params.stake
                    )
                else:
                    self.log(f'新止损价: {new_stop:.2f} 不大于当前止损价: {self.stop_price:.2f}，不更新止损价。')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，不做任何处理
            return
    
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: {order.executed.price:.2f}, 数量: {order.executed.size}')
            elif order.issell():
                self.log(f'卖出执行: {order.executed.price:.2f}, 数量: {order.executed.size}')
            self.order = None  # 重置订单状态
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
            self.order = None  # 重置订单状态
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'交易关闭: 盈亏={trade.pnl:.2f}, 手续费={trade.pnlcomm:.2f}')
            self.closed_trades.append(trade.pnl)
    
    def stop(self):
        if self.params.printlog:
            self.log(f'策略结束时资金: {self.broker.getvalue():.2f}')
            self.log(f'已关闭交易的盈亏列表: {self.closed_trades}')
