import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    filename='sector_rotation.log',
    filemode='w',  # 覆盖模式
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger()

def get_em_industry_names():
    """
    获取东方财富行业板块名称和代码
    """
    try:
        df = ak.stock_board_industry_name_em()
        logger.info("成功获取东方财富行业板块名称和代码")
        return df[['板块名称', '板块代码']]
    except Exception as e:
        logger.error(f"获取东方财富行业板块名称和代码失败: {e}")
        return pd.DataFrame()

def get_em_industry_hist(symbol, start_date, end_date, period="日k", adjust=""):
    """
    获取东方财富行业板块历史行情数据
    :param symbol: 行业板块名称，如 "小金属"
    :param start_date: 开始日期，如 "20211201"
    :param end_date: 结束日期，如 "20220401"
    :param period: 周期，默认 "日k"
    :param adjust: 复权类型，默认不复权
    :return: DataFrame 格式的历史行情数据
    """
    try:
        df = ak.stock_board_industry_hist_em(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            period=period,
            adjust=adjust
        )
        if not df.empty:
            df['日期'] = pd.to_datetime(df['日期'])
            df.set_index('日期', inplace=True)
            logger.info(f"成功获取行业板块 {symbol} 的历史行情数据")
            return df
        else:
            logger.warning(f"行业板块 {symbol} 的历史行情数据为空")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"获取行业板块 {symbol} 的历史行情数据失败: {e}")
        return pd.DataFrame()

def fetch_all_industry_hist(industry_names, start_date, end_date):
    """
    获取所有行业板块的历史行情数据
    :param industry_names: 行业板块名称列表
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 字典，键为行业名称，值为对应的历史行情DataFrame
    """
    industry_data = {}
    for name in industry_names:
        df = get_em_industry_hist(name, start_date, end_date)
        if not df.empty:
            industry_data[name] = df
    return industry_data

def calculate_cumulative_return(industry_data):
    """
    计算各行业板块的累计收益率
    :param industry_data: 字典，键为行业名称，值为历史行情DataFrame
    :return: DataFrame，各行业板块的累计收益率
    """
    cumulative_returns = pd.DataFrame()
    for name, df in industry_data.items():
        df_sorted = df.sort_index()
        # 检查列名并使用正确的列名
        if '收盘' in df_sorted.columns:
            price_column = '收盘'
        elif '收盘价' in df_sorted.columns:
            price_column = '收盘价'
        else:
            logger.warning(f"行业 {name} 的数据中没有找到收盘价列，跳过该行业")
            continue
        
        df_sorted['累计收益率'] = (df_sorted[price_column] / df_sorted[price_column].iloc[0]) - 1
        cumulative_returns[name] = df_sorted['累计收益率']
    return cumulative_returns

def select_top_n_industries(cumulative_returns, lookback_days=63, top_n=3):
    """
    选择表现最好的前N个行业板块
    :param cumulative_returns: DataFrame，各行业板块的累计收益率
    :param lookback_days: 回溯天数，默认63天（约3个月）
    :param top_n: 选择前N个行业
    :return: 列表，表现最好的行业名称
    """
    latest_date = cumulative_returns.index[-1]
    start_date = latest_date - pd.Timedelta(days=lookback_days)
    lookback_data = cumulative_returns.loc[start_date:latest_date]
    # 计算过去lookback_days的累计收益率
    performance = (lookback_data.iloc[-1] / lookback_data.iloc[0]) - 1
    top_industries = performance.nlargest(top_n).index.tolist()
    logger.info(f"在过去{lookback_days}天内表现最好的前{top_n}个行业板块: {top_industries}")
    return top_industries

def plot_cumulative_returns(cumulative_returns, selected_industries=None):
    """
    绘制各行业板块的累计收益率
    :param cumulative_returns: DataFrame，各行业板块的累计收益率
    :param selected_industries: 列表，选择特定的行业板块进行高亮显示
    """
    plt.figure(figsize=(14, 7))
    for column in cumulative_returns.columns:
        if selected_industries and column in selected_industries:
            plt.plot(cumulative_returns.index, cumulative_returns[column], label=column, linewidth=2)
        else:
            plt.plot(cumulative_returns.index, cumulative_returns[column], label=column, alpha=0.3)
    plt.title('各行业板块累计收益率')
    plt.xlabel('日期')
    plt.ylabel('累计收益率')
    plt.legend(loc='upper left', fontsize='small', ncol=2)
    plt.grid(True)
    plt.show()

def main():
    # 获取东方财富行业板块名称和代码
    industry_df = get_em_industry_names()
    if industry_df.empty:
        logger.error("未获取到东方财富行业板块名称和代码，程序终止。")
        return
    
    industry_names = industry_df['板块名称'].tolist()
    
    # 设置日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')  # 过去一年的数据
    
    # 获取所有行业板块的历史行情数据
    industry_data = fetch_all_industry_hist(industry_names, start_date, end_date)
    if not industry_data:
        logger.error("未获取到任何行业板块的历史行情数据，程序终止。")
        return
    
    # 计算各行业板块的累计收益率
    cumulative_returns = calculate_cumulative_return(industry_data)
    
    # 选择表现最好的前3个行业板块
    top_industries = select_top_n_industries(cumulative_returns, lookback_days=63, top_n=3)
    
    # 可视化累计收益率
    #plot_cumulative_returns(cumulative_returns, selected_industries=top_industries)
    
    # 输出选择的行业板块
    print(f"表现最好的前3个行业板块: {top_industries}")

if __name__ == "__main__":
    main()
