import argparse
from datetime import datetime, timedelta
import pandas as pd
from zhipuai import ZhipuAI
import sys
from data_fetch import get_stock_data, get_stock_name, get_stock_basic_info, get_stock_news, get_etf_data, get_us_stock_data
import logging
from typing import Union, Generator
import requests
from abc import ABC, abstractmethod
from config import Config
import json
from openai import AsyncOpenAI, OpenAI
import os


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


class ZhipuAIModel(AIModelBase):
    """智谱AI模型实现"""
    
    def __init__(self):
        config = Config()
        api_key = config.get_api_key('zhipu')
        self.client = ZhipuAI(api_key=api_key)
    
    def analyze(
        self,
        prompt: str,
        stream: bool = False
    ) -> Union[str, Generator]:
        response = self.client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": prompt}],
            stream=stream
        )
        
        if stream:
            return response
        return response.choices[0].message.content


class KimiModel(AIModelBase):
    """Kimi AI模型实现"""
    
    def __init__(self):
        config = Config()
        self.api_key = config.get_api_key('kimi')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.api_url = "https://api.moonshot.cn/v1/chat/completions"
    
    def analyze(
        self,
        prompt: str,
        stream: bool = False
    ) -> Union[str, Generator]:
        data = {
            "model": "moonshot-v1-8k",
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=data,
            stream=stream
        )
        
        if response.status_code != 200:
            raise Exception(f"Kimi API请求失败: {response.text}")
        
        if stream:
            return self._handle_stream_response(response)
        return response.json()["choices"][0]["message"]["content"]
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        for line in response.iter_lines():
            if line:
                if line.startswith(b"data: "):
                    json_str = line[6:].decode('utf-8')
                    if json_str.strip() == "[DONE]":
                        break
                    chunk = json.loads(json_str)
                    if chunk["choices"][0]["delta"].get("content"):
                        yield chunk


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
            model="gpt-4o",  # 或使用其他可用模型
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

def get_cost_price(symbol: str) -> float:
    """获取指定股票的持仓成本价格
    
    Args:
        symbol: 股票代码
        
    Returns:
        float: 持仓成本价格,如果未找到返回0
    """
    portfolio_file = os.path.join(os.path.dirname(__file__), 'config/portfolio_stocks.csv')
    try:
        df = pd.read_csv(portfolio_file)
        cost_price = df[df['股票代码'].astype(str) == str(symbol)]['持仓成本'].iloc[0]
        return float(cost_price)
    except Exception as e:
        print(f"获取股票{symbol}持仓成本时出错: {str(e)}")
        return 0.0



def get_stock_analysis_prompt(
    symbol: str,
    stock_data: pd.DataFrame,
    stock_name: str, 
    basic_info: dict, 
    news_list: list, 
    include_backtest: bool = True
) -> str:
    """
    优化后的函数，用于生成针对股票的分析提示词（Prompt）。
    结合Chandelier Exit策略、其他技术指标和资讯，帮助LLM生成更深入的交易决策分析。
    
    Args:
        symbol (str): 股票代码
        stock_data (pd.DataFrame): 近30交易日行情数据，需包含以下列：
            ['Close', 'Pct_change', 'ATR', '多头止损', '空头止损',
             'MACD', 'MACD_SIGNAL', 'MACD_HIST',
             'RSI_6','RSI_12','RSI_24',
             'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER',
             'ZLSMA_20', 'ZLSMA_60',
             '夏普比率', '最大回撤', '胜率', '总收益', '最新信号']
        stock_name (str): 股票简称
        basic_info (dict): 股票基本信息，如{'总市值': 'xxx', '行业': 'xxx', ...}
        news_list (list): 最新资讯列表，元素包含{'publish_time', 'title', 'content'}
        include_backtest (bool): 是否需要在提示中包含回测指标（默认True）
    
    Returns:
        str: 优化后的分析提示词（Prompt）。
    """

    # 简单的容错：若stock_data行数不足2行，直接给出提示
    if len(stock_data) < 2:
        return (
            f"数据不足：仅有 {len(stock_data)} 条记录，无法生成有效分析。"
            "请提供至少2个交易日的行情数据。"
        )

    # ========== 1. 提取最新行情、技术指标等 ========== #
    latest_row = stock_data.iloc[-1]
    prev_row = stock_data.iloc[-2]

    # 最新价格和涨跌幅
    current_price = round(latest_row['Close'], 2)
    pct_change = round(latest_row['Pct_change'], 2)

    # Chandelier Exit (吊灯止损) 相关
    atr = round(prev_row['ATR'], 2)
    long_stop = round(prev_row['多头止损'], 2)
    short_stop = round(prev_row['空头止损'], 2)

    # 回测指标
    sharpe_ratio = round(prev_row['夏普比率'], 2) if '夏普比率' in prev_row else None
    max_drawdown = round(prev_row['最大回撤'], 2) if '最大回撤' in prev_row else None
    win_rate = round(prev_row['胜率']*100, 2) if '胜率' in prev_row else None
    total_return = round(prev_row['总收益']*100, 2) if '总收益' in prev_row else None
    latest_signal = prev_row['最新信号'] if '最新信号' in prev_row else None

    # 技术指标
    macd = round(latest_row['MACD'], 2)
    macd_signal = round(latest_row['MACD_SIGNAL'], 2)
    macd_hist = round(latest_row['MACD_HIST'], 2)
    rsi_6 = round(latest_row['RSI_6'], 2)
    rsi_12 = round(latest_row['RSI_12'], 2)
    rsi_24 = round(latest_row['RSI_24'], 2)
    boll_upper = round(latest_row['BOLL_UPPER'], 2)
    boll_middle = round(latest_row['BOLL_MIDDLE'], 2)
    boll_lower = round(latest_row['BOLL_LOWER'], 2)
    zlsma_20 = round(latest_row['ZLSMA_20'], 2)
    zlsma_60 = round(latest_row['ZLSMA_60'], 2)

    # 基本信息
    basic_info_text = "\n".join([f"{k}: {v}" for k, v in basic_info.items()])

    # 最新资讯格式化
    if news_list:
        # 截取content前200字
        news_text = "\n".join([
            f"- {news['publish_time']}: {news['title']}\n  {news['content'][:200]}..."
            for news in news_list
        ])
    else:
        news_text = "无最新资讯"

    # 持仓成本信息
    cost_price = get_cost_price(symbol)
    if cost_price > 0:
        cost_info = f"当前持仓成本: {round(cost_price, 2)}"
    else:
        cost_info = "无持仓成本信息"

    # ========== 2. 持仓建议逻辑 ========== #
    if cost_price > 0:
        if current_price > cost_price * 1.05:
            position_plan = "建议继续持有或部分止盈，保护已有利润。"
        elif long_stop < current_price <= cost_price:
            position_plan = (
                "当前价格接近或低于持仓成本，建议严格关注多头止损并制定减仓计划。"
            )
        elif current_price <= long_stop:
            position_plan = "价格已低于多头止损，建议止损离场，减少损失。"
        else:
            position_plan = "当前价格表现平稳，建议继续观察，等待明确信号。"
    else:
        position_plan = "无持仓，无需制定持仓计划。"

    # ========== 3. MACD顶背离检测 ========== #
    macd_divergence = "未检测到顶背离。"
    if macd < round(prev_row['MACD'], 2) and current_price > round(prev_row['Close'], 2):
        macd_divergence = "检测到MACD顶背离，建议关注潜在风险，考虑减仓或止盈。"

    # ========== 4. 角色设定与深度分析需求 ========== #
    # 通过在提示中增加更明确的角色和分析指引，让模型输出更深入的内容
    role_intro = f"""
你是一名在金融行业拥有超过十年经验的资深量化交易员，熟悉多种交易策略和风控体系。
请基于所提供的 {stock_name}（{symbol}）的最新行情、基本面数据以及资讯，结合 Chandelier Exit（吊灯止损）策略，
深入分析并输出专业报告。你可以充分运用技术分析、数据建模以及宏观行业洞察，帮助我们制定更全面的交易计划。
"""

    # ========== 5. 详细分析要求，引导输出结构 ========== #
    # 在analysis_requirements中明确列出希望模型逐条回应的分析重点
    analysis_requirements = f"""
【分析要求】  

1. **行情回顾与多空格局**  
   - 总结 {symbol} 近30个交易日的价格走势与成交量变化，说明近期涨跌幅是否反映了多空情绪的转变。
   - 结合 ATR（{atr}）等波动性指标，判断当前市场情绪是偏乐观还是谨慎。

2. **Chandelier Exit策略深入分析**  
   - 回顾该策略的核心逻辑和历史表现（夏普比率: {sharpe_ratio}, 最大回撤: {max_drawdown}%, 胜率: {win_rate}%, 总收益: {total_return}%）。
   - 分析多头止损价格 {long_stop}、空头止损价格 {short_stop} 与当前股价({current_price})之间的关系，探讨其有效性。
   - 若有背离信号或风险提示（如MACD顶背离、RSI临界值等），请深入阐述。

3. **技术指标交叉验证**  
   - 从MACD、RSI、BOLL、ZLSMA等角度，逐一解释其意义并判断当前是强势还是谨慎信号。
   - 判断这些指标是否需要进一步确认，如等待量能配合、或参考其他周期的K线形态。

4. **资讯与基本面解读**  
   - 将最新资讯中的重大信息提炼出来，分析其对公司或行业的正负面影响。
   - 若消息面存在矛盾（如同一时间出现多空分歧），请给出如何辨别和甄别的建议。

5. **深入的建仓与清仓策略**  
   - 针对“多头止损价 {long_stop} 上方的区域是否适合建仓”，给出更细化的价格区间及分批建仓思路。
   - 若出现指标矛盾或信号减弱，如何执行止盈止损，包括参考价格区间、分批卖出的计划等。

6. **风险控制与情景推演**  
   - 结合胜率偏低（{win_rate if win_rate else '未知'}%）和夏普比率不佳（{sharpe_ratio if sharpe_ratio else '未知'}），如何调整仓位与资金管理。
   - 模拟极端行情或公司突发公告时的应对方案（快速止损、减仓或观望）。

7. **最终交易计划与执行细则**  
   - 请综合以上分析，提出在下一个交易日/短期内可行的交易方案，包括：初始买入价、加仓时机、止损和止盈目标。
   - 特别说明潜在不确定因素与风险提示，帮助投资者做好资金管理。
"""

    # ========== 6. 组织最终 Prompt 文本 ========== #
    prompt = f"""
{role_intro}

【股票基本信息】  
{basic_info_text}

【当前价格信息】  
- 当前价格: {current_price:.2f}  
- 涨跌幅: {pct_change:.2f}%  
- 持仓成本: {cost_info}

【Chandelier Exit指标】  
- ATR值: {atr:.2f}  
- 多头止损价格: {long_stop:.2f}  
- 空头止损价格: {short_stop:.2f}
- 夏普比率: {sharpe_ratio if sharpe_ratio is not None else '未知'}
- 最大回撤: {max_drawdown if max_drawdown is not None else '未知'}%
- 胜率: {win_rate if win_rate is not None else '未知'}%
- 总收益: {total_return if total_return is not None else '未知'}%
- 最新信号: {latest_signal if latest_signal is not None else '未知'}

【技术指标】  
- MACD: {macd:.2f}, 信号线: {macd_signal:.2f}, 柱状图: {macd_hist:.2f}  
- RSI(6): {rsi_6:.2f}, RSI(12): {rsi_12:.2f}, RSI(24): {rsi_24:.2f}  
- BOLL(上轨): {boll_upper:.2f}, BOLL(中轨): {boll_middle:.2f}, BOLL(下轨): {boll_lower:.2f}  
- ZLSMA(20): {zlsma_20:.2f}, ZLSMA(60): {zlsma_60:.2f}

【持仓建议】  
{position_plan}

【MACD顶背离分析】  
{macd_divergence}

【最新资讯与链接】  
{news_text}

{analysis_requirements}

请根据以上信息，结合你的量化交易经验、资金管理策略和行业分析能力，
给出具有深度、逻辑清晰、且能实际执行的交易分析报告。
"""
    print(prompt)
    return prompt

def get_backtest_results(symbol, start_date=None, end_date=None, strategy_params=None):
    """
    调用回测函数获取指定股票的回测结果
    
    参数：
    - symbol: str，股票代码
    - start_date: str，可选，开始日期，格式'YYYY-MM-DD'，默认一年前
    - end_date: str，可选，结束日期，格式'YYYY-MM-DD'，默认当前日期
    - strategy_params: dict，可选，策略参数字典
    
    返回：
    - dict，回测结果
    """
    from chandelier_zlsma_test import run_backtest
    
    # 如果未指定日期，使用默认值
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        
    # 如果未指定策略参数，检查是否存在优化参数文件
    if strategy_params is None:
        optimization_file = f'results/{symbol}_ChandelierZlSmaStrategy_optimization_results.csv'
        if os.path.exists(optimization_file):
            # 读取优化参
            opt_params = pd.read_csv(optimization_file).iloc[-1]
            strategy_params = {
                'period': int(opt_params['period']),
                'mult': float(opt_params['mult']), 
                'investment_fraction': float(opt_params['investment_fraction']),
                'max_pyramiding': int(opt_params['max_pyramiding'])
            }
        else:
            # 使用默认参数
            strategy_params = {
                'period': 14,
                'mult': 2.0,
                'investment_fraction': 0.8,
                'max_pyramiding': 0
            }
            
    try:
        # 调用回测函数
        results = run_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            printlog=True,
            **strategy_params
        )
        
        return results
    except Exception as e:
        return {
            'error': f'回测过程发生错误: {str(e)}'
        }


def analyze_stock(symbol, start_date, end_date, model, stream=False):
    try:
        # 检查是否存在当天的分析结果文件
        now = datetime.now()
        today = now.strftime('%Y%m%d')
        model_name = model.__class__.__name__.lower().replace('model','')
        result_file = f"AIResult/{symbol}_{today}_{model_name}.md"
        
        # 确保AIResult目录存在
        os.makedirs('AIResult', exist_ok=True)
        
        if os.path.exists(result_file):
            # 判断当前时间是否超过下午4点
            current_hour = now.hour
            
            # 获取文件最后修改时间
            file_mtime = datetime.fromtimestamp(os.path.getmtime(result_file))
            
            # 如果当前时间超过下午4点,需要确保文件是在当天下午4点后生成的
            if current_hour >= 16:
                file_date = file_mtime.date()
                file_hour = file_mtime.hour
                
                if file_date == now.date() and file_hour >= 16:
                    # 文件是在当天下午4点后生成的,可以直接使用
                    with open(result_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    if stream:
                        for char in content:
                            yield char
                    else:
                        yield content
                    return
            else:
                # 当前时间未超过下午4点,可以直接使用已有文件
                with open(result_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if stream:
                    for char in content:
                        yield char
                else:
                    yield content
                return
            
        # 获取股票数据
        if symbol.startswith(('51', '159')):
            stock_data = get_etf_data(symbol, start_date, end_date)
        elif symbol.isdigit():
            stock_data = get_stock_data(
                symbol,
                start_date,
                end_date,
                include_macd=True,
                include_rsi=True,
                include_boll=True,
                include_zlsma=True,
                include_chandelier=True
            )
        else:
            stock_data = get_us_stock_data(symbol, start_date, end_date)
            
        if stock_data.empty:
            yield "未找到股票数据"
            return

        # 获取股票名称和基本信息
        stock_name = get_stock_name(symbol)
        basic_info = get_stock_basic_info(symbol)
        
        # 获取最近的新闻（限制为5条）
        news_list = get_stock_news(symbol, limit=5)

        # 构建提示信息，使用Markdown格式
        prompt = get_stock_analysis_prompt(symbol, stock_data, stock_name, basic_info, news_list)
        
        # 生成输出文件名
        output_file = f"AIResult/{symbol}_{today}_{model_name}.md"
        
        # 获取分析结果
        if stream:
            # 流式分析,同时输出和收集结果
            result = []
            for chunk in model.analyze(prompt, stream=True):
                if chunk:
                    if isinstance(model, ZhipuAIModel):
                        content = chunk.choices[0].delta.content
                    elif isinstance(model, OpenAIModel):
                        content = chunk  # OpenAI 流式响应已在模型类中处理
                    else:  # KimiModel
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        result.append(content)
                        yield content  # 流式输出每个片段
                        
            # 完整结果保存到文件
            complete_result = "".join(result)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(complete_result)
                
        else:
            # 一次性分析
            result = model.analyze(prompt, stream=False)
            # 保存分析结果到文件
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)
            yield result
            
    except Exception as e:
        logger.error(f"分析股票时发生错误: {str(e)}", exc_info=True)
        yield f"分析过程中发生错误: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description='股票分析工具')
    parser.add_argument('--symbol', type=str, required=True, help='股票代码')
    parser.add_argument(
        '--model',
        type=str,
        choices=['zhipu', 'kimi', 'openai'],
        default='zhipu',
        help='选择AI模型'
    )
    parser.add_argument('--stream', action='store_true', help='是否使用流式输出')
    args = parser.parse_args()
    
    try:
        # 初始化选择的AI模型
        if args.model == 'zhipu':
            model = ZhipuAIModel()
        elif args.model == 'openai':
            model = OpenAIModel()
        else:
            model = KimiModel()
        
        # 计算日期范围（最近30个交易日）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=50)).strftime('%Y-%m-%d')
        
        # 确保AIResult目录存在
        os.makedirs('AIResult', exist_ok=True)
        
        # 生成输出文件名
        output_file = f"AIResult/{args.symbol}_{datetime.now().strftime('%Y%m%d')}_{args.model}.md"
        
        if args.stream:
            # 流式输出并保存
            result_chunks = []
            for chunk in analyze_stock(
                args.symbol,
                start_date,
                end_date,
                model,
                stream=True
            ):
                if chunk:
                    print(chunk, end='', flush=True)
                    result_chunks.append(chunk)
            
            # 将流式结果写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(''.join(result_chunks))
        else:
            # 阻塞模式
            result = analyze_stock(
                args.symbol,
                start_date,
                end_date,
                model,
                stream=False
            )
            print(result)
            
            # 保存结果到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
    except Exception as e:
        logger.error(f"程序执行错误: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()