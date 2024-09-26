# strategies/chandelier_exit_strategy.py

import backtrader as bt
import backtrader.indicators as btind


class ChandelierExitStrategy(bt.Strategy):
    params = (
        ('atr_period', 22),           # ATR 计算周期
        ('atr_multiplier', 3.0),      # ATR 倍数
        ('use_close', True),          # 是否使用收盘价计算极值
        ('printlog', False),          # 是否打印日志
        ('investment_fraction', 0.5), # 每次交易使用可用资金的比例
        ('max_pyramiding', 2),        # 允许的最大加仓次数
    )

    def __init__(self):
        # 初始化价格数据
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high

        # ATR 指标
        self.atr = btind.ATR(self.datas[0], period=self.params.atr_period)

        # 多头停止点
        if self.params.use_close:
            self.highest = btind.Highest(self.datas[-1].close, period=self.params.atr_period)
        else:
            self.highest = btind.Highest(self.datas[-1].high, period=self.params.atr_period)
        self.long_stop = self.highest - self.params.atr_multiplier * self.atr
        
        # 前一个周期的多头停止点
        self.long_stop_prev = self.long_stop(-1)
        
        # 更新多头停止点
        self.long_stop = bt.If(
            self.data.close(-1) > self.long_stop_prev,
            bt.Max(self.long_stop, self.long_stop_prev),
            self.long_stop
        )

        # 记录止损价
        self.stop_price = None

        # 记录订单状态
        self.order = None

        # 初始化已关闭交易列表
        self.closed_trades = []

        # 初始化买入信号列表
        self.buy_signals = []

        # 方向变量
        self.direction = -1  # -1 表示空头方向，1 表示多头方向

    def log(self, txt, dt=None):
        ''' 日志函数，用于调试 '''
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，不做任何处理
            self.log(f'订单状态更新: {order.getstatusname(order.status)}')
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: 价格: {order.executed.price:.2f}, 数量: {order.executed.size}')
                # 记录买入信号
                self.buy_signals.append({
                    'Date': self.datas[0].datetime.date(0),
                    'Buy Price': order.executed.price
                })
                # 方向从非多头（-1）转为多头（1）
                if self.direction != 1:
                    self.direction = 1
                    self.log('方向改变为多头')
            elif order.issell():
                self.log(f'卖出执行: 价格: {order.executed.price:.2f}, 数量: {order.executed.size}')
                # 方向从多头（1）转为空头（-1）
                if self.direction != -1:
                    self.direction = -1
                    self.log('方向改变为空头')
            self.order = None  # 重置订单状态
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单取消/保证金不足/拒绝: {order.getstatusname(order.status)}')
            self.order = None  # 重置订单状态
        else:
            self.log(f'未知订单状态: {order.getstatusname(order.status)}')

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'交易关闭: 盈亏={trade.pnl:.2f}, 手续费={trade.pnlcomm:.2f}')
            self.closed_trades.append(trade.pnl)

    def next(self):
        """策略的核心逻辑"""
        # 更新止损价
        #self.long_stop = self.highest[0] - self.params.atr_multiplier * self.atr[0]

        # 检查是否已经有订单待处理
        if self.order:
            return

        # 买入信号
        if self.dataclose[0] > self.long_stop[0]:
            if self.direction != 1:
                # 方向从空头转为多头，开始建仓
                self.log(f'检测到方向从空头转为多头，准备建仓。当前收盘价: {self.dataclose[0]:.2f}, 当前止损线: {self.long_stop[0]:.2f}')
                # 计算可用资金
                available_cash = self.broker.getcash()
                # 可用资金的比例用于购买
                investment = available_cash * self.params.investment_fraction
                # 计算可购买的最大股数
                size = int(investment / self.dataclose[0])

                # 检查是否允许加仓
                if self.params.max_pyramiding > 0 and self.position.size > 0:
                    max_allowed = self.params.max_pyramiding - self.position.size
                    if max_allowed > 0:
                        size = min(size, max_allowed)

                # 如果可购买股数大于0，创建买入订单
                if size > 0:
                    self.log(f'创建买入订单: 价格: {self.dataclose[0]:.2f}, 数量: {size}')
                    self.order = self.buy(size=size)
                else:
                    self.log('可用资金不足或达到加仓限制，无法买入')

        # 持仓时的止损逻辑
        if self.position:
            if self.dataclose[0] < self.long_stop:
                self.log(f'触发止损卖出订单: 价格: {self.dataclose[0]:.2f}, 数量: {self.position.size}')
                self.order = self.sell(size=self.position.size)

    def stop(self):
        if self.params.printlog:
            self.log(f'策略结束时资金: {self.broker.getvalue():.2f}')
            self.log(f'已关闭交易的盈亏列表: {self.closed_trades}')
