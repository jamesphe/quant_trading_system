import pandas as pd
from openai import OpenAI
from data_fetch import get_stock_data
from datetime import datetime, timedelta
import sys
import argparse
import os
import json


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

    根据���析结果请给出明确的交易建议，包括是否应该买入或卖出股票，以及建议的交易价格。
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


def get_stock_web_analysis(symbol):
    """
    使用Kimi的网络搜索功能获取股票的最新市场分析
    
    参数：
    - symbol: str，股票代码（例如：'600519'）
    
    返回：
    - str，基于网络搜索的分析结果
    """
    client = OpenAI(
        api_key="sk-mZyZTW8RmwaDNM1yG6OAh46Av22yRaPknNucnT2606iLWDye",
        base_url="https://api.moonshot.cn/v1",
    )
    
    # 修改提示词，确保web工具被正确激活
    system_prompt = """你是一位专业的股票分析师，请使用网络搜索功能获取并分析最新的市场信息。
    在分析时请标注信息来源，确保信息的可靠性。"""
    
    user_prompt = f"""@web 
    请搜索股票代码 {symbol} 的以下信息：
    1. 最新的公司公告和新闻（最近7天内）
    2. 当前的主要财务指标
    3. 最新的分析师评级和目标价
    4. 所属行业的最新动态
    5. 相关的市场热点

    请基于搜索到的信息：
    1. 总结关键信息要点
    2. 分析可能对股价产生的影响
    3. 给出投资建议
    """
    
    try:
        completion = client.chat.completions.create(
            model="moonshot-v1-32k",  # 使用更大的模型以支持更多上下文
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            tools=[{"type": "web_search"}],  # 显式启用网络搜索工具
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"获取网络分析时发生错误: {str(e)}"


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


def read_industry_fund_flow(date):
    """
    读取指定日期的行业资金流数据
    
    参数:
    - date: datetime对象,表示要读取的日期
    
    返回:
    - DataFrame,包含行业资金流数据,如果文件不存在则返回None
    """
    file_name = f"行业资金流_{date.strftime('%Y%m%d')}.csv"
    print(f"尝试读取文件: {file_name}")
    if os.path.exists(file_name):
        print(f"文件存在,正在读取...")
        return pd.read_csv(file_name)
    else:
        print(f"文件不存在: {file_name}")
        return None


def stream_kimi_analysis(prompt):
    """
    将提示词发送给Kimi接口并流式输出分析结果
    
    参数：
    - prompt: str，发送给Kimi的提示词
    """
    client = OpenAI(
        api_key="sk-mZyZTW8RmwaDNM1yG6OAh46Av22yRaPknNucnT2606iLWDye",
        base_url="https://api.moonshot.cn/v1",
    )
    
    stream = client.chat.completions.create(
        model="moonshot-v1-auto",
        messages=[
            {"role": "system", "content": "你是一位专业的股票分析师,擅长分析大量股票数据并提供投资建议。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=4000,
        stream=True  # 启用流式输出
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='', flush=True)
    print()  # 输出完成后换行


def analyze_csv_stocks(csv_file, date):
    """
    分析CSV文件中的股票数据,找出最适合买入的股票
    
    参数:
    - csv_file: str, CSV文件的路径
    - date: datetime对象,表示分析的日期
    """
    # 读取CSV文件
    df = pd.read_csv(csv_file)
    
    # 读取行业资金流数据
    industry_fund_flow = read_industry_fund_flow(date)
    
    # 准备发送给Kimi的提示词
    prompt = f"""
    请对以下股票数据进行全面分析,筛选出最适合买入的5只股票。

    股票数据:
    {df.to_string()}

    行业资金流数据:
    {industry_fund_flow.to_string() if industry_fund_flow is not None else "无可用的行业资金流数据"}

    筛选标准:
    1. 资金面分析
    - 主力资金净流入情况
    - 近3日和5日资金净流入趋势
    - 行业资金流向稳定性
    
    2. 市场表现
    - 近期涨跌幅(优选涨幅温和的股票)
    - 换手率和成交量变化
    - 技术指标表现
    - 涨停风险评估(需规避连续涨停、炒作题材等高风险股票)
    
    3. 风险控制指标
    - 夏普比率(优选>1.5)
    - 最大回撤(<20%)
    - 历史胜率(>60%)
    
    4. 收益能力
    - 历史总回报率
    - 近期盈利表现
    - 未来增长潜力

    5. 行业分析
    - 行业发展前景
    - 政策支持力度
    - 市场热点关注度

    对每只推荐股票请提供:
    1. 核心推荐理由
    2. 关键指标数据支撑
    3. 行业背景分析
    4. 风险提示(特别关注涨停板风险)
    5. 建议买入价位区间

    最后请给出:
    1. 整体投资策略建议
    2. 仓位控制建议
    3. 风险控制要点(包括涨停板风险防范措施)
    4. 止盈止损参考位
    """
    
    print(prompt)

    print("\nCSV文件中股票的分析结果:")
    stream_kimi_analysis(prompt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="股票分析工具")
    parser.add_argument(
        "-m", "--mode", 
        choices=["single", "csv", "web"], 
        default="csv", 
        help="分析模式: single (单只股票分析) 或 csv (CSV文件分析) 或 web (网络信息分析), 默认为csv"
    )
    parser.add_argument("-s", "--symbol", help="股票代码 (在single和web模式下使用)")
    parser.add_argument(
        "-d", "--date", 
        default=datetime.now().strftime('%Y-%m-%d'), 
        help="分析日期，格式YYYY-MM-DD，默认为今天"
    )
    args = parser.parse_args()

    try:
        date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"错误: 无效的日期格式 '{args.date}'. 请使用 YYYY-MM-DD 格式.")
        sys.exit(1)

    if args.mode in ["single", "web"]:
        if not args.symbol:
            print(f"错误: 在{args.mode}模式下必须提供股票代码。")
            sys.exit(1)
        
        if args.mode == "web":
            print(f"股票 {args.symbol} 的网络信息分析结果：")
            analysis_result = get_stock_web_analysis(args.symbol)
            print(analysis_result)
        else:
            three_months_ago = date - timedelta(days=90)
            start_date = three_months_ago.strftime('%Y-%m-%d')
            end_date = date.strftime('%Y-%m-%d')
            
            stock_data = get_stock_data(args.symbol, start_date, end_date)
            if stock_data.empty:
                print(f"无法获取股票 {args.symbol} 的数据")
                sys.exit(1)
            
            prompt = f"""
            请分析以下股票数据，并根据分析结果给出交易建议：

            {stock_data.to_string()}

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
            
            print(f"股票 {args.symbol} 的AI分析结果：")
            stream_kimi_analysis(prompt)
    
    elif args.mode == "csv":
        csv_file = f"updated_target_stocks_{date.strftime('%Y-%m-%d')}.csv"
        try:
            analyze_csv_stocks(csv_file, date)
        except FileNotFoundError:
            print(f"错误: 找不到文件 '{csv_file}'. 请确保文件存在.")
        except Exception as e:
            print(f"分析CSV文件时发生错误: {str(e)}")
