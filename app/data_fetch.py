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
        stock_info = stock_info[(~stock_info['code'].str.startswith('8')) & (~stock_info['name'].str.contains('ST')) & (~stock_info['code'].str.startswith('688')) & (~stock_info['code'].str.startswith('4'))]
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

def get_stock_industry(symbol):
    """
    获取指定股票的所属行业板块

    参数:
    - symbol: 股票代码,例如 '000001'

    返回:
    - 行业板块名称,如果未找到则返回 None
    """
    try:
        # 使用stock_individual_info_em接口获取股票信息
        stock_info = ak.stock_individual_info_em(symbol=symbol)
        
        # 查找行业信息
        industry_info = stock_info[stock_info['item'] == '行业']
        
        if not industry_info.empty:
            return industry_info['value'].values[0]
        else:
            print(f"未找到股票 {symbol} 的行业信息")
            return None
    except Exception as e:
        print(f"获取股票 {symbol} 的行业信息时发生错误: {e}")
        return None

def get_industry_fund_flow_rank(sector_type="行业资金流"):
    """
    获取行业资金流向排名情况,包括今日、5日和10日的数据

    参数:
    - sector_type: str, 可选 "行业资金流", "概念资金流", "地域资金流"

    返回:
    - DataFrame: 包含行业资金流向排名的数据框,合并了今日、5日和10日的数据
    """
    try:
        print(f"开始获取 {sector_type} 的行业资金流向排名...")
        # 定义需要获取的时间周期
        periods = ["今日", "5日", "10日"]
        
        # 用于存储各个时间周期的数据
        data_frames = []
        
        for period in periods:
            # 获取行业资金流向数据
            industry_flow = ak.stock_sector_fund_flow_rank(indicator=period, sector_type=sector_type)
            print(f"成功获取 {period} 的行业资金流向数据")
            
            # 重命名列
            column_rename = {
                '名称': 'industry_name',
                '今日涨跌幅': f'{period}_change_pct',
                '主力净流入-净额': f'{period}_main_net_inflow',
                '主力净流入-净占比': f'{period}_main_net_inflow_pct',
                '超大单净流入-净额': f'{period}_super_big_net_inflow',
                '超大单净流入-净占比': f'{period}_super_big_net_inflow_pct',
                '大单净流入-净额': f'{period}_big_net_inflow',
                '大单净流入-净占比': f'{period}_big_net_inflow_pct',
                '中单净流入-净额': f'{period}_medium_net_inflow',
                '中单净流入-净占比': f'{period}_medium_net_inflow_pct',
                '小单净流入-净额': f'{period}_small_net_inflow',
                '小单净流入-净占比': f'{period}_small_net_inflow_pct',
                '主力净流入最大股': f'{period}_top_net_inflow_stock'
            }
            
            industry_flow_rank = industry_flow.rename(columns=column_rename)
            print(f"成功重命名 {period} 的行业资金流向数据列")
            
            # 确保数值列为float类型
            numeric_columns = [col for col in industry_flow_rank.columns if col != 'industry_name' and col != f'{period}_top_net_inflow_stock']
            for col in numeric_columns:
                industry_flow_rank[col] = pd.to_numeric(industry_flow_rank[col], errors='coerce')
            print(f"成功转换 {period} 的行业资金流向数据列为float类型")
            
            data_frames.append(industry_flow_rank)
        
        # 合并三个时间周期的数据
        merged_data = data_frames[0]
        for df in data_frames[1:]:
            merged_data = pd.merge(merged_data, df, on='industry_name', how='outer')
        print("成功合并三个时间周期的数据")
        
        print(f"获取 {sector_type} 的行业资金流向排名成功！")
        return merged_data
    except Exception as e:
        print(f"获取 {sector_type} 的行业资金流向排名时发生错误: {e}")
        return pd.DataFrame()
    
def get_us_stock_list():
    """
    获取知名美股清单
    """
    try:
        stock_types = ['科技类', '金融类', '医药食品类', '媒体类', '汽车能源类', '制造零售类']
        us_stock_list = pd.DataFrame()
        
        # 使用列表收集所有数据框
        dfs = []
        for stock_type in stock_types:
            stock_data = ak.stock_us_famous_spot_em(symbol=stock_type)
            dfs.append(stock_data)
        
        # 使用 concat 合并所有数据框
        if dfs:
            us_stock_list = pd.concat(dfs, ignore_index=True)
            
        us_stock_list['代码'] = us_stock_list['代码'].str.replace(r'^\d+\.', '', regex=True)
            
        # 只返回股票代码code，和股票名称name，并将字��名称改名为英文名称
        us_stock_list = us_stock_list[['代码', '名称']].rename(columns={'代码': 'code', '名称': 'name'})
        return us_stock_list
    except Exception as e:
        print(f"获取知名美股清单失败: {e}")
        return pd.DataFrame()

def get_industry_stocks(industry_name):
    """
    获取指定行业板块所包含的股票清单

    参数:
    - industry_name: str, 行业板块名称，例如"小金属"
                    可以通过 ak.stock_board_industry_name_em() 获取所有行业代码

    返回:
    - DataFrame: 包含该行业板块所有成份股信息的数据框
                返回的列包括: ['code', 'name', 'price', 'change_pct', 'volume', 
                           'amount', 'amplitude', 'high', 'low', 'open', 
                           'pre_close', 'turnover_rate']
    """
    try:
        print(f"开始获取 {industry_name} 行业板块的成份股清单...")
        
        # 获取行业成份股数据
        stocks = ak.stock_board_industry_cons_em(symbol=industry_name)
        
        # 重命名列
        stocks = stocks.rename(columns={
            '代码': 'code',
            '名称': 'name',
            '最新价': 'price',
            '涨跌幅': 'change_pct',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '最高': 'high',
            '最低': 'low',
            '今开': 'open',
            '昨收': 'pre_close',
            '换手率': 'turnover_rate'
        })
        
        # 排除ST股票、科创板股票、北交所股票和新三板股票
        stocks = stocks[(~stocks['code'].str.startswith('8')) & 
                       (~stocks['name'].str.contains('ST')) & 
                       (~stocks['code'].str.startswith('688')) & 
                       (~stocks['code'].str.startswith('4'))]
        
        # 选择需要的列
        selected_columns = ['code', 'name', 'price', 'change_pct', 'volume', 
                          'amount', 'amplitude', 'high', 'low', 'open', 
                          'pre_close', 'turnover_rate']
        stocks = stocks[selected_columns]
        
        # 确保数值列为float类型
        numeric_columns = [col for col in selected_columns if col not in ['code', 'name']]
        for col in numeric_columns:
            stocks[col] = pd.to_numeric(stocks[col], errors='coerce')
            
        print(f"成功获取 {industry_name} 行业板块的成份股清单，共 {len(stocks)} 只股票")
        return stocks
        
    except Exception as e:
        print(f"获取 {industry_name} 行业板块成份股清单时发生错误: {e}")
        return pd.DataFrame()
