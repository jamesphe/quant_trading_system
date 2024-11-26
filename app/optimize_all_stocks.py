import pandas as pd
from data_fetch import get_a_share_list, get_stock_data, get_us_stock_list, get_etf_data, get_us_stock_data
from optimizer import optimize_strategy
import backtrader as bt
from strategies import ChandelierZlSmaStrategy
from datetime import datetime, timedelta
import concurrent.futures
from tqdm import tqdm
import os
import psutil
import argparse

# 设置回测的开始和结束日期
END_DATE = datetime.now().strftime('%Y-%m-%d')
START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

def get_optimal_workers():
    cpu_count = os.cpu_count()
    available_memory = psutil.virtual_memory().available / (1024 ** 3)
    estimated_memory_per_worker = 0.3  # 每个工作进程需要0.3GB内存
    
    max_workers_memory = int(available_memory / estimated_memory_per_worker)
    optimal_workers = min(cpu_count, max_workers_memory)
    
    print(f"优化后的工作进程数: {optimal_workers}")  # 确保至少有1个工作进程，最多16个
    
    return max(1, min(optimal_workers, 16))  # 确保至少有1个工作进程，最多16个

def optimize_single_stock(symbol):
    """
    对单个股票进行优化
    """
    try:
        
        # 获取股票数据
        if symbol.startswith(('51', '159')):  # ETF
            stock_data = get_etf_data(symbol, START_DATE, END_DATE)
        elif symbol.isdigit():  # A股
            stock_data = get_stock_data(symbol, START_DATE, END_DATE)
        else:  # 美股
            stock_data = get_us_stock_data(symbol, START_DATE, END_DATE)
        
        if stock_data.empty:
            return None

        # 计算最新交易日的交易金额
        latest_trading_amount = stock_data.iloc[-1]['Close'] * stock_data.iloc[-1]['Volume']

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
            'period': int(best_trial.params['period']),
            'mult': round(best_trial.params['mult'], 2),
            'investment_fraction': round(best_trial.params['investment_fraction'], 2),
            'max_pyramiding': int(best_trial.params['max_pyramiding'])
        }

        return {
            'symbol': symbol,
            'latest_trading_amount': round(latest_trading_amount, 2),
            'sharpe_ratio': round(best_trial.value * -1, 2),
            'best_win_rate': round(best_trial.user_attrs['win_rate'], 2),
            'best_max_drawdown': round(best_trial.user_attrs['max_drawdown'], 2),
            'best_return': round(best_trial.user_attrs['total_return'], 2),
            'last_signal': best_trial.user_attrs['last_signal'],
            **best_params
        }
    except Exception:
        return None

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='股票策略优化程序')
    parser.add_argument('--market', type=str, choices=['A', 'US'], 
                       default='A', help='选择市场: A(A股) 或 US(美股)')
    args = parser.parse_args()
    
    # 根据市场类型获取股票列表
    if args.market == 'A':
        stock_list = get_a_share_list()
    else:
        stock_list = get_us_stock_list()
    
    results = []
    total_stocks = len(stock_list)

    # 使用线程池进行并行优化
    with concurrent.futures.ProcessPoolExecutor(max_workers=get_optimal_workers()) as executor:
        future_to_stock = {executor.submit(optimize_single_stock, row['code']): row['code'] for _, row in stock_list.iterrows()}
        
        # 使用tqdm创建进度条
        with tqdm(total=total_stocks, desc="优化进度", ncols=100) as pbar:
            for future in concurrent.futures.as_completed(future_to_stock):
                result = future.result()
                if result:
                    results.append(result)
                pbar.update(1)  # 更新进度条

    # 将结果转换为DataFrame并保存为CSV
    results_df = pd.DataFrame(results)
    market_str = "all_stocks" if args.market == 'A' else "us_stocks"
    filename = (f'{market_str}_optimization_results_'
               f'{datetime.now().strftime("%Y-%m-%d")}.csv')
    
    # 确保stock_data目录存在
    os.makedirs('stock_data', exist_ok=True)
    
    # 保存到stock_data目录
    save_path = os.path.join('stock_data', filename)
    results_df.to_csv(save_path, index=False)
    print(f"优化完成，结果已保存到 {save_path}")

if __name__ == '__main__':
    main()
