import pandas as pd
from openai import OpenAI, AsyncOpenAI
from data_fetch import get_stock_data
from datetime import datetime, timedelta
import sys
import argparse
import os
from zhipuai import ZhipuAI
from abc import ABC, abstractmethod
from config import Config
from typing import Union, Generator
import json
import time

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
        self.config = config.config.get('openai', {})
        self.client = OpenAI(
            api_key=api_key, 
            base_url=self.config.get('base_url', "https://api.chatanywhere.tech/v1")
        )
        self.async_client = AsyncOpenAI(
            api_key=api_key, 
            base_url=self.config.get('base_url', "https://api.chatanywhere.tech/v1")
        )
    
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
            model=self.config.get('model', "gpt-4o"),
            messages=messages,
            stream=stream,
            temperature=self.config.get('temperature', 0.5),
            max_tokens=self.config.get('max_tokens', 4096)
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
    stock_data = get_stock_data(
        symbol, start_date, end_date, 
        include_macd=True, include_rsi=True, include_boll=True, 
        include_zlsma=True, include_chandelier=True
    )
    
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
    file_name = os.path.join('stock_data', f"行业资金流_{date.strftime('%Y%m%d')}.csv")
    print(f"尝试读取文件: {file_name}")
    if os.path.exists(file_name):
        print("文件存在,正在读取...")
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
    date_str = (date.strftime('%Y%m%d') if date 
                else datetime.now().strftime('%Y%m%d'))
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
    请对提供的全部股票进行全面的对比分析，从中筛选出最适合基于CE策略短线交易的5只股票。
    分析过程需要对每只股票的各项指标进行横向比较，综合评估后给出最终推荐名单。

    行业资金流数据:
    {industry_fund_flow.to_string() if industry_fund_flow is not None 
      else "无可用的行业资金流数据"}

    股票数据:
    {df.to_string()}

    分析步骤:
    1. CE策略信号分析（第一轮筛选）
    - CE策略信号强度评估
      * 信号强度(signal_strength值较高的股票，优先考虑>0.5的股票)
      * 最新信号(为1.0的股票表示有买入信号)
      * 信号强度分级(A+/A/B+/B/C)
    - CE策略参数分析
      * 周期(period)与倍数组合分析(短周期适合短线交易)
      * 参数敏感性分析(参数微调对信号的影响)

    2. 技术面确认（第二轮筛选）
    - 技术指标表现
      * 夏普比率(优选>1.5的高夏普比率股票)
      * 胜率(优选胜率>0.7的股票)
      * 最大回撤(优先选择<15%的股票)
      * 最佳回报(优选>0.5的股票)
    - 技术指标信号
      * EMA交叉信号(为1表示金叉)
      * KDJ信号(为1表示金叉)
      * MACD信号(为1表示金叉)
      * 布林带宽度(较窄表示波动较小)
    - 价格波动性分析
      * 最新涨跌幅(优先选择涨幅在3-10%之间的股票，避免涨幅过大或过小的股票)
      * 5日变化率(优选>0的股票)
      * 日内波动率(优选<10%的股票)
      * 14日ATR(用于设置止损位)

    3. 资金流向分析（第三轮筛选）
    - 主力资金流向分析
      * 主力净流入(优选>0的股票)
      * 主力净流入率(优选>5%的股票)
      * 最近3日净流入(优选>0的股票)
      * 最近5日净流入(优选>0的股票)
    - 交易活跃度
      * 最新交易量(相对于行业平均水平)
      * 换手率(优选>5%的活跃股票)
      * 资金流变化率(优选>0的股票)

    4. 行业分析(第四轮筛选)
    - 所属行业分析
      * 行业景气度
      * 行业轮动情况
      * 行业内个股表现对比

    5. 风险控制指标
    - 止损位设置建议(基于ATR倍数，参考period和倍数列)
    - 流动性风险评估(基于换手率和交易量)
    - 短期技术面风险评估
    - 最大加仓次数限制(参考最大加仓列)
    - 投资比例参考(参考投资比例列)
    - strength_threshold值分析(作为信号强度阈值参考)

    6. 综合评估与排序
    - CE策略信号优先级评分
    - 技术面确认加分
    - 资金流向加分
    - 行业热度加分
    - 风险因素扣分(考虑最大回撤和资金流向)
    - 最终排序与推荐

    对每只推荐股票请提供:
    1. CE策略信号分析
       - 信号强度和分级
       - 参数分析和优化建议
    2. 技术面确认情况
       - 夏普比率、胜率和最大回撤
       - 技术指标信号(EMA、KDJ、MACD)
       - 价格波动性分析
    3. 资金流向分析
       - 主力资金净流入情况及占比
       - 近期资金流向趋势(3日和5日)
       - 换手率和交易量分析
    4. 所属行业分析
    5. 风险提示
    6. 建议买入价位区间和止损位(基于ATR倍数计算)

    最后请给出:
    1. 次日交易计划
       - 具体买入价位区间
       - 分批建仓策略
       - 持仓时间预期
    2. 精确的止盈止损建议(基于ATR倍数)
    3. 交易时机选择建议(开盘、盘中、收盘前的具体策略)
    4. 仓位配置建议(参考投资比例列)
    5. 加仓策略(参考最大加仓列)
    6. 风险控制措施
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
    client = ZhipuAI(
        api_key="8d71dbdc04f0f2fb125badc9f6ab51be.vBBjM6pPSaoVIHoM"
    )
    
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
    client = ZhipuAI(
        api_key="8d71dbdc04f0f2fb125badc9f6ab51be.vBBjM6pPSaoVIHoM"
    )
    
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


def stream_zhipu_followup(symbol, question, conversation_history):
    """处理智谱AI的后续对话"""
    try:
        retries = 3
        retry_delay = 1
        client = ZhipuAI(api_key="your_api_key")
        
        # 构建系统提示词
        system_prompt = """你是一位专业的股票分析师，正在就特定股票进行持续对话。
        请基于之前的对话历史和新的问题，提供专业、准确的分析和建议。
        回答时请保持前后一致性，并参考之前讨论过的信息。"""
        
        # 构建消息历史
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({
            "role": "system", 
            "content": f"当前正在分析的股票代码是: {symbol}"
        })
        messages.append({"role": "user", "content": question})
        
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model="glm-4-plus",
                    messages=messages,
                    temperature=0.7,
                    stream=True
                )
                
                for chunk in response:
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        if content:
                            yield f"data: {json.dumps({'content': content})}\n\n"
                
                break
            except Exception as e:
                if attempt < retries - 1:
                    print(f"[API] 第{attempt + 1}次尝试失败: {str(e)}")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise
                    
    except Exception as e:
        error_message = f"分析过程发生错误: {str(e)}"
        print(f"[API ERROR] {error_message}")
        yield f"data: {json.dumps({'error': error_message}, ensure_ascii=False)}\n\n"

def stream_kimi_followup(symbol, question, conversation_history):
    """处理Kimi的后续对话"""
    try:
        client = OpenAI(
            api_key="sk-5WISVUa4tF2lypG13gvpqmzZ3j3ASGlpK4yyxLur4itEpyeb",
            base_url="https://api.moonshot.cn/v1",
        )
        
        # 构建系统提示词
        system_prompt = """你是一位专业的股票分析师，正在就特定股票进行持续对话。
        请基于之前的对话历史和新的问题，提供专业、准确的分析和建议。
        回答时请保持前后一致性，并参考之前讨论过的信息。
        请直接给出分析内容，不要输出无关的格式化字符。
        """
        
        # 构建消息历史
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({
            "role": "system", 
            "content": f"当前正在分析的股票代码是: {symbol}"
        })
        messages.append({"role": "user", "content": question})
        
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages,
            temperature=0.7,
            stream=True
        )
        
        buffer = ""
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content:
                    buffer += content
                    if content.endswith(('。', '！', '？', '\n')):
                        yield f"data: {json.dumps({'content': buffer}, ensure_ascii=False)}\n\n"
                        buffer = ""
        
        if buffer:
            yield f"data: {json.dumps({'content': buffer}, ensure_ascii=False)}\n\n"
                    
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

def stream_openai_followup(symbol, question, conversation_history):
    """处理OpenAI的后续对话"""
    try:
        retries = 3  # 添加重试机制
        retry_delay = 1  # 重试延迟秒数
        
        model = OpenAIModel()
        
        # 构建系统提示词
        system_prompt = """你是一位专业的股票分析师，正在就特定股票进行持续对话。
        请基于之前的对话历史和新的问题，提供专业、准确的分析和建议。
        回答时请保持前后一致性，并参考之前讨论过的信息。
        请直接给出分析内容，不要输出无关的格式化字符。
        """
        
        # 构建消息历史
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({
            "role": "system", 
            "content": f"当前正在分析的股票代码是: {symbol}"
        })
        messages.append({"role": "user", "content": question})
        
        for attempt in range(retries):
            try:
                response = model.client.chat.completions.create(
                    model=model.config.get('model', "gpt-4"),
                    messages=messages,
                    temperature=0.7,
                    stream=True
                )
                
                for chunk in response:
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                        
                break  # 如果成功完成，跳出重试循环
                
            except Exception as e:
                if attempt < retries - 1:  # 如果还有重试机会
                    print(f"[API] 第{attempt + 1}次尝试失败: {str(e)}")
                    time.sleep(retry_delay)  # 等待一段时间后重试
                    continue
                else:  # 如果已经用完所有重试机会
                    raise  # 重新抛出异常
                    
    except Exception as e:
        error_message = f"分析过程发生错误: {str(e)}"
        print(f"[API ERROR] {error_message}")
        yield error_message


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
