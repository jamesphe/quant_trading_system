import backtrader as bt
import datetime

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
        # 计算 ATR
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        self.atr_value = self.params.atr_multiplier * self.atr

        # 计算最高高点或最高收盘价
        if self.params.use_close:
            self.highest = bt.indicators.Highest(self.data.close, period=self.params.atr_period)
            self.lowest = bt.indicators.Lowest(self.data.close, period=self.params.atr_period)
        else:
            self.highest = bt.indicators.Highest(self.data.high, period=self.params.atr_period)
            self.lowest = bt.indicators.Lowest(self.data.low, period=self.params.atr_period)

        # 初始化长短止损
        self.long_stop = self.highest - self.atr_value
        self.short_stop = self.lowest + self.atr_value

        # 方向: 1 = 多头, -1 = 空头
        self.direction = 1  # 初始方向为多头

        # 设置允许的最大加仓次数
        self.max_pyramiding = self.params.max_pyramiding
        self.current_pyramiding = 0  # 当前加仓次数

        self.trades = []  # 用于存储交易记录

    def log(self, txt, dt=None):
        ''' 日志记录功能 '''
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def next(self):
        # 获取当前价格和前一个价格
        current_close = self.data.close[0]
        prev_close = self.data.close[-1]

        # 获取前一个周期的止损值
        prev_long_stop = self.long_stop[-1]
        prev_short_stop = self.short_stop[-1]

        # 更新长止损
        if prev_close > prev_long_stop:
            self.long_stop[0] = max(self.long_stop[0], prev_long_stop)
        else:
            self.long_stop[0] = self.long_stop[0]

        # 更新短止损
        if prev_close < prev_short_stop:
            self.short_stop[0] = min(self.short_stop[0], prev_short_stop)
        else:
            self.short_stop[0] = self.short_stop[0]

        # 确定当前方向
        if current_close > prev_short_stop:
            new_direction = 1  # 多头
        elif current_close < prev_long_stop:
            new_direction = -1  # 空头
        else:
            new_direction = self.direction  # 保持原方向

        # 检查方向变化
        direction_changed = new_direction != self.direction
        self.direction = new_direction

        # 获取当前持仓数量
        current_positions = self.position.size

        # 计算每次交易的资金量
        available_cash = self.broker.getcash() * self.params.investment_fraction
        stake = int((available_cash * self.params.investment_fraction) / current_close)

        # 处理多头方向
        if self.direction == 1:
            # 检查是否可以买入或加仓
            if not self.position:  # 如果当前未持仓
                self.buy(size=stake)
                self.current_pyramiding = 1
                self.log(f'买入信号 - 价格: {current_close:.2f}, 首次建仓')
            elif self.current_pyramiding < self.max_pyramiding and current_close > self.position.price * 1.02:
                # 如果当前收盘价高于持仓价的2%，且未达到最大加仓次数，则加仓
                self.buy(size=stake)
                self.current_pyramiding += 1
                self.log(f'加仓信号 - 价格: {current_close:.2f}, 加仓次数: {self.current_pyramiding}')
        
        # 处理空头方向
        elif self.direction == -1:
            if direction_changed:
                # 如果方向变化为空头，清空多头仓位
                if self.position.size > 0:
                    self.close()  # 平多头仓位
                    self.log(f'平多头仓位, 价格: {current_close:.2f}')
                    self.current_pyramiding = 0  # 重置加仓次数

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，但尚未执行
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行, 价格: {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒单')

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append(trade)
        super().notify_trade(trade)

    def stop(self):
        print('交易记录:')
        for trade in self.trades:
            print(f'开仓时间: {bt.num2date(trade.dtopen)}, '
                  f'收仓时间: {bt.num2date(trade.dtclose)}, '
                  f'开仓价格: {trade.price:.2f}, '
                  f'数量: {trade.size}, '
                  f'佣金: {trade.commission:.2f}, '
                  f'净盈亏: {trade.pnlcomm:.2f}')