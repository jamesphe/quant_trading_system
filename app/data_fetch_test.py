import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak
import numpy as np

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
    get_stock_data,
    get_industry_market_data,  # 新增
    get_industry_detail_data,   # 新增
    get_hot_stock_rank,  # 添加新的导入
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
    测试获取股票历史行情数据功能，包括基础数据和技术指标
    """
    print("\n开始测试股票历史行情数据获取功能...")

    # 测试参数
    symbol = "600519"  # 贵州茅台
    end_date = datetime.now().strftime('%Y-%m-%d')  # 使用当前日期作为结束日期
    start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')  # 从120天前开始

    print(f"测试日期范围: {start_date} 到 {end_date}")

    # 1. 测试基础数据获取
    print("\n1. 测试基础数据获取")
    test_basic_data(symbol, start_date, end_date)

    # 2. 测试MACD指标
    print("\n2. 测试MACD指标")
    test_macd_indicator(symbol, start_date, end_date)

    # 3. 测试RSI指标
    print("\n3. 测试RSI指标")
    test_rsi_indicator(symbol, start_date, end_date)

    # 4. 测试布林带指标
    print("\n4. 测试布林带指标")
    test_bollinger_bands(symbol, start_date, end_date)

    # 5. 测试ZLSMA指标
    print("\n5. 测试ZLSMA指标")
    test_zlsma_indicator(symbol, start_date, end_date)

    # 6. 测试吊灯指标
    print("\n6. 测试吊灯指标")
    test_chandelier_indicator(symbol, start_date, end_date)

def test_basic_data(symbol, start_date, end_date):
    """测试基础数据获取"""
    try:
        # 测试两个数据源
        for source in ['baostock', 'akshare']:
            print(f"\n测试{source}数据源:")
            stock_data = get_stock_data(symbol, start_date, end_date, source=source)
            
            if not stock_data.empty:
                print(f"成功获取数据，数据条数: {len(stock_data)}")
                
                # 检查基础数据列
                expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Pct_change']
                assert all(col in stock_data.columns for col in expected_columns), \
                    f"数据列不完整，期望列: {expected_columns}，实际列: {stock_data.columns.tolist()}"
                
                # 检查数据类型
                assert stock_data.index.dtype == 'datetime64[ns]', "索引不是日期时间类型"
                for col in expected_columns:
                    assert stock_data[col].dtype in ['float64', 'int64'], f"{col}列不是数值类型"
                
                # 检查数据有效性
                assert all(stock_data['High'] >= stock_data['Low']), "存在最高价低于最低价的数据"
                assert all(stock_data['Volume'] >= 0), "存在负的成交量"
                assert all(stock_data['Amount'] >= 0), "存在负的成交额"
                
                print("基础数据验证通过")
            else:
                print(f"{source}数据源返回空数据")
    except Exception as e:
        print(f"测试基础数据时发生错误: {str(e)}")

def test_macd_indicator(symbol, start_date, end_date):
    """测试MACD指标计算"""
    try:
        stock_data = get_stock_data(
            symbol, start_date, end_date, 
            source='baostock', 
            include_macd=True
        )
        
        if not stock_data.empty:
            # 检查MACD相关列是否存在
            macd_columns = ['MACD', 'MACD_SIGNAL', 'MACD_HIST']
            assert all(col in stock_data.columns for col in macd_columns), \
                "MACD指标数据列不完整"
            
            # 检查数据类型
            for col in macd_columns:
                assert stock_data[col].dtype == 'float64', f"{col}列不是浮点数类型"
            
            # MACD = MACD_HIST + MACD_SIGNAL 验证
            np.testing.assert_array_almost_equal(
                stock_data['MACD'],
                stock_data['MACD_HIST'] + stock_data['MACD_SIGNAL'],
                decimal=4
            )
            
            print("MACD指标验证通过")
        else:
            print("获取MACD数据失败")
    except Exception as e:
        print(f"测试MACD指标时发生错误: {str(e)}")

def test_rsi_indicator(symbol, start_date, end_date):
    """测试RSI指标计算"""
    try:
        stock_data = get_stock_data(
            symbol, start_date, end_date,
            source='baostock',
            include_rsi=True
        )
        
        if not stock_data.empty:
            # 检查RSI相关列是否存在
            rsi_columns = ['RSI_6', 'RSI_12', 'RSI_24']
            assert all(col in stock_data.columns for col in rsi_columns), \
                "RSI指标数据列不完整"
            
            # 检查数据类型
            for col in rsi_columns:
                assert stock_data[col].dtype == 'float64', f"{col}列不是浮点数类型"
            
            # 检查RSI值范围（应该在0-100之间）
            for col in rsi_columns:
                assert all((stock_data[col] >= 0) & (stock_data[col] <= 100)), \
                    f"{col}值超出有效范围(0-100)"
            
            print("RSI指标验证通过")
        else:
            print("获取RSI数据失败")
    except Exception as e:
        print(f"测试RSI指标时发生错误: {str(e)}")

def test_bollinger_bands(symbol, start_date, end_date):
    """测试布林带指标计算"""
    try:
        stock_data = get_stock_data(
            symbol, start_date, end_date,
            source='baostock',
            include_boll=True
        )
        
        if not stock_data.empty:
            # 检查布林带相关列是否存在
            boll_columns = ['BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']
            assert all(col in stock_data.columns for col in boll_columns), \
                "布林带指标数据列不完整"
            
            # 检查数据类型
            for col in boll_columns:
                assert stock_data[col].dtype == 'float64', f"{col}列不是浮点数类型"
            
            # 验证布林带的基本特性
            assert all(stock_data['BOLL_UPPER'] >= stock_data['BOLL_MIDDLE']), \
                "上轨存在低于中轨的值"
            assert all(stock_data['BOLL_MIDDLE'] >= stock_data['BOLL_LOWER']), \
                "中轨存在低于下轨的值"
            
            print("布林带指标验证通过")
        else:
            print("获取布林带数据失败")
    except Exception as e:
        print(f"测试布林带指标时发生错误: {str(e)}")

def test_zlsma_indicator(symbol, start_date, end_date):
    """测试ZLSMA指标计算"""
    try:
        stock_data = get_stock_data(
            symbol, start_date, end_date,
            source='baostock',
            include_zlsma=True
        )
        
        if not stock_data.empty:
            # 检查ZLSMA相关列是否存在
            zlsma_columns = ['ZLSMA_20', 'ZLSMA_60']
            assert all(col in stock_data.columns for col in zlsma_columns), \
                "ZLSMA指标数据列不完整"
            
            # 检查数据类型
            for col in zlsma_columns:
                assert stock_data[col].dtype == 'float64', f"{col}列不是浮点数类型"
            
            # 验证ZLSMA的基本特性（应该在最高价和最低价之间）
            for col in zlsma_columns:
                assert all(stock_data[col] <= stock_data['High'].rolling(window=60).max()), \
                    f"{col}存在超过历史最高价的值"
                assert all(stock_data[col] >= stock_data['Low'].rolling(window=60).min()), \
                    f"{col}存在低于历史最低价的值"
            
            print("ZLSMA指标验证通过")
        else:
            print("获取ZLSMA数据失败")
    except Exception as e:
        print(f"测试ZLSMA指标时发生错误: {str(e)}")

def test_chandelier_indicator(symbol, start_date, end_date):
    """测试吊灯指标计算"""
    try:
        stock_data = get_stock_data(
            symbol, start_date, end_date,
            source='baostock',
            include_chandelier=True
        )
        
        if not stock_data.empty:
            # 检查吊灯指标相关列是否存在
            chandelier_columns = ['ATR', '周期', '倍数', '多头止损', '空头止损']
            assert all(col in stock_data.columns for col in chandelier_columns), \
                "吊灯指标数据列不完整"
            
            # 检查数据类型
            numeric_columns = ['ATR', '多头止损', '空头止损']
            for col in numeric_columns:
                assert stock_data[col].dtype == 'float64', f"{col}列不是浮点数类型"
            
            # 验证吊灯指标的基本特性
            assert all(stock_data['多头止损'] <= stock_data['空头止损']), \
                "存在多头止损点高于空头止损点的情况"
            assert all(stock_data['ATR'] >= 0), "存在负的ATR值"
            
            print("吊灯指标验证通过")
        else:
            print("获取吊灯指标数据失败")
    except Exception as e:
        print(f"测试吊灯指标时发生错误: {str(e)}")

def test_get_industry_market_data():
    """
    测试获取行业市场数据功能
    """
    print("\n开始测试获取行业市场数据...")
    
    try:
        industry_data = get_industry_market_data()
        
        if not industry_data.empty:
            print(f"成功获取行业市场数据")
            print(f"获取到的行业数量: {len(industry_data)}")
            print("\n数据结构:")
            print(f"列名: {industry_data.columns.tolist()}")
            print("\n数据前5行:")
            print(industry_data.head())
            
            # 检查数据列 - 根据实际返回的列名修改
            expected_columns = [
                'industry_name',    # 板块名称
                'price',           # 最新价
                'change',          # 涨跌额
                'change_pct',      # 涨跌幅
                'market_value',    # 总市值
                'turnover_rate',   # 换手率
                'up_count',        # 上涨家数
                'down_count',      # 下跌家数
                'leading_stock',   # 领涨股票
                'leading_stock_pct' # 领涨股票涨跌幅
            ]
            
            for col in expected_columns:
                assert col in industry_data.columns, f"缺少必要的列 '{col}'"
            print("\n数据列检查通过")
            
            # 检查数据类型
            assert industry_data['industry_name'].dtype == 'object', "industry_name列不是字符串类型"
            numeric_columns = [
                'price', 'change', 'change_pct', 'market_value',
                'turnover_rate', 'up_count', 'down_count', 'leading_stock_pct'
            ]
            for col in numeric_columns:
                assert industry_data[col].dtype in ['float64', 'int64'], \
                    f"{col}列不是数值类型"
            print("数据类型检查通过")
            
            # 检查数值有效性
            assert all(industry_data['price'] >= 0), "存在负的价格"
            assert all(industry_data['market_value'] >= 0), "存在负的市值"
            assert all(industry_data['turnover_rate'] >= 0), "存在负的换手率"
            assert all(industry_data['up_count'] >= 0), "存在负的上涨家数"
            assert all(industry_data['down_count'] >= 0), "存在负的下跌家数"
            print("数值有效性检查通过")
            
            print("\n数据验证全部通过！")
        else:
            print("获取到的行业市场数据为空")
            
    except Exception as e:
        print(f"获取行业市场数据时发生错误: {str(e)}")

def test_get_industry_detail_data():
    """
    测试获取行业详细数据功能
    """
    print("\n开始测试获取行业详细数据...")
    
    try:
        # 测试获取半导体行业的详细数据
        industry_name = "半导体"
        industry_detail = get_industry_detail_data(industry_name)
        
        if not industry_detail.empty:
            print(f"成功获取{industry_name}行业的详细数据")
            print(f"获取到的数据条数: {len(industry_detail)}")
            print("\n数据前5行:")
            print(industry_detail.head())
            
            # 检查数据列
            expected_columns = [
                'date', 'close', 'change_pct', 'volume',
                'amount', 'turnover_rate'
            ]
            for col in expected_columns:
                assert col in industry_detail.columns, f"缺少必要的列 '{col}'"
            print("\n数据列检查通过")
            
            # 检查数据类型
            assert pd.api.types.is_datetime64_any_dtype(industry_detail['date']), \
                "date列不是日期类型"
            numeric_columns = [
                'close', 'change_pct', 'volume',
                'amount', 'turnover_rate'
            ]
            for col in numeric_columns:
                assert industry_detail[col].dtype in ['float64', 'int64'], \
                    f"{col}列不是数值类型"
            print("数据类型检查通过")
            
            # 检查数值有效性
            assert all(industry_detail['close'] > 0), "存在无效的收盘点数"
            assert all(industry_detail['volume'] >= 0), "存在负的成交量"
            assert all(industry_detail['amount'] >= 0), "存在负的成交额"
            assert all(industry_detail['turnover_rate'] >= 0), "存在负的换手率"
            print("数值有效性检查通过")
            
            # 检查日期范围 - 修改这部分代码
            start_date = pd.Timestamp('2024-01-01')
            end_date = pd.Timestamp.now()
            min_date = pd.to_datetime(industry_detail['date'].min())
            max_date = pd.to_datetime(industry_detail['date'].max())
            
            assert min_date >= start_date, "数据开始日期早于2024年1月1日"
            assert max_date <= end_date, "数据结束日期晚于当前日期"
            print("日期范围检查通过")
            
            print("\n数据验证全部通过！")
        else:
            print(f"未能获取{industry_name}行业的详细数据")
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        raise

def test_get_hot_stock_rank():
    """
    测试获取同花顺热榜股票功能
    """
    print("\n开始测试获取同花顺热榜股票数据...")
    
    try:
        # 测试小时榜
        hour_rank = get_hot_stock_rank(data_type='大家都在看', date='hour')
        
        if not hour_rank.empty:
            print(f"成功获取小时热榜数据")
            print(f"获取到的股票数量: {len(hour_rank)}")
            print("\n数据前5行:")
            print(hour_rank.head())
            
            # 检查数据列
            expected_columns = ['market', 'code', 'name', 'hot_value', 'change_pct']
            for col in expected_columns:
                assert col in hour_rank.columns, f"缺少必要的列 '{col}'"
            print("\n数据列检查通过")
            
            # 检查数据类型
            assert hour_rank['market'].dtype == 'object', "market列不是字符串类型"
            assert hour_rank['code'].dtype == 'object', "code列不是字符串类型"
            assert hour_rank['name'].dtype == 'object', "name列不是字符串类型"
            assert hour_rank['hot_value'].dtype in ['float64', 'int64'], "hot_value列不是数值类型"
            assert hour_rank['change_pct'].dtype == 'float64', "change_pct列不是浮点数类型"
            print("数据类型检查通过")
            
            # 检查数值有效性
            assert all(hour_rank['hot_value'] >= 0), "存在负的热度值"
            assert all(abs(hour_rank['change_pct']) <= 1), "涨跌幅超出正常范围"
            print("数值有效性检查通过")
            
            # 检查市场代码
            valid_markets = ['沪市', '深市']
            assert all(hour_rank['market'].isin(valid_markets)), "存在无效的市场代码"
            print("市场代码检查通过")
            
            # 检查股票代码格式
            assert all(len(code) == 6 for code in hour_rank['code']), "存在非6位股票代码"
            assert all(code.isdigit() for code in hour_rank['code']), "存在非数字股票代码"
            print("股票代码格式检查通过")
            
            print("\n小时榜数据验证通过！")
            
        # 测试日榜
        day_rank = get_hot_stock_rank(data_type='快速飙升中', date='day')
        print("\n获取到的日榜数据:")
        print(f"数据形状: {day_rank.shape}")
        print("\n数据示例:")
        print(day_rank)
        print("\n数据类型信息:")
        print(day_rank.dtypes)
        if not day_rank.empty:
            print(f"\n成功获取日榜数据")
            print(f"获取到的股票数量: {len(day_rank)}")
            print("\n数据前5行:")
            print(day_rank.head())
            
            # 进行与小时榜相同的验证
            for col in expected_columns:
                assert col in day_rank.columns, f"缺少必要的列 '{col}'"
            
            assert all(day_rank['hot_value'] >= 0), "存在负的热度值"
            assert all(abs(day_rank['change_pct']) <= 1), "涨跌幅超出正常范围"
            assert all(day_rank['market'].isin(valid_markets)), "存在无效的市场代码"
            assert all(len(code) == 6 for code in day_rank['code']), "存在非6位股票代码"
            assert all(code.isdigit() for code in day_rank['code']), "存在非数字股票代码"
            
            print("\n日榜数据验证通过！")
            
        # 测试无效参数
        invalid_rank = get_hot_stock_rank(data_type='无效类型', date='invalid')
        assert isinstance(invalid_rank, pd.DataFrame), "对于无效参数应返回空DataFrame"
        assert invalid_rank.empty, "对于无效参数应返回空DataFrame"
        print("\n无效参数测试通过")
        
        print("\n所有测试通过！")
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        raise

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
    #test_get_industry_market_data()  # 新增
    #print("\n" + "="*50 + "\n")
    #test_get_industry_detail_data()  # 新增
    #print("\n" + "="*50 + "\n")
    test_get_stock_data()
    print("\n" + "="*50 + "\n")
    #test_get_hot_stock_rank()  # 添加新的测试
    #print("\n" + "="*50 + "\n")
