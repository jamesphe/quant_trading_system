import pandas as pd
import akshare as ak
import sys
from datetime import datetime

def get_stock_data(symbol):
    try:
        # 获取个股资金流向数据
        market = "sh" if symbol.startswith("6") else "sz"
        stock_df = ak.stock_individual_fund_flow(stock=symbol, market=market)
        # 获取最新的一行数据
        latest_data = stock_df.iloc[-1]
        # 计算最近3日和最近5日的累计主力净流入-净额
        last_3_days_net_inflow = stock_df['主力净流入-净额'].iloc[-3:].sum()
        last_5_days_net_inflow = stock_df['主力净流入-净额'].iloc[-5:].sum()
        
        return {
            'latest_price': latest_data['收盘价'],
            'latest_change': latest_data['涨跌幅'],
            'main_net_inflow': latest_data['主力净流入-净额'],
            'main_net_inflow_rate': latest_data['主力净流入-净占比'],
            'last_3_days_net_inflow': last_3_days_net_inflow,
            'last_5_days_net_inflow': last_5_days_net_inflow
        }
    except Exception as e:
        print(f"获取股票 {symbol} 数据时发生错误: {e}")
        return None

def get_all_stocks_realtime_data():
    try:
        # 获取所有 A 股实时行情数据
        all_stocks_df = ak.stock_zh_a_spot_em()
        # 将股票代码设置为索引，方便后续查找
        return all_stocks_df.set_index('代码')
    except Exception as e:
        print(f"获取实时行情数据时发生错误: {e}")
        return None

def update_target_stocks():
    # 获取命令行参数中的日期
    if len(sys.argv) > 1:
        date_suffix = sys.argv[1]
    else:
        # 默认为当天日期
        date_suffix = datetime.now().strftime("%Y-%m-%d")

    df = pd.read_csv(f'target_stocks_{date_suffix}.csv', dtype={'symbol': str})
    
    # 添加新列
    df['latest_price'] = None
    df['latest_change'] = None
    df['turnover_rate'] = None
    
    # 获取所有股票的实时数据
    all_stocks_data = get_all_stocks_realtime_data()
    
    if all_stocks_data is not None:
        # 更新目标股票的数据
        for index, row in df.iterrows():
            symbol = row['symbol'].zfill(6)
            print(f"正在处理股票 {symbol}...")
            
            if symbol in all_stocks_data.index:
                stock_data = all_stocks_data.loc[symbol]
                df.at[index, 'latest_price'] = stock_data['最新价']
                df.at[index, 'latest_change'] = stock_data['涨跌幅']
                df.at[index, 'turnover_rate'] = stock_data['换手率']
            else:
                print(f"未找到股票 {symbol} 的实时数据")
        
        # 获取其他数据（如资金流向）
        for index, row in df.iterrows():
            symbol = row['symbol'].zfill(6)
            stock_data = get_stock_data(symbol)
            if stock_data:
                df.at[index, 'main_net_inflow'] = stock_data['main_net_inflow']
                df.at[index, 'main_net_inflow_rate'] = stock_data['main_net_inflow_rate']
                df.at[index, 'last_3_days_net_inflow'] = stock_data['last_3_days_net_inflow']
                df.at[index, 'last_5_days_net_inflow'] = stock_data['last_5_days_net_inflow']
    else:
        print("无法获取实时行情数据，将使用原有方法更新")
        for index, row in df.iterrows():
            symbol = row['symbol'].zfill(6)
            print(f"正在处理股票 {symbol}...")
            
            stock_data = get_stock_data(symbol)
            if stock_data:
                df.at[index, 'latest_price'] = stock_data['latest_price']
                df.at[index, 'latest_change'] = stock_data['latest_change']
                df.at[index, 'main_net_inflow'] = stock_data['main_net_inflow']
                df.at[index, 'main_net_inflow_rate'] = stock_data['main_net_inflow_rate']
                df.at[index, 'last_3_days_net_inflow'] = stock_data['last_3_days_net_inflow']
                df.at[index, 'last_5_days_net_inflow'] = stock_data['last_5_days_net_inflow']
            else:
                print(f"未找到股票 {symbol} 的数据")
    
    # 把df中的字段名称转换为中文
    df = df.rename(columns={
        'symbol': '股票代码', 'stock_name': '股票名称', 'latest_trading_amount': '最新交易量',
        'sharpe_ratio': '夏普比率', 'best_win_rate': '最佳胜率',
        'best_max_drawdown': '最佳最大回撤', 'best_return': '最佳回报',
        'last_signal': '最新信号', 'length': '长度', 'mult': '倍数',
        'zlsma_length': 'ZLSMA长度', 'investment_fraction': '投资比例',
        'max_pyramiding': '最大加仓', 'latest_price': '最新价格',
        'latest_change': '最新涨跌幅', 'turnover_rate': '换手率',
        'main_net_inflow': '主力净流入', 'main_net_inflow_rate': '主力净流入率',
        'last_3_days_net_inflow': '最近3日净流入', 'last_5_days_net_inflow': '最近5日净流入'
    })
    
    # 根据股票代码和涨跌幅进行过滤
    # df = df[
    #     # 以3开头的股票,涨跌幅在5%~12%之间
    #     ((df['股票代码'].str.startswith('3')) & (df['最新涨跌幅'].between(5, 12))) |
    #     # 其他股票,涨幅在3%~7%之间 
    #     ((~df['股票代码'].str.startswith('3')) & (df['最新涨跌幅'].between(3, 7)))
    # ]

    # 按涨跌幅降序排序
    df = df.sort_values(by='最新涨跌幅', ascending=False)
    
    # 保存更新后的数据
    df.to_csv(f'updated_target_stocks_{date_suffix}.csv', index=False)
    print(f"数据更新完成，已保存到 updated_target_stocks_{date_suffix}.csv")

if __name__ == "__main__":
    update_target_stocks()
