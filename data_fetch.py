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
        stock_info = stock_info[(~stock_info['code'].str.startswith('8')) & (~stock_info['name'].str.contains('ST')) & (~stock_info['code'].str.startswith('688'))]
        #stock_info = stock_info[stock_info['code'].str.startswith('3')]
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
    获取美股历史行情

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
    - symbol: 股票代码，例如 '300077' 或 'AAPL'

    返回：
    - 股票名称，如果未找到则返回原始代码
    """
    try:
        # 尝试获取A股股票名称
        stock_list = ak.stock_info_a_code_name()
        print(stock_list)
        print(symbol)
        stock = stock_list[stock_list['code'] == symbol]
        print(stock)
        
        if not stock.empty:
            return stock['name'].values[0]
               
        # 如果都未找到，返回原始代码
        return symbol
    except Exception as e:
        print(f"获取股票 {symbol} 名称时发生错误: {e}")
        return symbol

def get_etf_data(symbol, start_date, end_date):
    """
    获取A股ETF历史行情数据

    参数：
    - symbol: ETF代码，例如 '159919'（创业板ETF）
    - start_date: 开始日期，格式 'YYYY-MM-DD'
    - end_date: 结束日期，格式 'YYYY-MM-DD'

    返回：
    - etf_data: 经过预处理的DataFrame
    """
    try:
        # 获取ETF数据
        etf_data = ak.fund_etf_hist_em(
            symbol=symbol,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq"
        )
        
        if etf_data.empty:
            print(f"ETF {symbol} 无有效数据。")
            return pd.DataFrame()
        
        # 重命名列名
        etf_data.rename(columns={
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
        etf_data['Date'] = pd.to_datetime(etf_data['Date'])
        etf_data.set_index('Date', inplace=True)
        
        # 将数据类型转换为数值类型
        numeric_cols = ['Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Pct_change']
        etf_data[numeric_cols] = etf_data[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        # 按日期排序
        etf_data.sort_index(inplace=True)
        
        return etf_data[['Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Pct_change']]
    except Exception as e:
        print(f"获取ETF {symbol} 数据失败: {e}")
        return pd.DataFrame()

def get_etf_list():
    """
    获取所有A股ETF的代码和名称。

    返回：
    - etf_info: 包含ETF代码和名称的DataFrame
    """
    try:
        print("开始获取ETF列表...")
        
        # 使用akshare获取所有ETF基金列表
        etf_df = ak.fund_etf_category_sina(symbol="ETF基金")
        print(f"获取到的原始ETF数量: {len(etf_df)}")
        print("前5条ETF数据:")
        print(etf_df.head())
        
        # 打印列名，以便调试
        print(f"列名: {etf_df.columns.tolist()}")
        
        # 重命名列
        etf_info = etf_df.rename(columns={'代码': 'code', '名称': 'name'})
        print("列已重命名")
        
        # 只保留代码和名称列
        etf_info = etf_info[['code', 'name']]
        etf_info['code'] = etf_info['code'].str.replace('^(sh|sz)', '', regex=True)
        
        # 筛选出A股ETF（假设A股ETF的代码以'5'或'1'开头）
        etf_info = etf_info[etf_info['code'].str.startswith(('510', '159'))]
        
        print(f"最终A股ETF列表的形状: {etf_info.shape}")
        
        print(f"ETF列表获取成功:{etf_info}")
        return etf_info
    except Exception as e:
        print(f"获取A股ETF列表失败: {e}")
        return pd.DataFrame()
