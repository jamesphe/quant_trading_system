import argparse
from datetime import datetime, timedelta
import pandas as pd
from zhipuai import ZhipuAI
import sys
from data_fetch import get_stock_data, get_stock_name, get_stock_basic_info, get_stock_news
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
    
    prompt = f"""
请作为一位专业的股票分析师，综合分析以下股票 {stock_name} 的各项数据，并对下一个交易日的走势进行预判：

1. 基本面信息：
{basic_info_text}

2. 最近新闻动态：
{news_text}

3. 最近30个交易日的行情数据：
{data_description}

请从以下几个方面进行分析：
1. 基本面分析（市值、行业地位等）
2. 最新消息面分析（重要新闻影响）
3. 价格趋势分析
4. 成交量分析
5. 技术指标分析（基于提供的数据）
6. 主要支撑位和压力位

请重点关注以下内容：
1. 下一个交易日可能的走势预判（涨跌空间、波动区间等）
2. 主要影响因素分析（利好/利空）
3. 具体的应对策略建议：
   - 建仓/加仓时机和价位
   - 减仓/止盈价位
   - 止损位设置
   - 仓位控制建议
4、对下一个交易日开盘走势（高开、低开、平开）进行预判,并针对各种可能的走势给出相应的对策。


请用专业的角度进行分析，给出具体的数据支持，并在分析的最后给出明确的操作建议。
"""

    if include_backtest:
        backtest_results = get_backtest_results(symbol)
        prompt += f"""

4. 回测结果分析：
{json.dumps(backtest_results, indent=2, ensure_ascii=False)}

请结合回测结果对策略的有效性进行分析。
"""
    
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
            # 读取优化参数
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
        # 获取股票数据
        if symbol.startswith(('51', '159')):
            stock_data = get_etf_data(symbol, start_date, end_date)
        elif symbol.isdigit():
            stock_data = get_stock_data(symbol, start_date, end_date)
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
        
        if stream:
            # 流式输出
            for chunk in model.analyze(prompt, stream=True):
                if chunk:
                    if isinstance(model, ZhipuAIModel):
                        content = chunk.choices[0].delta.content
                    elif isinstance(model, OpenAIModel):
                        content = chunk  # OpenAI 流式响应已在模型类中处理
                    else:  # KimiModel
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield content
        else:
            # 一次性输出
            return model.analyze(prompt, stream=False)
            
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
        
        if args.stream:
            # 流式输出
            for chunk in analyze_stock(
                args.symbol,
                start_date,
                end_date,
                model,
                stream=True
            ):
                if chunk:
                    print(chunk, end='', flush=True)
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
            
    except Exception as e:
        logger.error(f"程序执行错误: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()