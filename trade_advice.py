import pandas as pd
from data_fetch import get_stock_data, get_stock_name
from strategies.chandelier_zlsma_strategy import ChandelierZlSmaStrategy
import backtrader as bt
from datetime import datetime, timedelta
import os

# 当前持仓清单
current_holdings = [
    {"code": "300077", "name": "国民技术", "quantity": 300, "cost": 10.693},
    {"code": "300687", "name": "赛意信息", "quantity": 200, "cost": 11.729},
    {"code": "603206", "name": "嘉环科技", "quantity": 200, "cost": 12.731},
    {"code": "300383", "name": "光环新网", "quantity": 200, "cost": 8.425},
    {"code": "300857", "name": "协创数据", "quantity": 0, "cost": 68.95},
    {"code": "300522", "name": "万集科技", "quantity": 0, "cost": 37.00},
    # 可以添加更多持仓
]

# 当前可用资金
available_cash = 50000

def get_trade_advice(holdings, cash, days_to_analyze=200):
    advice_list = []
    today = datetime.now().date()
    start_date = (today - timedelta(days=days_to_analyze)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    for stock in holdings:
        # 获取股票数据
        stock_data = get_stock_data(stock['code'], start_date, end_date)
        
        if stock_data.empty:
            print(f"无法获取股票 {stock['code']} 的数据，跳过该股票")
            continue

        # 计算当前股票市值
        current_price = stock_data['Close'].iloc[-1]
        stock_value = stock['quantity'] * current_price

        # 创建 Cerebro 引擎
        cerebro = bt.Cerebro()

        # 添加数据
        data = bt.feeds.PandasData(dataname=stock_data)
        cerebro.adddata(data)

        optimization_file = f"results/{stock['code']}_optimization_results.csv"
        if os.path.exists(optimization_file):
            opt_results = pd.read_csv(optimization_file)
            if not opt_results.empty:
                best_params = opt_results.iloc[0]
                cerebro.addstrategy(ChandelierZlSmaStrategy, 
                                    length=int(best_params['length']), 
                                    mult=float(best_params['mult']), 
                                    zlsma_length=int(best_params['zlsma_length']), 
                                    investment_fraction=float(best_params['investment_fraction']), 
                                    max_pyramiding=int(best_params['max_pyramiding']), 
                                    printlog=bool(best_params['printlog']))
            else:
                cerebro.addstrategy(ChandelierZlSmaStrategy)
        else:
            cerebro.addstrategy(ChandelierZlSmaStrategy)

        # 设置初始资金为当前股票市值加可用资金
        initial_cash = stock_value + cash
        cerebro.broker.setcash(initial_cash)

        # 运行策略
        results = cerebro.run()

        # 获取最后一个交易日的持仓数量和信号
        final_position = cerebro.broker.getposition(data).size
        last_signal = results[0].signal[-1]

        # 获取建议建仓时间和价格
        suggested_entry_time = None
        trades = results[0].trades
        if trades:
            last_trade = trades[-1]
            print(f"last_trade.dtopen 类型: {type(last_trade.dtopen)}, 内容: {last_trade.dtopen}")
            suggested_entry_time = bt.num2date(last_trade.dtopen)
            suggested_entry_price = last_trade.price
        else:
            suggested_entry_time = "无建议"
            suggested_entry_price = 0.0

        # 生成建议
        if final_position > stock['quantity']:
            advice = "买入"
            quantity_change = final_position - stock['quantity']
        elif final_position < stock['quantity']:
            advice = "卖出"
            quantity_change = stock['quantity'] - final_position
        else:
            advice = "持有"
            quantity_change = 0

        advice_list.append({
            "code": stock['code'],
            "name": stock['name'],
            "current_quantity": stock['quantity'],
            "suggested_quantity": final_position,
            "quantity_change": quantity_change,
            "cost": stock['cost'],
            "advice": advice,
            "current_price": current_price,
            "signal": last_signal,
            "suggested_entry_time": suggested_entry_time,
            "suggested_entry_price": suggested_entry_price,
            "strategy_params": {
                "length": int(best_params['length']),
                "mult": float(best_params['mult']),
                "zlsma_length": int(best_params['zlsma_length']),
                "investment_fraction": float(best_params['investment_fraction']),
                "max_pyramiding": int(best_params['max_pyramiding']),
                "printlog": bool(best_params['printlog'])
            }
        })

    return advice_list

def print_advice(advice_list):
    print("\n交易建议:")
    for advice in advice_list:
        print(f"股票代码: {advice['code']}")
        print(f"股票名称: {advice['name']}")
        print(f"当前持股数量: {advice['current_quantity']}")
        print(f"建议持股数量: {advice['suggested_quantity']}")
        print(f"数量变化: {advice['quantity_change']}")
        print(f"持股成本: {advice['cost']:.2f}")
        print(f"当前价格: {advice['current_price']:.2f}")
        print(f"建议: {advice['advice']}")
        print(f"信号: {advice['signal']}")
        if advice['suggested_entry_time'] != "无建议":
            print(f"建议建仓时间: {advice['suggested_entry_time']}")
            print(f"建议建仓价格: {advice['suggested_entry_price']:.2f}")
        else:
            print("建议建仓时间: 无建议")
            print("建议建仓价格: 无建议")
        print(f"策略参数: 长度={advice['strategy_params']['length']}, "
              f"乘数={advice['strategy_params']['mult']}, "
              f"ZLSMA长度={advice['strategy_params']['zlsma_length']}, "
              f"投资比例={advice['strategy_params']['investment_fraction']}, "
              f"最大加仓次数={advice['strategy_params']['max_pyramiding']}, "
              f"打印日志={advice['strategy_params']['printlog']}")
        print("------------------------")

if __name__ == "__main__":
    advice_list = get_trade_advice(current_holdings, available_cash)
    print_advice(advice_list)
    print(f"当前可用资金: {available_cash:.2f}")
