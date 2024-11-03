# strategies/mean_reversion_strategy.py

import backtrader as bt
import pandas as pd


class TradeRecord:
    def __init__(self):
        self.trades = []
        self.trade_groups = []  # 新增：用于存储分组后的交易
    
    def add(self, date, action, price, size=None, value=None, commission=None, reason=None, pnl=None):
        trade = {
            'date': date,
            'action': action,
            'price': price,
            'size': size,
            'value': value,
            'commission': commission,
            'reason': reason,
            'pnl': pnl
        }
        self.trades.append(trade)
        self._group_trades()  # 每次添加交易后重新分组
    
    def _group_trades(self):
        """将交易按买入卖出配对分组"""
        self.trade_groups = []
        current_group = []
        
        for trade in self.trades:
            # 如果是交易结束，且有当前组，则添加到当前组
            if trade['action'] == '交易结束' and current_group:
                current_group.append(trade)
                continue
                
            # 如果是新的买入成交，开始新的组
            if trade['action'] == '买入成交':
                if current_group:  # 如果有未完成的组，先保存
                    self.trade_groups.append(current_group)
                current_group = [trade]
            # 如果是当前交易组的一部分
            elif current_group:
                current_group.append(trade)
                # 当遇到卖出成交时，结束当前分组
                if trade['action'] == '卖出成交':
                    self.trade_groups.append(current_group)
                    current_group = []
        
        # 如果还有未完成的交易，添加到分组中
        if current_group:
            self.trade_groups.append(current_group)
    
    def print_trades(self):
        print("\n📊 交易明细报告")
        print("=" * 60)
        
        total_pnl = 0
        for i, group in enumerate(self.trade_groups, 1):
            print(f"\n🔄 交易 #{i}")
            print("-" * 50)
            
            group_pnl = 0
            for trade in group:
                date = trade['date'].strftime('%Y-%m-%d')
                action = trade['action']
                price = f"¥{trade['price']:.2f}" if trade['price'] else '-'
                size = f"{trade['size']}股" if trade['size'] else ''
                value = f"¥{trade['value']:.2f}" if trade['value'] else ''
                commission = f"¥{trade['commission']:.2f}" if trade['commission'] else ''
                pnl = trade['pnl'] if trade['pnl'] is not None else 0
                group_pnl += pnl
                pnl_str = f"¥{pnl:.2f}" if pnl != 0 else ''
                reason = f"({trade['reason']})" if trade['reason'] else ''
                
                # 组合输出信息
                trade_info = f"📅 {date} | {action}"
                if size:
                    trade_info += f" {size}"
                if price != '-':
                    trade_info += f" @ {price}"
                if value:
                    trade_info += f" 金额: {value}"
                if commission:
                    trade_info += f" 手续费: {commission}"
                if pnl_str:
                    trade_info += f" 盈亏: {pnl_str}"
                if reason:
                    trade_info += f" {reason}"
                    
                print(trade_info)
            
            # 显示当前交易组的盈亏小计
            if group_pnl != 0:
                print(f"📈 交易盈亏: ¥{group_pnl:.2f}")
            total_pnl += group_pnl
        
        print("\n" + "=" * 60)
        print(f"💰 总盈亏: ¥{total_pnl:.2f}")


class SignalIndicator(bt.Indicator):
    lines = ('signal',)  # 定义一个信号线
    plotinfo = dict(plot=True, plotname='Signal')
    
    def __init__(self):
        super(SignalIndicator, self).__init__()
        # 不需要初始化 self.lines.signal，backtrader 会自动处理

    def next(self):
        # 在这里计算信号值
        self.lines.signal[0] = 0  # 默认无信号


class MeanReversionStrategy(bt.Strategy):
    params = (
        ('period', 20),  # 布林带周期
        ('devfactor', 2),  # 布林带标准差倍数
        ('portion', 0.1),  # 每次交易的资金比例
        ('stop_loss', 0.02),  # 止损比例
        ('take_profit', 0.04),  # 止盈比例
    )

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(
            self.data.close, period=self.p.period, devfactor=self.p.devfactor
        )
        self.order = None
        self.price_entry = None
        self.trade_record = TradeRecord()
        
        # 添加交易列表用于优化分析
        self.trades = []
        
        # 添加信号指标用于优化器跟踪
        self.signal = SignalIndicator()  # 使用自定义的信号指标
        
    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append(trade)
            
            # 记录交易的详细信息
            self.trade_record.add(
                date=self.datas[0].datetime.date(0),
                action='交易结束',
                price=trade.price,
                size=trade.size,
                value=trade.value,
                commission=trade.commission,
                pnl=trade.pnlcomm
            )
            
    def next(self):
        if self.order:
            return

        if not self.position:
            if self.data.close[0] < self.boll.lines.bot[0]:
                size = int(self.broker.getcash() * self.p.portion / self.data.close[0])
                if size > 0:
                    self.price_entry = self.data.close[0]
                    self.order = self.buy(size=size)
        else:
            sell_reason = ""
            if self.data.close[0] > self.boll.lines.top[0]:
                sell_reason = "突破上轨"
            elif self.data.close[0] > self.boll.lines.mid[0]:
                sell_reason = "突破中轨"
            elif self.data.close[0] < self.price_entry * (1 - self.p.stop_loss):
                sell_reason = "止损"
            elif self.data.close[0] > self.price_entry * (1 + self.p.take_profit):
                sell_reason = "止盈"

            if sell_reason:
                self.order = self.sell(size=self.position.size)
                pnl = (self.data.close[0] - self.position.price) * self.position.size
                self.trade_record.add(
                    date=self.datas[0].datetime.date(0),
                    action='卖出信号',
                    price=self.data.close[0],
                    reason=sell_reason,
                    pnl=pnl
                )

            # 更新信号指标
            if not self.position:
                self.signal.lines.signal[0] = (
                    1 if self.data.close[0] < self.boll.lines.bot[0] else 0
                )
            else:
                self.signal.lines.signal[0] = (
                    -1 if sell_reason else 0
                )

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.trade_record.add(
                    date=self.datas[0].datetime.date(0),
                    action='买入成交',
                    price=order.executed.price,
                    size=order.executed.size,
                    value=order.executed.value,
                    commission=order.executed.comm
                )
            elif order.issell():
                self.trade_record.add(
                    date=self.datas[0].datetime.date(0),
                    action='卖出成交',
                    price=order.executed.price,
                    size=order.executed.size,
                    value=order.executed.value,
                    commission=order.executed.comm
                )
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.trade_record.add(
                date=self.datas[0].datetime.date(0),
                action='订单取消/拒绝',
                price=0,
                reason=order.getstatusname()
            )

        self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"[{dt}] {txt}")

    def stop(self):
        """策略结束的回调函数"""
        # 计算策略的最终统计数据
        self.final_value = self.broker.getvalue()
        self.pnl = self.final_value - self.broker.startingcash
        self.roi = (self.final_value / self.broker.startingcash - 1.0) * 100
        
        if self.trades:
            self.win_trades = sum(1 for t in self.trades if t.pnlcomm > 0)
            self.loss_trades = sum(1 for t in self.trades if t.pnlcomm <= 0)
            self.total_trades = len(self.trades)
            self.win_rate = (self.win_trades / self.total_trades 
                           if self.total_trades > 0 else 0)


def run_mean_reversion_backtest(symbol, start_date, end_date, data_df, **kwargs):
    cerebro = bt.Cerebro()

    data = bt.feeds.PandasData(
        dataname=data_df,
        fromdate=pd.to_datetime(start_date),
        todate=pd.to_datetime(end_date)
    )
    cerebro.adddata(data)
    cerebro.addstrategy(MeanReversionStrategy, **kwargs)

    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    results = cerebro.run()
    strat = results[0]

    # 打印交易记录
    strat.trade_record.print_trades()
    
    # 获取交易分析
    trade_analysis = strat.analyzers.trades.get_analysis()
    
    if trade_analysis:
        total_trades = getattr(trade_analysis.total, 'total', 0)
        won_total = getattr(trade_analysis.won, 'total', 0)
        lost_total = getattr(trade_analysis.lost, 'total', 0)
        
        print("\n=== 交易统计 ===")
        print(f"总交易次数: {total_trades}")
        print(f"盈利交易: {won_total}")
        print(f"亏损交易: {lost_total}")
        
        if total_trades > 0:
            win_rate = (won_total / total_trades * 100)
            print(f"胜率: {win_rate:.2f}%")
            
        if hasattr(trade_analysis, 'pnl') and hasattr(trade_analysis.pnl, 'net'):
            total_pnl = getattr(trade_analysis.pnl.net, 'total', 0)
            avg_pnl = getattr(trade_analysis.pnl.net, 'average', 0)
            print(f"总盈亏: {total_pnl:.2f}")
            print(f"平均盈亏: {avg_pnl:.2f}")
    
    return results


def print_optimization_results(best_params, sharpe_ratio, max_drawdown, win_rate, total_return, last_signal):
    print("\n" + "=" * 50)
    print("🎯 策略优化结果".center(48))
    print("=" * 50)
    
    print("\n📊 最佳参数组合：")
    print("-" * 30)
    print(f"• 布林带周期: {best_params['period']:>8}")
    print(f"• 标准差倍数: {best_params['devfactor']:>8.2f}")
    print(f"• 仓位比例  : {best_params['portion']:>8.0%}")
    print(f"• 止损比例  : {best_params['stop_loss']:>8.0%}")
    print(f"• 止盈比例  : {best_params['take_profit']:>8.0%}")
    
    print("\n📈 策略绩效：")
    print("-" * 30)
    print(f"• 夏普比率  : {sharpe_ratio:>8.2f}")
    print(f"• 最大回撤  : {max_drawdown:>8.1%}")
    print(f"• 胜率      : {win_rate:>8.0%}")
    print(f"• 总收益率  : {total_return:>8.1%}")
    
    # 根据最后信号给出策略建议
    print("\n🤔 策略建议：")
    print("-" * 30)
    if last_signal > 0:
        print("当前处于买入信号")
    elif last_signal < 0:
        print("当前处于卖出信号")
    else:
        print("当前无交易信号")
    
    print("\n" + "=" * 50)


if __name__ == '__main__':
    from data_fetch import get_stock_data

    symbol = '300077'  # 示例股票代码
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    data_df = get_stock_data(symbol, start_date, end_date)

    run_mean_reversion_backtest(
        symbol,
        start_date,
        end_date,
        data_df,
        period=25,        # 布林带周期
        devfactor=2.36,    # 标准差倍数
        portion=0.18,      # 更大的仓位比例
        stop_loss=0.04,   # 止损比例
        take_profit=0.04  # 止盈比例
    )