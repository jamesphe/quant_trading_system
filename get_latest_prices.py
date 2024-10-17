import pandas as pd
import akshare as ak
import sys
from datetime import datetime

def get_all_stock_data():
    try:
        # 获取A股实时行情
        stock_df = ak.stock_zh_a_spot_em()
        print(stock_df)
        
        # 将代码列设置为索引，以便后续快速查找
        stock_df.set_index('代码', inplace=True)
        
        return stock_df
    except Exception as e:
        print(f"获取股票数据时发生错误: {e}")
        return None

def update_target_stocks():
    # 获取命令行参数中的日期
    if len(sys.argv) > 1:
        date_suffix = sys.argv[1]
    else:
        # 默认为当天日期
        date_suffix = datetime.now().strftime("%Y-%m-%d")

    df = pd.read_csv(f'target_stocks_{date_suffix}.csv', dtype={'symbol': str})
    
    # 获取所有股票数据
    stock_df = get_all_stock_data()
    
    if stock_df is None:
        print("无法获取股票数据，程序退出。")
        return
    
    # 添加新列
    df['latest_price'] = None
    df['latest_change'] = None
    
    # 更新目标股票的数据
    for index, row in df.iterrows():
        symbol = row['symbol'].zfill(6)
        print(f"正在处理股票 {symbol}...")
        
        if symbol in stock_df.index:
            df.at[index, 'latest_price'] = stock_df.loc[symbol, '最新价']
            df.at[index, 'latest_change'] = stock_df.loc[symbol, '涨跌幅']
            df.at[index, '换手率'] = stock_df.loc[symbol, '换手率']
        else:
            print(f"未找到股票 {symbol} 的价格信息")
    
    # 按涨跌幅降序排序
    df = df.sort_values(by='latest_change', ascending=False)
    
    # 保存更新后的数据
    df.to_csv(f'updated_target_stocks_{date_suffix}.csv', index=False)
    print(f"数据更新完成，已保存到 updated_target_stocks_{date_suffix}.csv")

if __name__ == "__main__":
    update_target_stocks()
