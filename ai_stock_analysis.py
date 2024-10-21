import pandas as pd
from openai import OpenAI
from data_fetch import get_stock_data
from datetime import datetime, timedelta
import sys
import argparse


def get_kimi_analysis(stock_data):
    """
    将股票数据发送给Kimi接口进行分析
    
    参数：
    - stock_data: DataFrame，包含股票历史数据
    
    返回：
    - str，Kimi的分析结果
    """
    client = OpenAI(
        api_key="sk-mZyZTW8RmwaDNM1yG6OAh46Av22yRaPknNucnT2606iLWDye",
        base_url="https://api.moonshot.cn/v1",
    )
    
    # 准备发送给Kimi的提示词
    prompt = f"""
    请分析以下股票数据，并根据分析结果给出交易建议：

    {stock_data if isinstance(stock_data, str) else stock_data.to_string()}

    请考虑以下方面进行分析：
    1. 股票价格趋势
    2. 成交量变化
    3. 主要的技术指标（如移动平均线、RSI等）
    4. 可能的支撑位和阻力位
    5. 基于历史数据的短期和中期预测
    6. 任何值得注意的异常模式或事件
    7. 从网上获取的这支股票的最新消息

    根据分析结果，请给出明确的交易建议，包括是否应该买入或卖出股票，以及建议的交易价格。
    """
    
    completion = client.chat.completions.create(
        model="moonshot-v1-8k",
        messages=[
            {"role": "system", "content": "你是一位专业的股票分析师，擅长分析股票数据并提供交易建议。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )
    
    return completion.choices[0].message.content


def analyze_stock(symbol, start_date, end_date):
    """
    获取股票数据并进行AI分析
    
    参数：
    - symbol: str，股票代码
    - start_date: str，开始日期，格式'YYYY-MM-DD'
    - end_date: str，结束日期，格式'YYYY-MM-DD'
    
    返回：
    - str，分析结果
    """
    # 获取股票数据
    stock_data = get_stock_data(symbol, start_date, end_date)
    
    if stock_data.empty:
        return f"无法获取股票 {symbol} 的数据"
    
    # 发送数据给Kimi进行分析
    analysis_result = get_kimi_analysis(stock_data)
    
    return analysis_result


def analyze_csv_stocks(csv_file):
    """
    分析CSV文件中的股票数据,找出最适合买入的股票
    
    参数:
    - csv_file: str, CSV文件的路径
    
    返回:
    - str, 分析结果和推荐买入的股票
    """
    # 读取CSV文件
    df = pd.read_csv(csv_file)
    
    # 准备发送给Kimi的提示词
    prompt = f"""
    请分析以下股票数据,并找出最适合买入的前5只股票:

    {df.to_string()}

    请考虑以下因素进行分析:
    1. 夏普比率
    2. 最佳胜率
    3. 最佳最大回撤
    4. 最佳回报
    5. 最新信号
    6. 最新涨跌幅
    7. 主力净流入和净流入率
    8. 最近3日和5日净流入

    对于每只推荐的股票,请简要解释选择的原因。最后,给出一个总体的投资建议。
    """
    
    client = OpenAI(
        api_key="sk-mZyZTW8RmwaDNM1yG6OAh46Av22yRaPknNucnT2606iLWDye",
        base_url="https://api.moonshot.cn/v1",
    )
    
    completion = client.chat.completions.create(
        model="moonshot-v1-auto",
        messages=[
            {"role": "system", "content": "你是一位专业的股票分析师,擅长分析大量股票数据并提供投资建议。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )
    
    return completion.choices[0].message.content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="股票分析工具")
    parser.add_argument("-m", "--mode", choices=["single", "csv"], default="csv", help="分析模式: single (单只股票) 或 csv (CSV文件), 默认为csv")
    parser.add_argument("-s", "--symbol", help="股票代码 (仅在single模式下使用)")
    parser.add_argument("-d", "--date", default=datetime.now().strftime('%Y-%m-%d'), help="分析日期，格式YYYY-MM-DD，默认为今天")
    args = parser.parse_args()

    try:
        date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"错误: 无效的日期格式 '{args.date}'. 请使用 YYYY-MM-DD 格式.")
        sys.exit(1)

    if args.mode == "single":
        if not args.symbol:
            print("错误: 在single模式下必须提供股票代码。")
            sys.exit(1)
        
        three_months_ago = date - timedelta(days=90)
        start_date = three_months_ago.strftime('%Y-%m-%d')
        end_date = date.strftime('%Y-%m-%d')
        
        result = analyze_stock(args.symbol, start_date, end_date)
        print(f"股票 {args.symbol} 的AI分析结果：\n{result}")
    
    elif args.mode == "csv":
        csv_file = f"updated_target_stocks_{date.strftime('%Y-%m-%d')}.csv"
        try:
            csv_analysis_result = analyze_csv_stocks(csv_file)
            print(f"\nCSV文件中股票的分析结果:\n{csv_analysis_result}")
        except FileNotFoundError:
            print(f"错误: 找不到文件 '{csv_file}'. 请确保文件存在.")
        except Exception as e:
            print(f"分析CSV文件时发生错误: {str(e)}")
