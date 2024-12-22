# data_fetch.py

import akshare as ak
import pandas as pd
import baostock as bs
from datetime import datetime
import talib
import os
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

def get_stock_data(symbol, start_date, end_date, source='akshare', include_macd=False, include_rsi=False, include_boll=False, include_zlsma=False, include_chandelier=False):
    """
    获取A股股票历史行情数据

    参数：
    - symbol: 股票代码，例如 '600519'
    - start_date: 开始日期，格式 'YYYY-MM-DD'
    - end_date: 结束日期，格式 'YYYY-MM-DD'
    - source: 数据源，可选 'akshare' 或 'baostock'，默认为 'akshare'
    - include_macd: 是否包含MACD指标数据，默认为False
    - include_rsi: 是否包含RSI指标数据，默认为False
    - include_boll: 是否包含布林带指标数据，默认为False
    - include_zlsma: 是否包含零延迟移动平均线，默认为False
    - include_chandelier: 是否包含吊灯止损指标，默认为False

    返回：
    - stock_data: 经过预处理的DataFrame，包含以下可选指标：
                 - MACD、MACD_SIGNAL和MACD_HIST (if include_macd=True)
                 - RSI_6、RSI_12和RSI_24 (if include_rsi=True)
                 - BOLL_UPPER、BOLL_MIDDLE、BOLL_LOWER (if include_boll=True)
                 - ZLSMA_20、ZLSMA_60 (if include_zlsma=True)
                 - CHANDELIER_LONG、CHANDELIER_SHORT (if include_chandelier=True)
    """
    # 验证日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    if end_date > current_date:
        print(f"结束日期 {end_date} 超过当前日期 {current_date}，将使用当前日期作为结束日期")
        end_date = current_date
    
    # 获取基础数据
    if source == 'baostock':
        stock_data = _get_stock_data_baostock(symbol, start_date, end_date)
    else:
        stock_data = _get_stock_data_akshare(symbol, start_date, end_date)
    
    if not stock_data.empty and (include_macd or include_rsi or include_boll or include_zlsma or include_chandelier):
        # 获取额外90天的数据以确保指标计算的准确性
        extended_start_date = (pd.to_datetime(start_date) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
        temp_df = get_stock_data(symbol, extended_start_date, end_date, source=source, 
                               include_macd=False, include_rsi=False, include_boll=False, include_zlsma=False, include_chandelier=False)
        
        if include_macd:
            # 计算EMA
            exp12 = temp_df['Close'].ewm(span=12, adjust=False).mean()
            exp26 = temp_df['Close'].ewm(span=26, adjust=False).mean()
            
            # 计算MACD
            temp_df['MACD'] = exp12 - exp26
            temp_df['MACD_SIGNAL'] = temp_df['MACD'].ewm(span=9, adjust=False).mean()
            temp_df['MACD_HIST'] = temp_df['MACD'] - temp_df['MACD_SIGNAL']
        
        if include_rsi:
            # 计算不同周期的RSI
            temp_df['RSI_6'] = talib.RSI(temp_df['Close'].values, timeperiod=6)
            temp_df['RSI_12'] = talib.RSI(temp_df['Close'].values, timeperiod=12)
            temp_df['RSI_24'] = talib.RSI(temp_df['Close'].values, timeperiod=24)
        
        if include_boll:
            # 计算布林带指标 (20日均线，2倍标准差)
            upper, middle, lower = talib.BBANDS(
                temp_df['Close'].values,
                timeperiod=20,
                nbdevup=2,
                nbdevdn=2,
                matype=0  # 简单移动平均
            )
            temp_df['BOLL_UPPER'] = upper
            temp_df['BOLL_MIDDLE'] = middle
            temp_df['BOLL_LOWER'] = lower
        
        if include_zlsma:
            # 计算ZLSMA指标
            # 计算20日和60日的ZLSMA
            for period in [20, 60]:
                # 计算EMA
                ema = temp_df['Close'].ewm(span=period, adjust=False).mean()
                # 计算EMA的EMA
                ema_ema = ema.ewm(span=period, adjust=False).mean()
                # 计算ZLSMA
                temp_df[f'ZLSMA_{period}'] = 2 * ema - ema_ema
        
        if include_chandelier:
            # 尝试读取优化参数文件
            try:
                result_file = f"results/{symbol}_ChandelierZlSmaStrategy_optimization_results.csv"
                if os.path.exists(result_file):
                    params_df = pd.read_csv(result_file)
                    if not params_df.empty:
                        chandelier_period = int(params_df.iloc[0]['period'])
                        chandelier_mult = float(params_df.iloc[0]['mult'])
                    else:
                        chandelier_period = 14
                        chandelier_mult = 2.0
                else:
                    chandelier_period = 14
                    chandelier_mult = 2.0
            except Exception as e:
                chandelier_period = 14
                chandelier_mult = 2.0
            
            # 计算ATR
            atr = talib.ATR(temp_df['High'].values,
                          temp_df['Low'].values,
                          temp_df['Close'].values,
                          timeperiod=chandelier_period)
            
            # 计算最高价和最低价
            high = temp_df['Close'].rolling(window=chandelier_period).max()
            low = temp_df['Close'].rolling(window=chandelier_period).min()
            
            # 初始化多头止损和空头止损
            long_stop = pd.Series(index=temp_df.index)
            short_stop = pd.Series(index=temp_df.index)
            
            # 第一个有效值的计算
            first_valid = chandelier_period - 1
            long_stop.iloc[first_valid] = high.iloc[first_valid] - (atr[first_valid] * chandelier_mult)
            short_stop.iloc[first_valid] = low.iloc[first_valid] + (atr[first_valid] * chandelier_mult)
            
            # 动态调整止损点
            for i in range(first_valid + 1, len(temp_df)):
                # 计算当前的基础止损点
                current_long_stop = high.iloc[i] - (atr[i] * chandelier_mult)
                current_short_stop = low.iloc[i] + (atr[i] * chandelier_mult)
                
                # 动态调整多头止损点
                if temp_df['Close'].iloc[i] > long_stop.iloc[i-1]:
                    long_stop.iloc[i] = max(current_long_stop, long_stop.iloc[i-1])
                else:
                    long_stop.iloc[i] = current_long_stop
                
                # 动态调整空头止损点
                if temp_df['Close'].iloc[i] < short_stop.iloc[i-1]:
                    short_stop.iloc[i] = min(current_short_stop, short_stop.iloc[i-1])
                else:
                    short_stop.iloc[i] = current_short_stop
            
            # 保存计算结果
            temp_df['ATR'] = atr
            temp_df['周期'] = chandelier_period
            temp_df['倍数'] = chandelier_mult
            temp_df['多头止损'] = long_stop  # 现在使用的是动态调整后的止损点
            temp_df['空头止损'] = short_stop  # 现在使用的是动态调整后的止损点
        # 只返回请求的日期范围的数据
        df = temp_df[start_date:end_date].copy()
        return df
    
    return stock_data

def _get_stock_data_baostock(symbol, start_date, end_date):
    """使用baostock获取股票数据"""
    try:
        # 登录baostock
        # baostock不需要账号密码,直接调用login()即可
        # 返回值为BaoStockLoginResult对象,可以通过error_code和error_msg查登录状态
        login_result = bs.login()
        if login_result.error_code != '0':
            print(f'baostock登录失败: {login_result.error_msg}')
            return pd.DataFrame()
        
        # baostock需要特定格式的股票代码
        if symbol.startswith('6'):
            bs_symbol = f"sh.{symbol}"
        else:
            bs_symbol = f"sz.{symbol}"
            
        # 获取数据
        rs = bs.query_history_k_data_plus(
            bs_symbol,
            "date,open,high,low,close,volume,amount,pctChg",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="2"  # 前复权
        )
        
        if rs.error_code != '0':
            print(f"baostock获取数据失败: {rs.error_msg}")
            return pd.DataFrame()
            
        # 转换为DataFrame
        stock_data = pd.DataFrame(rs.data, columns=rs.fields)
        
        if stock_data.empty:
            print(f"股票 {symbol} 无有效数据。")
            return pd.DataFrame()
            
        # 重命名列
        stock_data.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'close': 'Close',
            'high': 'High',
            'low': 'Low',
            'volume': 'Volume',
            'amount': 'Amount',
            'pctChg': 'Pct_change'
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
    finally:
        # 退出baostock
        bs.logout()

def _get_stock_data_akshare(symbol, start_date, end_date):
    """使用akshare获取股票数据（原有的实现）"""
    try:
        # 获取数据，复权类型为前复权（qfq）
        stock_data = ak.stock_zh_a_hist(
            symbol=symbol, 
            period="daily", 
            start_date=start_date.replace('-', ''), 
            end_date=end_date.replace('-', ''), 
            adjust="qfq"
        )
        
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
        
        # 将数据类型转换为数类型
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
            '成量': 'Volume',
            '成交额': 'Amount',
            '涨跌幅': 'Pct_change'
        }, inplace=True)
        
        # 将'Date'列转换为日期格式并置为索引
        etf_data['Date'] = pd.to_datetime(etf_data['Date'])
        etf_data.set_index('Date', inplace=True)
        
        # 将数据类型换为数值类型
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
        
        # 筛选出A股ETF（假设A股ETF的代码以'5'或'1'开头
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
                '今日涨幅': f'{period}_change_pct',
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
            
        # 只返回股票代码code，和股票名称name，并将字名称改名为英文名称
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
            '最新': 'price',
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

def get_stock_basic_info(stock_code: str) -> dict:
    """
    获取股票的基本信息，包括总市值、流通市值、行业等
    
    参数:
        stock_code (str): 股票代码，例如 "000001"
        
    返回:
        dict: 包含股票基本信息的字典，包括以下字段:
            - 总市值 (float): 单位为亿元
            - 流通市值 (float): 单位为亿元
            - 行业 (str): 所属行业
            - 上市时间 (str): 格式为YYYYMMDD
            - 股票代码 (str)
            - 股票简称 (str)
            - 总股本 (float): 单位为亿股
            - 流通股 (float): 单位为亿股
    """
    try:
        # 获取股票信息
        df = ak.stock_individual_info_em(symbol=stock_code)
        
        # 将 DataFrame 转换为字典
        info_dict = dict(zip(df['item'], df['value']))
        
        # 格式化数值
        if '总市值' in info_dict:
            info_dict['总市值'] = float(info_dict['总市值']) / 100000000  # 转换为亿元
        if '流通市值' in info_dict:
            info_dict['流通市值'] = float(info_dict['流通市值']) / 100000000  # 转换为亿元
        if '总股本' in info_dict:
            info_dict['总股本'] = float(info_dict['总股本']) / 100000000  # 转换为亿股
        if '流通股' in info_dict:
            info_dict['流通股'] = float(info_dict['流通股']) / 100000000  # 转换为亿股
            
        return info_dict
    except Exception as e:
        print(f"获取股票 {stock_code} 的基本信息时发生错误: {str(e)}")
        return {}

def get_stock_news(stock_code: str, limit: int = 10) -> list:
    """
    获取指定股票的新闻资讯
    
    参数:
        stock_code (str): 股票代码，例如 "300059"
        limit (int): 返回的新闻条数，默认10条，最大100条
        
    返回:
        list: 包含新闻信息的列表，每条新闻为一个字典，包含以下字段:
            - keyword (str): 关键词
            - title (str): 新闻标题
            - content (str): 新闻内容
            - publish_time (str): 发布时间
            - source (str): 文章来源
            - url (str): 新闻链接
    """
    try:
        # 获取新闻数据
        df = ak.stock_news_em(symbol=stock_code)
        
        # 重命名列
        df = df.rename(columns={
            '关键词': 'keyword',
            '新闻标题': 'title',
            '新闻内容': 'content',
            '发布时间': 'publish_time',
            '文章来源': 'source',
            '新闻链接': 'url'
        })
        
        # 限制返回条数
        df = df.head(min(limit, len(df)))
        
        # 转换为字典列表
        news_list = df.to_dict('records')
        
        # 清理数据：去除多余的空白字符
        for news in news_list:
            for key, value in news.items():
                if isinstance(value, str):
                    news[key] = value.strip()
        
        return news_list
        
    except Exception as e:
        print(f"获取股票 {stock_code} 的新闻信息时发生错误: {str(e)}")
        return []

def get_industry_market_data():
    """
    获取行业市场数据
    
    返回：
    - DataFrame，包含以下列：
        - industry_name: 行业名称（板块名称）
        - price: 最新价
        - change: 涨跌额
        - change_pct: 涨跌幅
        - market_value: 总市值
        - turnover_rate: 换手率
        - up_count: 上涨家数
        - down_count: 下跌家数
        - leading_stock: 领涨股票
        - leading_stock_pct: 领涨股票涨跌幅
    """
    try:
        # 使用 akshare 获取行业行情数据
        industry_data = ak.stock_board_industry_name_em()
        
        if industry_data.empty:
            print("未获取到行业数据")
            return pd.DataFrame()
        
        # 重命名列以匹配预期的格式
        column_mapping = {
            '板块名称': 'industry_name',
            '最新价': 'price',
            '涨跌额': 'change',
            '涨跌幅': 'change_pct',
            '总市值': 'market_value',
            '换手率': 'turnover_rate',
            '上涨家数': 'up_count',
            '下跌家数': 'down_count',
            '领涨股票': 'leading_stock',
            '领涨股票-涨跌幅': 'leading_stock_pct'
        }
        
        # 选择需要的列并重命名
        industry_data = industry_data[list(column_mapping.keys())].rename(columns=column_mapping)
        
        # 转换数值类型列
        numeric_columns = ['price', 'change', 'change_pct', 'market_value', 
                         'turnover_rate', 'up_count', 'down_count', 'leading_stock_pct']
        for col in numeric_columns:
            industry_data[col] = pd.to_numeric(
                industry_data[col].astype(str)
                .str.replace(',', '')
                .str.replace('%', '')
                .str.replace('亿', '')
                .str.replace('万', '')
                .str.replace('--', 'NaN')
                .replace('', 'NaN'),
                errors='coerce'
            )
            
        # 将百分比列除以100
        percentage_columns = ['change_pct', 'turnover_rate', 'leading_stock_pct']
        for col in percentage_columns:
            industry_data[col] = industry_data[col] / 100
            
        return industry_data
        
    except Exception as e:
        print(f"获取行业市场数据失败: {e}")
        return pd.DataFrame()

def get_industry_detail_data(industry_name: str) -> pd.DataFrame:
    """
    获取指定行业的详细市场数据，包括该行业的历史走势

    参数:
        industry_name (str): 行业名称，例如"半导体"

    返回:
        DataFrame: 包含以下字段:
            - date: 日期
            - close: 收盘点数
            - change_pct: 涨跌幅(%)
            - volume: 成交量(万手)
            - amount: 成交额(亿元)
            - turnover_rate: 换手率(%)
    """
    try:
        print(f"开始获取{industry_name}行业的详细数据...")
        
        # 获取行业历史数据
        industry_detail = ak.stock_board_industry_hist_em(
            symbol=industry_name,
            start_date="20240101",
            end_date=datetime.now().strftime("%Y%m%d")
        )
        
        # 重命名列
        industry_detail = industry_detail.rename(columns={
            '日期': 'date',
            '收盘': 'close',
            '涨跌幅': 'change_pct',
            '成交量': 'volume',
            '成交额': 'amount',
            '换手率': 'turnover_rate'
        })
        
        # 转换日期格式
        industry_detail['date'] = pd.to_datetime(industry_detail['date'])
        
        # 转换数据类型
        numeric_columns = ['close', 'change_pct', 'volume', 'amount', 'turnover_rate']
        for col in numeric_columns:
            industry_detail[col] = pd.to_numeric(industry_detail[col], errors='coerce')
            
        # 单位转换：
        # 成交量转换为万手
        industry_detail['volume'] = industry_detail['volume'] / 10000
        # 成交额转换为亿元
        industry_detail['amount'] = industry_detail['amount'] / 100000000
        
        print(f"成功获取{industry_name}行业的详细数据，共 {len(industry_detail)} 条记录")
        return industry_detail
        
    except Exception as e:
        print(f"获取{industry_name}行业详细数据时发生错误: {str(e)}")
        return pd.DataFrame()

def get_hot_industries(min_change_pct=0.015, min_up_count=5):
    """
    获取热门行业数据
    
    参数:
        min_change_pct (float): 最小涨跌幅阈值，默认1.5%
        min_up_count (int): 最小上涨家数阈值，默认5家
        
    返回:
        list: 热门行业列表，每个元素为字典，包含行业名称和主力资金净流入等信息
    """
    try:
        print("正在获取热门行业数据...")
        
        # 获取行业行情数据
        industry_data = ak.stock_board_industry_name_em()
        
        if industry_data.empty:
            print("未获取到行业数据")
            return []
            
        # 打印实际的列名，帮助调试
        print("实际的列名:", industry_data.columns.tolist())
        
        # 根据实际返回的列名进行映射
        column_mapping = {
            '板块名称': 'industry_name',
            '涨跌幅': 'change_pct',
            '上涨家数': 'up_count',
            '总市值': 'market_value',
            '换手率': 'turnover_rate'
        }
        
        # 检查所需的列是否存在
        missing_columns = [col for col in column_mapping.keys() 
                         if col not in industry_data.columns]
        if missing_columns:
            print(f"缺少以下列: {missing_columns}")
            print("可用的列:", industry_data.columns.tolist())
            return []
        
        # 重命名列
        industry_data = industry_data[list(column_mapping.keys())].rename(columns=column_mapping)
        
        # 转换数值类型
        industry_data['change_pct'] = pd.to_numeric(
            industry_data['change_pct'].str.replace('%', ''), 
            errors='coerce'
        ) / 100
        
        industry_data['up_count'] = pd.to_numeric(
            industry_data['up_count'], 
            errors='coerce'
        )
        
        # 筛选热门行业
        hot_industries = industry_data[
            (industry_data['change_pct'] >= min_change_pct) & 
            (industry_data['up_count'] >= min_up_count)
        ]
        
        if hot_industries.empty:
            print("未找到符合条件的热门行业")
            return []
            
        # 转换为字典列表
        result = hot_industries.to_dict('records')
        
        print(f"找到 {len(result)} 个热门行业")
        return result
        
    except Exception as e:
        print(f"获取热门行业数据失败: {str(e)}")
        if 'industry_data' in locals():
            print("列名:", industry_data.columns.tolist())
        return []
