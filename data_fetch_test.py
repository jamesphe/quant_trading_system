import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加父目录到系统路径，以便能够导入 data_fetch 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from data_fetch import get_us_stock_data, get_etf_list, get_etf_data, get_stock_data_hourly

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

def test_get_stock_data_hourly():
    """
    测试获取股票或ETF的小时级别历史行情数据
    """
    print("\n开始测试获取小时级别历史行情数据...")
    
    # 测试A股
    symbol_cn = "600519"  # 贵州茅台
    # 测试ETF
    symbol_etf = "159919"  # 沪深300ETF
    # 测试美股
    symbol_us = "AAPL"  # 苹果公司
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    for symbol, market in [(symbol_cn, 'CN'), (symbol_etf, 'CN'), (symbol_us, 'US')]:
        print(f"\n测试 {market} 市场的 {symbol}")
        print(f"开始日期: {start_date}")
        print(f"结束日期: {end_date}")
        
        hourly_data = get_stock_data_hourly(symbol, start_date, end_date, market)
        
        if not hourly_data.empty:
            print(f"成功获取 {symbol} 从 {start_date} 到 {end_date} 的数据。")
            print("数据前5行：")
            print(hourly_data.head())
            print(f"数据行数: {len(hourly_data)}")
            
            # 检查数据列
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Pct_change']
            assert all(col in hourly_data.columns for col in expected_columns), f"{symbol} 数据列不完整"
            
            # 检查数据类型
            assert hourly_data.index.dtype == 'datetime64[ns]', f"{symbol} 索引不是日期时间类型"
            assert hourly_data['Close'].dtype == 'float64', f"{symbol} Close列不是浮点数类型"
            
            # 检查数据范围
            assert hourly_data.index.min().strftime('%Y-%m-%d') >= start_date, f"{symbol} 数据开始日期早于请求的开始日期"
            assert hourly_data.index.max().strftime('%Y-%m-%d') <= end_date, f"{symbol} 数据结束日期晚于请求的结束日期"
            
            print(f"{symbol} 数据验证通过！")
        else:
            print(f"未能获取 {symbol} 的数据。")
    
    print("数据测试完成。")

if __name__ == "__main__":
    #test_get_vgt_data()
    #print("\n" + "="*50 + "\n")
    #test_get_etf_list()
    #print("\n" + "="*50 + "\n")
    #test_get_etf_data()
    #print("\n" + "="*50 + "\n")
    test_get_stock_data_hourly()