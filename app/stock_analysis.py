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



def get_stock_analysis_prompt(symbol: str, stock_data: pd.DataFrame, stock_name: str, basic_info: dict, news_list: list, include_backtest: bool = True) -> str:
    """生成用于分析股票的prompt"""
    data_description = stock_data.to_string()
    
    # 格式化基本信息
    basic_info_text = "\n".join([f"{k}: {v}" for k, v in basic_info.items()])
    
    # 格式化新闻信息
    news_text = "\n".join([
        f"- {news['publish_time']}: {news['title']}\n  {news['content'][:200]}..."
        for news in news_list
    ])
    
    # 获取持仓成本
    cost_price = get_cost_price(symbol)
    cost_info = f"\n当前持仓成本: {cost_price}" if cost_price > 0 else ""
    
    prompt = f"""
你是一名经验丰富的股票量化交易员，需要根据以下变量进行全面的股票分析，并对下一个交易日的走势进行预判，提供相应的交易策略建议。分析需涵盖技术指标解读、趋势判断、风险评估、交易策略建议等方面，最终输出简明、直接的操作建议。
以下是股票{stock_name}的信息
1. 股票基本信息：
{basic_info_text}

2. 行情数据（30个交易日）：
{data_description} 

3. 最新资讯与链接：
{news_text}

分析要求

1. 公司概况：
给出公司的主营业务、行业地位、竞争优势、财务状况、管理层、发展前景等。

2. 技术分析：
结合MACD、RSI、BOLL分析趋势是否处于超买、超卖或震荡区间。
判断当前股票是否处于关键支撑位或压力位。

3. 量化策略应用：
使用吊顶止损指标(在行情数据中包含)，计算当前的止损参考点，并分析风险。
应用ZSLAM指标(在行情数据中包含)，评估当前趋势的强度与方向，判断市场情绪。

4. 基本面分析：
提取并分析最新资讯对股票价格的潜在影响。
判断行业政策或市场动态是否可能改变投资逻辑。

5. 下一个交易日走势预判：
基于上述分析，对下一个交易日的价格走势进行预测。
评估可能的波动范围和方向。
对各种可能的开盘情况（高开、低开、平开、高开低走、低开高走等）做出对应的交易策略建议。

6. 交易建议：
针对短线、中线投资，分别提供操作建议（如建仓、加仓、减仓、清仓）。
给出止盈止损点位，预期收益风险比。
针对持仓和空仓，分别给出操作建议。

7. 持仓成本分析：
{cost_info}，请结合当前个股走势，给出更有针对性的建议（如止盈止损、加仓减仓）。

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