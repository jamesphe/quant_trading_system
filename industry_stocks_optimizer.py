import os
import pandas as pd
from datetime import datetime, timedelta
import argparse
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')

from data_fetch import get_industry_stocks
from optimizer import optimize_strategy
from strategies.chandelier_zlsma_strategy import ChandelierZlSmaStrategy
import backtrader as bt
from ai_stock_analysis import analyze_csv_stocks

# 将 AkShareData 类移到全局作用域
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

# 将 optimize_single_stock 函数移到全局作用域
def optimize_single_stock(stock_code, start_date, end_date, stocks):
    """优化单个股票的策略参数"""
    try:
        from data_fetch import get_stock_data
        
        # 获取股票数据
        stock_data = get_stock_data(stock_code, start_date, end_date)
        if stock_data.empty:
            print(f"股票 {stock_code} 没有可用数据")
            return None
        
        # 实例化数据源
        data_feed = AkShareData(dataname=stock_data)
        
        # 运行优化
        study = optimize_strategy(ChandelierZlSmaStrategy, data_feed, n_trials=30, n_jobs=1)
        best_trial = study.best_trial
        
        # 获取最优参数和结果
        result = {
            'code': stock_code,
            'name': stocks[stocks['code'] == stock_code]['name'].iloc[0],
            'price': stocks[stocks['code'] == stock_code]['price'].iloc[0],
            'change_pct': stocks[stocks['code'] == stock_code]['change_pct'].iloc[0],
            'volume': stocks[stocks['code'] == stock_code]['volume'].iloc[0],
            'amount': stocks[stocks['code'] == stock_code]['amount'].iloc[0],
            'period': int(best_trial.params['period']),
            'mult': round(best_trial.params['mult'], 2),
            'investment_fraction': round(best_trial.params['investment_fraction'], 2),
            'max_pyramiding': int(best_trial.params['max_pyramiding']),
            'sharpe_ratio': round(best_trial.value * -1, 2),
            'max_drawdown': round(best_trial.user_attrs['max_drawdown'], 2),
            'win_rate': round(best_trial.user_attrs['win_rate'] * 100, 2),
            'total_return': round(best_trial.user_attrs['total_return'] * 100, 2),
            'last_signal': best_trial.user_attrs['last_signal']
        }
        
        print(f"股票 {stock_code} 优化完成")
        return result
        
    except Exception as e:
        print(f"处理股票 {stock_code} 时发生错误: {str(e)}")
        return None

def optimize_industry_stocks(industry_name, start_date, end_date, max_workers=4):
    """
    获取指定行业的所有股票并进行优化分析
    
    参数:
    - industry_name: str, 行业名称，如"小金属"
    - start_date: str, 开始日期，格式'YYYY-MM-DD'
    - end_date: str, 结束日期，格式'YYYY-MM-DD'
    - max_workers: int, 并行处理的最大进程数
    """
    print(f"开始处理 {industry_name} 行业的股票...")
    
    # 获取行业成份股
    stocks = get_industry_stocks(industry_name)
    if stocks.empty:
        print(f"未能获取 {industry_name} 行业的成份股数据")
        return
    
    print(f"获取到 {len(stocks)} 只股票，开始优化分析...")
    
    # 存储优化结果
    optimization_results = []
    
    # 修改进程池的调用方式
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 不使用 lambda，直接传递股票代码和其他参数
        futures = []
        for stock_code in stocks['code'].tolist():
            future = executor.submit(optimize_single_stock, stock_code, start_date, end_date, stocks)
            futures.append(future)
        
        # 收集结果
        results = []
        for future in futures:
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"处理股票时发生错误: {str(e)}")
    
    # 过滤掉None结果并转换为DataFrame
    results = [r for r in results if r is not None]
    results_df = pd.DataFrame(results)
    
    # 保存结果
    date_str = datetime.now().strftime('%Y-%m-%d')
    output_file = f"updated_target_stocks_{date_str}.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n优化结果已保存到: {output_file}")
    
    # 调用AI分析结果
    print("\n开始AI分析优化结果...")
    analyze_csv_stocks(output_file, datetime.now())

def main():
    parser = argparse.ArgumentParser(description='行业股票优化分析工具')
    parser.add_argument('industry', type=str, help='行业名称，如"小金属"')
    parser.add_argument('--start_date', type=str, 
                       default=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
                       help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str,
                       default=datetime.now().strftime('%Y-%m-%d'),
                       help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--workers', type=int, default=4,
                       help='并行处理的进程数')
    
    args = parser.parse_args()
    
    # 确保results目录存在
    if not os.path.exists('results'):
        os.makedirs('results')
    
    optimize_industry_stocks(
        industry_name=args.industry,
        start_date=args.start_date,
        end_date=args.end_date,
        max_workers=args.workers
    )

if __name__ == '__main__':
    main() 