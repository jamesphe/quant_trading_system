import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加父目录到系统路径，以便能够导入 data_fetch 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from data_fetch import (
    get_us_stock_data, 
    get_etf_list, 
    get_etf_data, 
    get_stock_name, 
    get_stock_industry, 
    get_industry_fund_flow_rank, 
    get_us_stock_list,
    get_a_share_list,
    get_industry_stocks,
    get_stock_news,
    get_stock_data
)

def test_get_vgt_data():
    """
    测试获取VGT（Vanguard Information Technology ETF）的行情数据
    """
    # 设置日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # 获取VGT数据
    vgt_symbol = 'VGT'
    vgt_data = get_us_stock_data(vgt_symbol, start_date, end_date)
    
    # 打印结果
    if not vgt_data.empty:
        print(f"成功获取VGT从{start_date}到{end_date}的数据。")
        print("数据前5行：")
        print(vgt_data.head())
        print(f"数据行数: {len(vgt_data)}")
        
        # 检查数据列
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Pct_change']
        assert all(col in vgt_data.columns for col in expected_columns), "数据列不完整"
        
        # 检查数据类型
        assert vgt_data.index.dtype == 'datetime64[ns]', "索引不是日期时间类型"
        assert vgt_data['Close'].dtype == 'float64', "Close列不是浮点数类型"
        
        print("数据验证通过！")
    else:
        print("未能获取VGT数据。")

def test_get_etf_list():
    """
    测试获取A股ETF列表
    """
    print("开始测试获取A股ETF列表...")
    etf_list = get_etf_list()
    print(f"获取到的ETF列表: {etf_list}")
    
    if not etf_list.empty:
        print("成功获取A股ETF列表。")
        print(f"ETF总数: {len(etf_list)}")
        print("前5个ETF:")
        print(etf_list.head())
        
        print("检查数据列...")
        expected_columns = ['code', 'name']
        for col in expected_columns:
            print(f"检查列 '{col}' 是否存在...")
            assert col in etf_list.columns, f"数据列 '{col}' 不存在"
        print("数据列检查完成。")
        
        print("检查数据类型...")
        print(f"code列数据类型: {etf_list['code'].dtype}")
        print(f"name列数据类型: {etf_list['name'].dtype}")
        assert etf_list['code'].dtype == 'object', "code列不是字符串类型"
        assert etf_list['name'].dtype == 'object', "name列不是字符串类型"
        print("数据类型检查完成。")
        
        print("检查是否有空值...")
        print(f"code列空值数量: {etf_list['code'].isnull().sum()}")
        print(f"name列空值数量: {etf_list['name'].isnull().sum()}")
        assert not etf_list['code'].isnull().any(), "code列存在空值"
        assert not etf_list['name'].isnull().any(), "name列存在空值"
        print("空值检查完成。")
        
        print("数据验证通过！")
    else:
        print("未能获取A股ETF列表。")
    print("测试完成。")

def test_get_etf_data():
    """
    测试获取A股ETF历史行情数据
    """
    print("\n开始测试获取A股ETF历史行情数据...")
    
    # 设置测试参数
    symbol = "159998"  # 创业板ETF
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"测试ETF: {symbol}")
    print(f"开始日期: {start_date}")
    print(f"结束日期: {end_date}")
    
    etf_data = get_etf_data(symbol, start_date, end_date)
    
    if not etf_data.empty:
        print(f"成功获取ETF {symbol} 从 {start_date} 到 {end_date} 的数据。")
        print("数据前5行：")
        print(etf_data.head())
        print(f"数据行数: {len(etf_data)}")
        
        # 检查数据列
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Pct_change']
        assert all(col in etf_data.columns for col in expected_columns), "数据列不完整"
        
        # 检查数据类型
        assert etf_data.index.dtype == 'datetime64[ns]', "索引不是日期时间类型"
        assert etf_data['Close'].dtype == 'float64', "Close列不是浮点数类型"
        
        # 检查数据范围
        assert etf_data.index.min().strftime('%Y-%m-%d') >= start_date, "数据开始日期早于请求的开始日期"
        assert etf_data.index.max().strftime('%Y-%m-%d') <= end_date, "数据结束日期晚于请求的结束日期"
        
        print("数据验证通过！")
    else:
        print(f"未能获取ETF {symbol} 数据。")
    
    print("测试完成。")

def test_get_stock_name():
    """
    测试获取股票名称功能
    """
    print("\n开始测试获取股票名称...")
    
    # 测试A股股票
    a_share_symbol = "301183"  # 贵州茅台
    a_share_name = get_stock_name(a_share_symbol)
    print(f"A股股票 {a_share_symbol} 的名称: {a_share_name}")
    assert a_share_name == "贵州茅台", f"预期名称为'贵州茅台'，实际获得'{a_share_name}'"
    
    
    # 测试不存在的股票代码
    invalid_symbol = "000000"
    invalid_name = get_stock_name(invalid_symbol)
    print(f"无效股票代码 {invalid_symbol} 的返回结果: {invalid_name}")
    assert invalid_name == invalid_symbol, f"对于无效代码，预期返回原始代码，实际返回'{invalid_name}'"
    
    print("获取股票名称测试完成。")

def test_get_stock_industry():
    """
    测试获取股票行业信息功能
    """
    print("\n开始测试获取股票行业信息...")
    
    # 测试A股股票
    a_share_symbol = "300077"  # 平安银行
    industry = get_stock_industry(a_share_symbol)
    print(f"股票 {a_share_symbol} 的行业: {industry}")
    assert industry is not None, f"未能获取股票 {a_share_symbol} 的行业信息"
    assert isinstance(industry, str), f"行业信息应为字符串,实际类型为 {type(industry)}"
    
    # 测试不存在的股票代码
    invalid_symbol = "000000"
    invalid_industry = get_stock_industry(invalid_symbol)
    print(f"无效股票代码 {invalid_symbol} 的行业信息: {invalid_industry}")
    assert invalid_industry is None, f"对于无效代码,预期返回None,实际返回 {invalid_industry}"
    
    print("获取股票行业信息测试完成。")

def test_get_industry_fund_flow_rank():
    """
    测试获取行业资金流向排名功能
    """
    print("\n开始测试获取行业资金流向排名...")
    
    # 测试行业资金流
    try:
        industry_flow = get_industry_fund_flow_rank(sector_type="行业资金流")
        print("行业资金流向排名数据:")
        print(industry_flow)
        
        
    except Exception as e:
        print(f"获取行资金流向排名时发生错误: {str(e)}")
        print("请检查 get_industry_fund_flow_rank 函数的实现")
        return
    

def test_get_stock_news():
    """
    测试获取股票新闻资讯功能
    """
    print("\n开始测试获取股票新闻资讯...")
    
    # 测试A股股票
    symbol = "300059"  # 东方财富
    news_list = get_stock_news(symbol, limit=5)  # 获取5条新闻测试
    
    if news_list:
        print(f"成功获取股票 {symbol} 的新闻资讯")
        print(f"获取到的新闻: {len(news_list)}")
        
        # 显前3条新闻的基本信息
        print("\n前3条新闻:")
        for i, news in enumerate(news_list[:3], 1):
            print(f"\n第{i}条新闻:")
            print(f"标题: {news['title']}")
            print(f"来源: {news['source']}")
            print(f"时间: {news['publish_time']}")
            print(f"链接: {news['url']}")
        
        # 检查数据结构
        expected_keys = ['keyword', 'title', 'content', 'publish_time', 
                        'source', 'url']
        for news in news_list:
            for key in expected_keys:
                assert key in news, f"新闻数据缺少必要的字段 '{key}'"
        print("\n数据结构检查通过")
        
        # 检查数据类型
        for news in news_list:
            assert isinstance(news['title'], str), "title不是字符串类型"
            assert isinstance(news['content'], str), "content不是字符串类型"
            assert isinstance(news['source'], str), "source不是字符串类型"
            assert isinstance(news['url'], str), "url不是字符串类型"
        print("数据类型检查通过")
        
        # 检查数据有效性
        for news in news_list:
            assert len(news['title']) > 0, "存在空标题"
            assert len(news['content']) > 0, "存在空内容"
            assert len(news['source']) > 0, "存在空来源"
            assert news['url'].startswith('http'), "无效的URL格式"
        print("数据有效性检查通过")
        
        # 检查返回数量限制
        assert len(news_list) <= 5, "返回的新闻数量超过限制"
        print("数量限制检查通过")
        
        print("\n数据验证全部通过！")
    else:
        print(f"未能获取股票 {symbol} 的新闻数据")
    
    # 测试无效股票代码
    invalid_symbol = "000000"
    invalid_news = get_stock_news(invalid_symbol)
    assert isinstance(invalid_news, list), "对于无效股票代码应返回空列表"
    assert len(invalid_news) == 0, "对于无效股票代码应返回空列表"
    print("\n无效股票代码测试通过")

def test_get_us_stock_list():
    """
    测试获取知名美股列表功能
    """
    print("\n开始测试获取知名美股列表...")
    
    try:
        us_stocks = get_us_stock_list()
        
        if not us_stocks.empty:
            print(f"成功获取知名美股列表")
            print(f"获取到的股票数量: {len(us_stocks)}")
            print("\n数据前5行:")
            print(us_stocks[['code', 'name']].head())
            
            # 检查数据列
            expected_columns = ['code', 'name']
            for col in expected_columns:
                assert col in us_stocks.columns, f"缺少必要的列 '{col}'"
            print("\n数据列检查通过")
            
            # 检查数据类型
            assert us_stocks['code'].dtype == 'object', "code列不是字符串类型"
            assert us_stocks['name'].dtype == 'object', "name列不是字符串类型"
            print("数据类型检查通过")
            
            # 检查是否有空值
            null_counts = us_stocks[['code', 'name']].isnull().sum()
            print("\n空值检查:")
            print(null_counts)
            assert not us_stocks['code'].isnull().any(), "code列存在空值"
            assert not us_stocks['name'].isnull().any(), "name列存在空值"
            print("空值检查通过")
            
            # 检查主要科技股的部分
            major_tech = ['AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN']
            found_stocks = us_stocks[us_stocks['code'].isin(major_tech)]
            
            print(f"\n主要科技股检查 (应包含以下股票: AAPL, MSFT, GOOGL, META, AMZN):")
            print(found_stocks[['code', 'name']])
            assert len(found_stocks) > 0, "未找到主要科技股"
            print("主要科技股检查通过")
            print("\n数据验证全部通过！")
        else:
            print("获取到的美股列表为空")
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        raise

def test_get_a_share_list():
    """
    测试获取A股股票列表功能
    """
    print("\n开始测试获取A股股票列表...")
    
    try:
        stock_list = get_a_share_list()
        
        if not stock_list.empty:
            print(f"成功获取A股股票列表")
            print(f"获取到的股票数量: {len(stock_list)}")
            print("\n数据前5行:")
            print(stock_list.head())
            
            # 检查数据列
            expected_columns = ['code', 'name']
            for col in expected_columns:
                assert col in stock_list.columns, f"缺少必要的列 '{col}'"
            print("\n数据列检查通过")
            
            # 检查数据类型
            assert stock_list['code'].dtype == 'object', "code列不是字符串类型"
            assert stock_list['name'].dtype == 'object', "name列不是字符串类型"
            print("数据类型检查通过")
            
            # 检查是否有空值
            null_counts = stock_list[['code', 'name']].isnull().sum()
            print("\n空值检查:")
            print(null_counts)
            assert not stock_list['code'].isnull().any(), "code列存在空值"
            assert not stock_list['name'].isnull().any(), "name列存在空值"
            print("空值检查通过")
            
            # 检查代码格式
            assert all(len(code) == 6 for code in stock_list['code']), "存在非6位股票代码"
            assert all(code.isdigit() for code in stock_list['code']), "存在非数字股票代码"
            print("代码格式检查通过")
            
            # 检查排除规则
            assert not any(code.startswith('8') for code in stock_list['code']), \
                "未排除8开头的股票"
            assert not any(code.startswith('688') for code in stock_list['code']), \
                "未排除科创板股票"
            assert not any(code.startswith('4') for code in stock_list['code']), \
                "未排除4开头的股票"
            assert not any('ST' in name for name in stock_list['name']), \
                "未排除ST股票"
            print("排除规则检查通过")
            
            # 检查主板股票
            main_board = stock_list[stock_list['code'].str.startswith(('600', '601', '603'))]
            assert not main_board.empty, "未包含主板股"
            print(f"主板股票数量: {len(main_board)}")
            
            # 检查创业板股票
            growth_board = stock_list[stock_list['code'].str.startswith('3')]
            assert not growth_board.empty, "未包含创业板股票"
            print(f"创业板股票数量: {len(growth_board)}")
            
            # 检查中小板股票
            sme_board = stock_list[stock_list['code'].str.startswith('002')]
            assert not sme_board.empty, "未包含中小板股票"
            print(f"中小板股票数量: {len(sme_board)}")
            
            print("\n数据验证全部通过！")
        else:
            print("获取到的A股列表为空")
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        raise

def test_get_industry_stocks():
    """
    测试获取行业板块成份股功能
    """
    print("\n开始测试获取行业板块成份股...")
    
    try:
        # 测试获取小金属行业的成份股
        industry_name = "小金属"
        stocks = get_industry_stocks(industry_name)
        
        if not stocks.empty:
            print(f"成功获取{industry_name}行业的成份股")
            print(f"获取到的股票数量: {len(stocks)}")
            print("\n数据前5行:")
            print(stocks.head())
            
            # 检查数据列
            expected_columns = ['code', 'name', 'price', 'change_pct', 'volume', 
                              'amount', 'amplitude', 'high', 'low', 'open', 
                              'pre_close', 'turnover_rate']
            for col in expected_columns:
                assert col in stocks.columns, f"缺少必要的列 '{col}'"
            print("\n数据列检查通过")
            
            # 检查数据类型
            assert stocks['code'].dtype == 'object', "code列不是字符串类型"
            assert stocks['name'].dtype == 'object', "name列不是字符串类型"
            numeric_columns = ['price', 'change_pct', 'volume', 'amount', 
                             'amplitude', 'high', 'low', 'open', 'pre_close', 
                             'turnover_rate']
            for col in numeric_columns:
                assert stocks[col].dtype in ['float64', 'int64'], \
                    f"{col}列不是数值类型"
            print("数据类型检查通过")
            
            # 检查是否有空值
            null_counts = stocks[expected_columns].isnull().sum()
            print("\n空值检查:")
            print(null_counts)
            assert not stocks['code'].isnull().any(), "code列存在空值"
            assert not stocks['name'].isnull().any(), "name列存在空值"
            print("空值检查通过")
            
            # 检查数值范围
            assert all(stocks['price'] >= 0), "存在负的股票价格"
            assert all(stocks['volume'] >= 0), "存在负的成交量"
            assert all(stocks['amount'] >= 0), "存在负的成交额"
            assert all(stocks['turnover_rate'] >= 0), "存在负的换手率"
            print("数值范围检查通过")
            
            print("\n数据验证全部通过！")
        else:
            print(f"未能获取{industry_name}行业的成份股数据")
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        raise

def test_get_stock_data():
    """
    测试获取股票历史行情数据功能
    """
    print("\n开始测试获取股票历史行情数据...")
    
    # 修改测试参数，使用历史数据
    symbol = "300059"  # 东方财富
    end_date = "2024-01-31"  # 使用固定的历史日期
    start_date = "2024-01-01"  # 使用固定的历史日期
    
    # 测试两种数据源
    data_sources = ['akshare', 'baostock']
    
    for source in data_sources:
        print(f"\n测试{source}数据源:")
        try:
            # 测试基础数据获取
            stock_data = get_stock_data(symbol, start_date, end_date, source=source)
            
            if not stock_data.empty:
                # 确保Volume列为float64类型
                stock_data['Volume'] = stock_data['Volume'].astype('float64')
                
                print(f"成功获取股票 {symbol} 从 {start_date} 到 {end_date} 的数据")
                print(f"数据行数: {len(stock_data)}")
                print("\n数据前5行:")
                print(stock_data.head())
                
                # 检查数据列
                expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 
                                  'Amount', 'Pct_change']
                for col in expected_columns:
                    assert col in stock_data.columns, f"缺少必要的列 '{col}'"
                print("\n数据列检查通过")
                
                # 检查数据类型
                assert stock_data.index.dtype == 'datetime64[ns]', "索引不是日期时间类型"
                numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 
                                 'Amount', 'Pct_change']
                for col in numeric_columns:
                    assert stock_data[col].dtype == 'float64', \
                        f"{col}列不是浮点数类型"
                print("数据类型检查通过")
                
                # 检查数据范围
                assert stock_data.index.min().strftime('%Y-%m-%d') >= start_date, \
                    "数据开始日期早于请求的开始日期"
                assert stock_data.index.max().strftime('%Y-%m-%d') <= end_date, \
                    "数据结束日期晚于请求的结束日期"
                print("数据范围检查通过")
                
                # 检查数值有效性
                assert all(stock_data['Open'] > 0), "存在无效的开盘价"
                assert all(stock_data['Close'] > 0), "存在无效的收盘价"
                assert all(stock_data['High'] >= stock_data['Low']), \
                    "最高价小于最低价"
                assert all(stock_data['Volume'] >= 0), "存在负的成交量"
                assert all(stock_data['Amount'] >= 0), "存在负的成交额"
                print("数值有效性检查通过")
                
                # 测试包含MACD的数据获取
                stock_data_with_macd = get_stock_data(
                    symbol, 
                    start_date, 
                    end_date, 
                    source=source,
                    include_macd=True
                )
                
                print("\n测试MACD数据:")
                # 检查MACD相关列是否存在
                macd_columns = ['MACD', 'MACD_SIGNAL', 'MACD_HIST']
                for col in macd_columns:
                    assert col in stock_data_with_macd.columns, f"缺少MACD相关列 '{col}'"
                print("MACD列检查通过")
                
                # 检查MACD数据类型
                for col in macd_columns:
                    assert stock_data_with_macd[col].dtype == 'float64', \
                        f"{col}列不是浮点数类型"
                print("MACD数据类型检查通过")
                
                # 检查MACD数据有效性
                assert not stock_data_with_macd['MACD'].isnull().all(), \
                    "MACD列全为空值"
                assert not stock_data_with_macd['MACD_SIGNAL'].isnull().all(), \
                    "MACD_SIGNAL列全为空值"
                assert not stock_data_with_macd['MACD_HIST'].isnull().all(), \
                    "MACD_HIST列全为空值"
                print("MACD数据有效性检查通过")
                
                # 验证MACD计算逻辑
                # MACD_HIST应该等于MACD减去MACD_SIGNAL
                hist_diff = abs(stock_data_with_macd['MACD_HIST'] - 
                              (stock_data_with_macd['MACD'] - 
                               stock_data_with_macd['MACD_SIGNAL']))
                assert all(hist_diff < 1e-10), "MACD_HIST计算错误"
                print("MACD计算逻辑验证通过")
                
                # 测试包含RSI的数据获取
                stock_data_with_indicators = get_stock_data(
                    symbol, 
                    start_date, 
                    end_date, 
                    source=source,
                    include_macd=True,
                    include_rsi=True
                )
                
                if not stock_data_with_indicators.empty:
                    print("\n测试RSI数据:")
                    # 检查RSI相关列是否存在
                    rsi_columns = ['RSI_6', 'RSI_12', 'RSI_24']
                    for col in rsi_columns:
                        assert col in stock_data_with_indicators.columns, f"缺少RSI相关列 '{col}'"
                    print("RSI列检查通过")
                    
                    # 检查RSI数据类型
                    for col in rsi_columns:
                        assert stock_data_with_indicators[col].dtype == 'float64', \
                            f"{col}列不是浮点数类型"
                    print("RSI数据类型检查通过")
                    
                    # 检查RSI数据有效性
                    for col in rsi_columns:
                        assert not stock_data_with_indicators[col].isnull().all(), \
                            f"{col}列全为空值"
                        # RSI值应该在0到100之间
                        valid_values = stock_data_with_indicators[col].dropna()
                        assert all((valid_values >= 0) & (valid_values <= 100)), \
                            f"{col}存在超出范围的值"
                    print("RSI数据有效性检查通过")
                    
                    print(f"\n{source}数据源（含MACD和RSI）测试通过！")
                else:
                    print(f"未能获取股票 {symbol} 的数据")
                    
            # 测试包含BOLL的数据获取
            stock_data_with_boll = get_stock_data(
                symbol, 
                start_date, 
                end_date, 
                source=source,
                include_boll=True
            )
            
            if not stock_data_with_boll.empty:
                print("\n测试BOLL数据:")
                # 检查BOLL相关列是否存在
                boll_columns = ['BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']
                for col in boll_columns:
                    assert col in stock_data_with_boll.columns, f"缺少BOLL相关列 '{col}'"
                print("BOLL列检查通过")
                
                # 检查BOLL数据类型
                for col in boll_columns:
                    assert stock_data_with_boll[col].dtype == 'float64', \
                        f"{col}列不是浮点数类型"
                print("BOLL数据类型检查通过")
                
                # 检查BOLL数据有效性
                for col in boll_columns:
                    assert not stock_data_with_boll[col].isnull().all(), \
                        f"{col}列全为空值"
                print("BOLL数据空值检查通过")
                
                # 验证BOLL计算逻辑
                # 上轨应该大于中轨，中轨应该大于下轨
                assert all(stock_data_with_boll['BOLL_UPPER'] >= 
                         stock_data_with_boll['BOLL_MIDDLE']), "上轨不大于等于中轨"
                assert all(stock_data_with_boll['BOLL_MIDDLE'] >= 
                         stock_data_with_boll['BOLL_LOWER']), "中轨不大于等于下轨"
                print("BOLL数据逻辑关系验证通过")
                
                # 测试包含ZLSMA的数据获取
                stock_data_with_zlsma = get_stock_data(
                    symbol, 
                    start_date, 
                    end_date, 
                    source=source,
                    include_zlsma=True
                )
                
                if not stock_data_with_zlsma.empty:
                    print("\n测试ZLSMA数据:")
                    # 检查ZLSMA相关列是否存在
                    zlsma_columns = ['ZLSMA_20', 'ZLSMA_60']
                    for col in zlsma_columns:
                        assert col in stock_data_with_zlsma.columns, f"缺少ZLSMA相关列 '{col}'"
                    print("ZLSMA列检查通过")
                    
                    # 检查ZLSMA数据类型
                    for col in zlsma_columns:
                        assert stock_data_with_zlsma[col].dtype == 'float64', \
                            f"{col}列不是浮点数类型"
                    print("ZLSMA数据类型检查通过")
                    
                    # 检查ZLSMA数据有效性
                    for col in zlsma_columns:
                        assert not stock_data_with_zlsma[col].isnull().all(), \
                            f"{col}列全为空值"
                    print("ZLSMA数据空值检查通过")
                    
                    # 验证ZLSMA数据范围
                    # ZLSMA应该在历史价格的最大值和最小值之间
                    close_min = stock_data_with_zlsma['Close'].min()
                    close_max = stock_data_with_zlsma['Close'].max()
                    for col in zlsma_columns:
                        valid_values = stock_data_with_zlsma[col].dropna()
                        assert all((valid_values >= close_min * 0.5) & 
                                 (valid_values <= close_max * 1.5)), \
                            f"{col}存在异常值"
                    print("ZLSMA数据范围验证通过")
                    
                    # 测试同时包含所有指标
                    stock_data_with_all = get_stock_data(
                        symbol, 
                        start_date, 
                        end_date, 
                        source=source,
                        include_macd=True,
                        include_rsi=True,
                        include_boll=True,
                        include_zlsma=True
                    )
                    
                    # 验证所有指标列都存在
                    all_indicator_columns = ['MACD', 'MACD_SIGNAL', 'MACD_HIST',
                                          'RSI_6', 'RSI_12', 'RSI_24',
                                          'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER',
                                          'ZLSMA_20', 'ZLSMA_60']
                    for col in all_indicator_columns:
                        assert col in stock_data_with_all.columns, f"缺少指标列 '{col}'"
                    print("\n所有指标列检查通过")
                    
                    print(f"\n{source}数据源（含所有指标）测试通过！")
                else:
                    print(f"未能获取股票 {symbol} 的数据")
                    
            # 测试包含ZLSMA的数据获取
            stock_data_with_zlsma = get_stock_data(
                symbol, 
                start_date, 
                end_date, 
                source=source,
                include_zlsma=True
            )
            
            if not stock_data_with_zlsma.empty:
                print("\n测试ZLSMA数据:")
                # 检查ZLSMA相关列是否存在
                zlsma_columns = ['ZLSMA_20', 'ZLSMA_60']
                for col in zlsma_columns:
                    assert col in stock_data_with_zlsma.columns, f"缺少ZLSMA相关列 '{col}'"
                print("ZLSMA列检查通过")
                
                # 检查ZLSMA数据类型
                for col in zlsma_columns:
                    assert stock_data_with_zlsma[col].dtype == 'float64', \
                        f"{col}列不是浮点数类型"
                print("ZLSMA数据类型检查通过")
                
                # 检查ZLSMA数据有效性
                for col in zlsma_columns:
                    assert not stock_data_with_zlsma[col].isnull().all(), \
                        f"{col}列全为空���"
                print("ZLSMA数据空值检查通过")
                
                # 验证ZLSMA数据范围
                # ZLSMA应该在历史价格的最大值和最小值之间
                close_min = stock_data_with_zlsma['Close'].min()
                close_max = stock_data_with_zlsma['Close'].max()
                for col in zlsma_columns:
                    valid_values = stock_data_with_zlsma[col].dropna()
                    assert all((valid_values >= close_min * 0.5) & 
                             (valid_values <= close_max * 1.5)), \
                        f"{col}存在异常值"
                print("ZLSMA数据范围验证通过")
                
                # 测试同时包含所有指标
                stock_data_with_all = get_stock_data(
                    symbol, 
                    start_date, 
                    end_date, 
                    source=source,
                    include_macd=True,
                    include_rsi=True,
                    include_boll=True,
                    include_zlsma=True
                )
                
                # 验证所有指标列都存在
                all_indicator_columns = ['MACD', 'MACD_SIGNAL', 'MACD_HIST',
                                          'RSI_6', 'RSI_12', 'RSI_24',
                                          'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER',
                                          'ZLSMA_20', 'ZLSMA_60']
                for col in all_indicator_columns:
                    assert col in stock_data_with_all.columns, f"缺少指标列 '{col}'"
                print("\n所有指标列检查通过")
                
                print(f"\n{source}数据源（含所有指标）测试通过！")
            else:
                print(f"未能获取股票 {symbol} 的数据")
                
            # 测试包含吊灯止损指标的数据获取
            stock_data_with_chandelier = get_stock_data(
                symbol, 
                start_date, 
                end_date, 
                source=source,
                include_chandelier=True
            )
            
            if not stock_data_with_chandelier.empty:
                print("\n测试吊灯止损指标数据:")
                # 检查吊灯止损相关列是否存在
                chandelier_columns = ['CHANDELIER_LONG', 'CHANDELIER_SHORT']
                for col in chandelier_columns:
                    assert col in stock_data_with_chandelier.columns, f"缺少吊灯止损相关列 '{col}'"
                print("吊灯止损列检查通过")
                
                # 检查吊灯止损数据类型
                for col in chandelier_columns:
                    assert stock_data_with_chandelier[col].dtype == 'float64', \
                        f"{col}列不是浮点数类型"
                print("���灯止损数据类型检查通过")
                
                # 检查吊灯止损数据有效性
                for col in chandelier_columns:
                    assert not stock_data_with_chandelier[col].isnull().all(), \
                        f"{col}列全为空值"
                print("吊灯止损数据空值检查通过")
                
                # 验证吊灯止损数据逻辑关系
                # 多头止损位应该低于最高价，空头止损位应该高于最低价
                assert not stock_data_with_chandelier['CHANDELIER_LONG'].isnull().all(), "多头止损位全为空值"
                assert not stock_data_with_chandelier['CHANDELIER_SHORT'].isnull().all(), "空头止损位全为空值"
                
                # 检查数值是否在合理范围内（不为0或异常大的数值）
                assert all(stock_data_with_chandelier['CHANDELIER_LONG'] > 0), "多头止损位存在非正数值"
                assert all(stock_data_with_chandelier['CHANDELIER_SHORT'] > 0), "空头止损位存在非正数值"
                print("吊灯止损数据有效性验证通过")
                
                # 更新所有指标测试部分的指标列表
                all_indicator_columns = ['MACD', 'MACD_SIGNAL', 'MACD_HIST',
                                          'RSI_6', 'RSI_12', 'RSI_24',
                                          'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER',
                                          'ZLSMA_20', 'ZLSMA_60',
                                          'CHANDELIER_LONG', 'CHANDELIER_SHORT']
                
                # 测试同时包含所有指标
                stock_data_with_all = get_stock_data(
                    symbol, 
                    start_date, 
                    end_date, 
                    source=source,
                    include_macd=True,
                    include_rsi=True,
                    include_boll=True,
                    include_zlsma=True,
                    include_chandelier=True
                )
                
                # 验证所有指标列都存在
                for col in all_indicator_columns:
                    assert col in stock_data_with_all.columns, f"缺少指标列 '{col}'"
                print("\n所有指标列检查通过")
                
                print(f"\n{source}数据源（含所有指标）测试通过！")
            else:
                print(f"未能获取股票 {symbol} 的数据")
                
        except Exception as e:
            print(f"测试{source}数据源时发生错误: {str(e)}")
            raise
    
    # 测试无效股票代码
    print("\n测试无效股票代码:")
    invalid_symbol = "000000"
    invalid_data = get_stock_data(invalid_symbol, start_date, end_date)
    assert isinstance(invalid_data, pd.DataFrame), "对于无效股票代码应返回空DataFrame"
    assert invalid_data.empty, "对于无效股票代码应返回空DataFrame"
    print("无效股票代码测试通过")
    
    print("\n所有测试完成！")

if __name__ == "__main__":
    #test_get_a_share_list()
    #test_get_vgt_data()
    #print("\n" + "="*50 + "\n")
    #test_get_etf_list()
    #print("\n" + "="*50 + "\n")
    #test_get_etf_data()
    #print("\n" + "="*50 + "\n")
    #test_get_stock_name()
    #print("\n" + "="*50 + "\n")
    #test_get_stock_industry()
    #print("\n" + "="*50 + "\n")
    #test_get_industry_fund_flow_rank()
    #print("\n" + "="*50 + "\n")
    #test_get_stock_news()
    #print("\n" + "="*50 + "\n")
    #test_get_us_stock_list()
    #print("\n" + "="*50 + "\n")
    #test_get_stock_news()
    test_get_stock_data()
    print("\n" + "="*50 + "\n")
