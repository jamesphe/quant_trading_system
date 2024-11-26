import pandas as pd
from openai import OpenAI, AsyncOpenAI
from data_fetch import get_stock_data
from datetime import datetime, timedelta
import sys
import argparse
import os
import zhipuai
from zhipuai import ZhipuAI
from abc import ABC, abstractmethod
from config import Config
from typing import Union, Generator

class AIModelBase(ABC):
    """AI模型基类"""
    
    @abstractmethod
    def analyze(
        self,
        prompt: str,
        stream: bool = False
    ) -> Union[str, Generator]:
        """分析方法"""
        pass


class OpenAIModel(AIModelBase):
    """OpenAI 模型实现"""
    
    def __init__(self):
        config = Config()
        api_key = config.get_api_key('openai')
        self.client = OpenAI(api_key=api_key, base_url="https://api.chatanywhere.tech/v1")
        self.async_client = AsyncOpenAI(api_key=api_key, base_url="https://api.chatanywhere.tech/v1")
    
    def analyze(
        self,
        prompt: str,
        stream: bool = False
    ) -> Union[str, Generator]:
        """分析方法"""
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的股票分析师，请基于提供的数据进行专业的分析。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=stream,
            temperature=0.7
        )
        
        if stream:
            return self._handle_stream_response(response)
        return response.choices[0].message.content
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def get_kimi_analysis(stock_data):
    """
    将股票数据发送给Kimi接口进行分析
    
    参数：
    - stock_data: DataFrame，包含股票历史数据
    
    返回：
    - str，Kimi的分析结果
    """
    client = OpenAI(
        api_key="sk-5WISVUa4tF2lypG13gvpqmzZ3j3ASGlpK4yyxLur4itEpyeb",
        base_url="https://api.moonshot.cn/v1",
    )
    
    prompt = get_stock_analysis_prompt(stock_data)
    
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
        api_key="sk-5WISVUa4tF2lypG13gvpqmzZ3j3ASGlpK4yyxLur4itEpyeb",
        base_url="https://api.moonshot.cn/v1",
    )
    
    # 修改提示词，确保web工具被正确激活
    system_prompt = """你是一位专业的股票分析师，请使用网络搜索功能获取并分析最新的市场信息。
    在分析时请标注信息来源，确保信息的可靠性。"""
    
    user_prompt = f"""@web 
    请搜索股票代码 {symbol} 的以下信息：
    1. 最新的公司公告新闻（最近7天内）
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

def save_analysis_to_markdown(analysis_result, symbol=None, date=None):
    """
    将分析结果保存到markdown文件
    
    参数：
    - analysis_result: str，分析结果
    - symbol: str，可选，股票代码
    - date: datetime，可选，分析日期
    """
    date_str = date.strftime('%Y%m%d') if date else datetime.now().strftime('%Y%m%d')
    file_name = (f"stock_analysis_{symbol}_{date_str}.md" if symbol 
                 else f"stocks_analysis_{args.ai}_{date_str}.md")
    
    # 确保AIResult目录存在
    os.makedirs('AIResult', exist_ok=True)
    
    # 保存到AIResult目录
    save_path = os.path.join('AIResult', file_name)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(f"# 股票分析报告 {date_str}\n\n")
        if symbol:
            f.write(f"## 股票代码：{symbol}\n\n")
        f.write(analysis_result)
    
    print(f"\n分析结果已保存到文件：{file_name}")


def stream_kimi_analysis(prompt):
    """
    将提示词发送给Kimi接口并流式输出分析结果
    
    参数：
    - prompt: str，发送给Kimi的提示词
    """
    client = OpenAI(
        api_key="sk-5WISVUa4tF2lypG13gvpqmzZ3j3ASGlpK4yyxLur4itEpyeb",
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
        stream=True
    )
    
    # 收集完整的分析结果
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            print(content, end='', flush=True)
    print()
    
    return full_response


def get_stock_analysis_prompt(stock_data):
    """
    生成单只股票分析的prompt
    
    参数：
    - stock_data: DataFrame，包含股票历史数据
    
    返回：
    - str，分析提示词
    """
    return f"""
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

    根据分析结果请给出明确的交易建议，包括是否应该买入或卖出股票，以及建议的交易价格。
    """


def get_csv_analysis_prompt(df, industry_fund_flow):
    """
    生成CSV文件分析的prompt
    
    参数：
    - df: DataFrame，股票列表数据
    - industry_fund_flow: DataFrame，行业资金流数据
    
    返回：
    - str，分析提示词
    """
    return f"""
    请对提供的全部股票进行全面的对比分析，从中筛选出最适合建仓的5只股票。分析过程需要对每只股票的各项指标进行横向比较，综合评估后给出最终推荐名单。

    行业资金流数据:
    {industry_fund_flow.to_string() if industry_fund_flow is not None 
      else "无可用的行业资金流数据"}

    股票数据:
    {df.to_string()}

    分析步骤:
    1. 个股筛选标准(主要考虑因素)
    - 主力资金流向分析
      * 主力净流入金额及占比
      * 近3日和5日资金净流入趋势
      * 主力资金持续性评估
    - 技术指标表现
      * 夏普比率(优选>0.15)
      * 历史胜率(>60%)
      * 最大回撤(<15%)
      * 历史最佳回报率
    - 交易活跃度
      * 最新交易量
      * 换手率变化
      * 最新涨跌幅(优先选择涨幅在5%以内的股票,避免涨停和涨幅过大的股票)

    2. 行业资金流分析(辅助参考)
    - 所属行业资金流入规模
    - 行业资金流入持续性
    - 行业基本面和发展前景
    
    3. 风险控制指标
    - 涨跌幅风险评估
    - 流动性风险评估
    - 行业系统性风险评估
    
    4. 综合评估
    - 个股投资价值评分
    - 行业景气度加分
    - 风险因素扣分

    对每只推荐股票请提供:
    1. 核心推荐理由(重点说明个股自身优势)
    2. 关键指标数据:
       - 主力资金净流入情况
       - 近期资金流向趋势
       - 夏普比率
       - 历史胜率
       - 最大回撤
       - 最新价格
       - 最新涨跌幅（百分比）
    3. 所属行业资金流情况及影响
    4. 风险提示
    5. 建议买入价位区间

    最后请给出:
    1. 投资组合配置建议
    2. 止盈止损建议
    """


def analyze_csv_stocks(csv_file, date, ai_provider="kimi"):
    """
    分析CSV文件中的股票数据
    
    参数:
    - csv_file: str, CSV文件的路径
    - date: datetime对象,表示分析的日期
    - ai_provider: str, 使用的AI提供商 ("kimi", "zhipu" 或 "openai")
    
    返回:
    - str, 分析结果
    """
    # 读取CSV文件
    df = pd.read_csv(csv_file, dtype={'股票代码': str})
    
    # 读取行业资金流数据
    industry_fund_flow = read_industry_fund_flow(date)
    
    # 获取分析提示词
    prompt = get_csv_analysis_prompt(df, industry_fund_flow)
    
    # 根据AI提供商选择不同的分析方法
    if ai_provider == "kimi":
        return stream_kimi_analysis(prompt)
    elif ai_provider == "zhipu":
        return stream_zhipu_analysis(prompt)
    else:  # openai
        return stream_openai_analysis(prompt)


def get_zhipu_analysis(stock_data):
    """
    使用智谱AI接口进行股票分析
    
    参数：
    - stock_data: DataFrame，包含股票历史数据
    
    返回：
    - str，智谱AI的分析结果
    """
    client = ZhipuAI(api_key="8d71dbdc04f0f2fb125badc9f6ab51be.vBBjM6pPSaoVIHoM")
    
    prompt = get_stock_analysis_prompt(stock_data)
    
    try:
        response = client.chat.completions.create(
            model="glm-4-plus",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的股票分析师，擅长分析股票数据并提供交易建议。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            top_p=0.95,
            max_tokens=4000,
            tools=[{"type": "web_search"}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"智谱AI分析时发生错误: {str(e)}"


def stream_zhipu_analysis(prompt):
    """
    使用智谱AI接口进行流式分析输出
    
    参数：
    - prompt: str，发送给智谱AI的提示词
    """
    client = ZhipuAI(api_key="8d71dbdc04f0f2fb125badc9f6ab51be.vBBjM6pPSaoVIHoM")
    
    try:
        response = client.chat.completions.create(
            model="glm-4-plus",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的股票分析师，擅长分析大量股票数据并提供投资建议。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            top_p=0.95,
            max_tokens=4000,
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    print(content, end='', flush=True)
        print()
        
        return full_response
    except Exception as e:
        error_msg = f"智谱AI流式分析时发生错误: {str(e)}"
        print(error_msg)
        return error_msg


def get_openai_analysis(stock_data):
    """
    使用OpenAI接口进行股票分析
    
    参数：
    - stock_data: DataFrame，包含股票历史数据
    
    返回：
    - str，OpenAI的分析结果
    """
    model = OpenAIModel()
    prompt = get_stock_analysis_prompt(stock_data)
    
    try:
        return model.analyze(prompt)
    except Exception as e:
        return f"OpenAI分析时发生错误: {str(e)}"


def stream_openai_analysis(prompt):
    """
    使用OpenAI接口进行流式分析输出
    
    参数：
    - prompt: str，发送给OpenAI的提示词
    """
    model = OpenAIModel()
    
    try:
        full_response = ""
        for chunk in model.analyze(prompt, stream=True):
            if chunk:
                full_response += chunk
                print(chunk, end='', flush=True)
        print()
        
        return full_response
    except Exception as e:
        error_msg = f"OpenAI流式分析时发生错误: {str(e)}"
        print(error_msg)
        return error_msg


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
    parser.add_argument(
        "--ai", 
        choices=["kimi", "zhipu", "openai"], 
        default="kimi",
        help="选择使用的AI接口: kimi、zhipu 或 openai, 默认为kimi"
    )
    args = parser.parse_args()

    try:
        date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"错误: 无效的日期格式 '{args.date}'. 请使用 YYYY-MM-DD 格式.")
        sys.exit(1)

    if args.mode in ["single", "web"]:
        if args.mode == "web":
            print(f"股票 {args.symbol} 的网络信息分析结果：")
            analysis_result = get_stock_web_analysis(args.symbol)
            print(analysis_result)
            save_analysis_to_markdown(analysis_result, args.symbol, date)
        else:
            three_months_ago = date - timedelta(days=90)
            start_date = three_months_ago.strftime('%Y-%m-%d')
            end_date = date.strftime('%Y-%m-%d')
            
            stock_data = get_stock_data(args.symbol, start_date, end_date)
            if stock_data.empty:
                print(f"无法获取股票 {args.symbol} 的数据")
                sys.exit(1)
            
            prompt = get_stock_analysis_prompt(stock_data)
            
            print(f"股票 {args.symbol} 的AI分析结果：")
            if args.ai == "kimi":
                analysis_result = stream_kimi_analysis(prompt)
            elif args.ai == "zhipu":
                analysis_result = stream_zhipu_analysis(prompt)
            else:  # openai
                analysis_result = stream_openai_analysis(prompt)
            save_analysis_to_markdown(analysis_result, args.symbol, date)
    
    elif args.mode == "csv":
        csv_file = os.path.join('stock_data', f"updated_target_stocks_{date.strftime('%Y-%m-%d')}.csv")
        try:
            analysis_result = analyze_csv_stocks(csv_file, date, args.ai)
            if analysis_result:
                save_analysis_to_markdown(analysis_result, date=date)
            else:
                print("错误: 未能获取分析结果")
        except FileNotFoundError:
            print(f"错误: 找不到文件 '{csv_file}'. 请确保文件存在.")
        except Exception as e:
            print(f"分析CSV文件时发生错误: {str(e)}")
