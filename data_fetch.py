# data_fetch.py

import akshare as ak
import pandas as pd
from datetime import datetime

def get_a_share_list():
    """
    获取A股所有上市股票的代码和名称。
    """
    try:
        stock_info = ak.stock_info_a_code_name()
        # 排除8开头的股票和ST股票
        stock_info = stock_info[(~stock_info['code'].str.startswith('8')) & (~stock_info['name'].str.contains('ST'))]
        return stock_info
    except Exception as e:
        print(f"获取A股列表失败: {e}")
        return pd.DataFrame()

def get_stock_data(symbol, start_date, end_date):
    """
    获取A股股票历史行情数据

    参数：
    - symbol: 股票代码，例如 '600519'
    - start_date: 开始日期，格式 'YYYY-MM-DD'
    - end_date: 结束日期，格式 'YYYY-MM-DD'

    返回：
    - stock_data: 经过预处理的DataFrame
    """
    try:
        # 获取数据，复权类型为前复权（qfq）
        stock_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date.replace('-', ''), end_date=end_date.replace('-', ''), adjust="qfq")
        
        if stock_data.empty:
            print(f"股票 {symbol} 无有效数据。")
            return pd.DataFrame()
        
        # 重命名列名
        stock_data.rename(columns={
            '日期': 'Date',
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume',
            '成交额': 'Amount',
            '涨跌幅': 'Pct_change'
        }, inplace=True)
        
        # 将'Date'列转换为日期格式并设置为索引
        stock_data['Date'] = pd.to_datetime(stock_data['Date'])
        stock_data.set_index('Date', inplace=True)
        
        # 将数据类型转换为数值类型
        numeric_cols = ['Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Pct_change']
        stock_data[numeric_cols] = stock_data[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        # 按日期排序
        stock_data.sort_index(inplace=True)
        
        return stock_data[['Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Pct_change']]
    except Exception as e:
        print(f"获取股票 {symbol} 数据失败: {e}")
        return pd.DataFrame()

def get_us_stock_data(symbol, start_date, end_date):
    """
    获取美股历史行情数据

    参数：
    - symbol: 股票代码，例如 'AAPL'
    - start_date: 开始日期，格式 'YYYY-MM-DD'
    - end_date: 结束日期，格式 'YYYY-MM-DD'

    返回：
    - stock_data: 经过预处理的DataFrame
    """
    try:
        # 获取数据
        stock_data = ak.stock_us_daily(symbol=symbol)
        
        if stock_data.empty:
            print(f"股票 {symbol} 无有效数据。")
            return pd.DataFrame()
        
        # 重命名列名
        stock_data.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        }, inplace=True)
        
        # 将'Date'列转换为日期格式并设置为索引
        stock_data['Date'] = pd.to_datetime(stock_data['Date'])
        stock_data.set_index('Date', inplace=True)
        
        # 筛选日期范围
        stock_data = stock_data.loc[start_date:end_date]
        
        # 计算涨跌幅
        stock_data['Pct_change'] = stock_data['Close'].pct_change() * 100
        
        # 将数据类型转换为数值类型
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Pct_change']
        stock_data[numeric_cols] = stock_data[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        # 按日期排序
        stock_data.sort_index(inplace=True)
        
        return stock_data[['Open', 'High', 'Low', 'Close', 'Volume', 'Pct_change']]
    except Exception as e:
        print(f"获取美股 {symbol} 数据失败: {e}")
        return pd.DataFrame()

def get_stock_name(symbol):
    """
    根据股票代码获取股票名称

    参数：
    - symbol: 股票代码，例如 '300077'

    返回：
    - 股票名称，如果未找到则返回原始代码
    """
    try:
        # 使用 akshare 获取 A 股股票列表
        stock_list = ak.stock_info_a_code_name()
        
        # 查找匹配的股票
        stock = stock_list[stock_list['代码'] == symbol]
        
        if not stock.empty:
            return stock['名称'].values[0]
        else:
            # 如果在 A 股列表中未找到，尝试获取美股名称
            us_stock_info = ak.stock_us_fundamental(symbol=symbol)
            if not us_stock_info.empty and 'name' in us_stock_info.columns:
                return us_stock_info['name'].values[0]
            else:
                return symbol  # 如果未找到，返回原始代码
    except Exception as e:
        print(f"获取股票 {symbol} 名称时发生错误: {e}")
        return symbol  # 发生错误时返回原始代码
