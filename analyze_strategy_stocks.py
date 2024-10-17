import pandas as pd
from datetime import datetime, timedelta
import backtrader as bt
from strategies import ChandelierZlSmaStrategy
from optimizer import optimize_strategy
import concurrent.futures
from data_fetch import get_stock_data, get_etf_data, get_us_stock_data

# 设置回测的开始和结束日期
END_DATE = datetime.now().strftime('%Y-%m-%d')
START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

def check_direction_change(stock_data):
    """检查最近3个交易日是否有交易方向变化"""
    if len(stock_data) < 3:
        return False
    
    last_3_days = stock_data.tail(3)
    direction = (last_3_days['Close'] > last_3_days['Open']).tolist()
    return not all(direction) and not all(not d for d in direction)

def optimize_single_stock(symbol):
    """对单个股票进行优化并检查交易方向"""
    try:
        print(f"正在分析股票: {symbol}")
        
        symbol = str(symbol)
        
        # 根据股票代码类型选择适当的数据获取方法
        if symbol.startswith(('510', '159')):  # ETF
            stock_data = get_etf_data(symbol, START_DATE, END_DATE)
        elif symbol.isdigit():  # A股
            stock_data = get_stock_data(symbol, START_DATE, END_DATE)
        else:  # 美股
            stock_data = get_us_stock_data(symbol, START_DATE, END_DATE)
        
        if stock_data.empty:
            print(f"股票 {symbol} 没有足够的数据进行分析")
            return None

        class AkShareData(bt.feeds.PandasData):
            params = (
                ('datetime', None),
                ('open', 'Open'),
                ('high', 'High'),
                ('low', 'Low'),
                ('close', 'Close'),
                ('volume', 'Volume'),
                ('openinterest', -1),
            )

        data_feed = AkShareData(dataname=stock_data)

        study = optimize_strategy(ChandelierZlSmaStrategy, data_feed, n_trials=50, n_jobs=1)

        best_trial = study.best_trial
        best_params = {
            'length': int(best_trial.params['length']),
            'mult': round(best_trial.params['mult'], 2),
            'zlsma_length': int(best_trial.params['zlsma_length']),
            'investment_fraction': round(best_trial.params['investment_fraction'], 2),
            'max_pyramiding': int(best_trial.params['max_pyramiding'])
        }

        return {
            'symbol': symbol,
            'sharpe_ratio': round(best_trial.value * -1, 2),
            'win_rate': round(best_trial.user_attrs['win_rate'], 2),
            'max_drawdown': round(best_trial.user_attrs['max_drawdown'], 2),
            'total_return': round(best_trial.user_attrs['total_return'], 2),
            'last_signal': best_trial.user_attrs['last_signal'],
            **best_params
        }
    except Exception as e:
        print(f"分析股票 {symbol} 时发生错误: {e}")
        return None

def main():
    # 读取股票列表
    stock_list = pd.read_csv('all_strategy_results.csv', dtype={'股票代码': str})
    
    results = []

    # 使用线程池进行并行优化
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_stock = {executor.submit(optimize_single_stock, row['股票代码']): row['股票代码'] for _, row in stock_list.iterrows()}
        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as exc:
                print(f'{stock} 生成了一个异常: {exc}')

    # 将结果转换为DataFrame并保存为CSV
    results_df = pd.DataFrame(results)
    filename = f'strategy_analysis_results_{datetime.now().strftime("%Y-%m-%d")}.csv'
    results_df.to_csv(filename, index=False)
    print(f"分析完成,结果已保存到 {filename}")

if __name__ == '__main__':
    main()