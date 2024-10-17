import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加父目录到系统路径，以便能够导入 data_fetch 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from data_fetch import get_us_stock_data
from data_fetch import get_etf_list
from data_fetch import get_etf_data
from data_fetch import get_stock_name

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

if __name__ == "__main__":
    #test_get_vgt_data()
    #print("\n" + "="*50 + "\n")
    #test_get_etf_list()
    #print("\n" + "="*50 + "\n")
    #test_get_etf_data()
    #print("\n" + "="*50 + "\n")
    test_get_stock_name()
