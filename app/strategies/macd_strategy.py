# macd_strategy.py

import backtrader as bt
import backtrader.indicators as btind
import logging

class MACDStrategy(bt.Strategy):
    """
    基于MACD的交易策略。
    
    参数:
        macd1 (int): MACD快速EMA周期。
        macd2 (int): MACD慢速EMA周期。
        signal (int): MACD信号线EMA周期。
        stake_pct (float): 每次交易使用的资金比例。
        stop_loss_pct (float): 止损百分比。
        take_profit_pct (float): 止盈百分比。
        printlog (bool): 是否启用日志记录。
    """

    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('signal', 9),
        ('stake_pct', 0.10),      # 使用10%的可用资金
        ('stop_loss_pct', 0.95),  # 5%止损
        ('take_profit_pct', 1.10),# 10%止盈
        ('printlog', False),
    )

    def __init__(self):
        # 初始化MACD指标
        self.macd = btind.MACD(
            self.data.close,
            period_me1=self.params.macd1,
            period_me2=self.params.macd2,
            period_signal=self.params.signal
        )
        self.macd_cross = btind.CrossOver(self.macd.macd, self.macd.signal)
        
        self.order = None  # 当前订单
        self.stop_order = None  # 当前止损订单
        self.take_order = None  # 当前止盈订单

    def log(self, txt: str, dt=None) -> None:
        """
        日志记录函数
        """
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """
        订单状态通知
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或接受，尚未成交
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: 价格={order.executed.price:.2f}, 成交量={order.executed.size}')
                
                # 设置止损和止盈
                stop_price = order.executed.price * self.params.stop_loss_pct
                take_price = order.executed.price * self.params.take_profit_pct
                
                self.stop_order = self.sell(
                    exectype=bt.Order.Stop,
                    price=stop_price,
                    size=order.executed.size,
                    parent=order
                )
                self.take_order = self.sell(
                    exectype=bt.Order.Limit,
                    price=take_price,
                    size=order.executed.size,
                    parent=order
                )
                self.log(f'设置止损价格={stop_price:.2f}, 止盈价格={take_price:.2f}')
                
            elif order.issell():
                self.log(f'卖出执行: 价格={order.executed.price:.2f}, 成交量={order.executed.size}')
                # 如果是止损或止盈卖出，可以在这里处理相关逻辑

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/被拒绝')

        self.order = None  # 重置订单

    def notify_trade(self, trade):
        """
        交易通知
        """
        if not trade.isclosed:
            return
        self.log(f'交易利润, 毛利={trade.pnl:.2f}, 净利={trade.pnlcomm:.2f}')

    def calculate_position_size(self) -> int:
        """
        根据资金比例计算仓位规模
        """
        cash = self.broker.getcash()
        size = (cash * self.params.stake_pct) / self.data.close[0]
        return int(size)

    def next(self):
        """
        主交易逻辑
        """
        # 记录当前的指标值
        self.log(f'MACD: {self.macd.macd[0]:.2f}, 信号线: {self.macd.signal[0]:.2f}, MACD差值: {self.macd.macd[0] - self.macd.signal[0]:.2f}')
        
        if self.order:
            return  # 如果有待处理订单，跳过

        if not self.position:
            # 未持仓，检查买入条件
            if self.macd_cross > 0:
                size = self.calculate_position_size()
                self.log(f'MACD金叉，生成买入信号，买入数量={size}')
                self.order = self.buy(size=size)
        else:
            # 已持仓，检查卖出条件
            if self.macd_cross < 0:
                self.log(f'MACD死叉，生成卖出信号')
                self.order = self.sell(size=self.position.size)