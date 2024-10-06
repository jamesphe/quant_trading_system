import pandas as pd
from data_fetch import get_a_share_list, get_stock_data, get_stock_name
from optimizer import optimize_strategy
import backtrader as bt
from strategies import ChandelierZlSmaStrategy
from datetime import datetime, timedelta
import concurrent.futures

# 设置回测的开始和结束日期
END_DATE = datetime.now().strftime('%Y-%m-%d')
START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

def optimize_single_stock(symbol):
    """
    对单个股票进行优化
    """
    try:
        print(f"正在优化股票: {symbol}")
        
        # 获取股票数据
        stock_data = get_stock_data(symbol, START_DATE, END_DATE)
        
        if stock_data.empty:
            print(f"股票 {symbol} 没有足够的数据进行优化")
            return None

        # 定义数据源类
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

        # 实例化数据源
        data_feed = AkShareData(dataname=stock_data)

        # 进行优化
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
            'best_win_rate': round(best_trial.user_attrs['win_rate'], 2),
            'best_max_drawdown': round(best_trial.user_attrs['max_drawdown'], 2),
            'best_return': round(best_trial.user_attrs['total_return'], 2),
            **best_params
        }
    except Exception as e:
        print(f"优化股票 {symbol} 时发生错误: {e}")
        return None

def main():
    # 获取所有A股列表
    stock_list = get_a_share_list()
    
    results = []

    # 使用线程池进行并行优化
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_stock = {executor.submit(optimize_single_stock, row['code']): row['code'] for _, row in stock_list.iterrows()}
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
    results_df.to_csv('all_stocks_optimization_results.csv', index=False)
    print("优化完成,结果已保存到 all_stocks_optimization_results.csv")

if __name__ == '__main__':
    main()