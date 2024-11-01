import pandas as pd
from data_fetch import get_stock_name, get_stock_industry
import sys
from datetime import datetime

def add_stock_names(input_file, output_file):
    # 读取指定日期后缀的CSV文件
    df = pd.read_csv(input_file, dtype={'symbol': str})
    df = df[df['last_signal'] == 1]
    
    # 过滤出最佳回报大于0.2的股票
    df = df[df['best_return'] > 0.2]
    
    

    # 将symbol列的值前缀补0符合A股编码规则
    df['symbol'] = df['symbol'].apply(lambda x: x.zfill(6))

    # 获取股票名称并添加到数据框中
    df['stock_name'] = df['symbol'].apply(lambda x: get_stock_name(x))
    
    # 获取股票行业信息并添加到数据框中
    df['industry'] = df['symbol'].apply(lambda x: get_stock_industry(x))

    # 重新排列列的顺序，将stock_name放在symbol后面
    columns = df.columns.tolist()
    columns.insert(1, columns.pop(columns.index('stock_name')))
    columns.insert(2, columns.pop(columns.index('industry')))
    df = df[columns]

    # 保存到新的CSV文件
    df.to_csv(output_file, index=False)

    print(f"处理完成。结果已保存到 {output_file}")

def main():
    if len(sys.argv) > 1:
        date_suffix = sys.argv[1]
    else:
        date_suffix = datetime.now().strftime('%Y-%m-%d')
    input_file = f'all_stocks_optimization_results_{date_suffix}.csv'
    output_file = f'target_stocks_{date_suffix}.csv'
    add_stock_names(input_file, output_file)

if __name__ == "__main__":
    main()
