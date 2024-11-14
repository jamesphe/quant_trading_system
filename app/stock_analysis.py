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


def get_stock_analysis_prompt(stock_data: pd.DataFrame, stock_name: str, basic_info: dict, news_list: list) -> str:
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
请作为一位专业的股票分析师，综合分析以下股票 {stock_name} 的各项数据：

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
7. 短期投资建议

请用专业的角度进行分析，给出具体的数据支持，并在分析的最后给出明确的投资建议。
"""
    return prompt


def analyze_stock(
    symbol: str,
    start_date: str,
    end_date: str,
    model: AIModelBase,
    stream: bool = False
) -> Union[str, Generator]:
    """
    分析股票数据并返回分析结果
    
    参数:
    - symbol: 股票代码
    - start_date: 开始日期
    - end_date: 结束日期
    - model: AI模型实例
    - stream: 是否使用流式输出
    
    返回:
    - 如果stream=False，返回完整的分析文本
    - 如果stream=True，返回生成器，用于流式输出
    """
    try:
        # 获取股票行情数据
        stock_data = get_stock_data(symbol, start_date, end_date)
        if stock_data.empty:
            raise ValueError(f"无法获取股票 {symbol} 的数据")
        
        # 获取股票名称
        stock_name = get_stock_name(symbol)
        
        # 获取股票基本信息
        basic_info = get_stock_basic_info(symbol)
        
        # 获取最近的新闻（限制为5条）
        news_list = get_stock_news(symbol, limit=5)
        
        # 生成分析提示
        prompt = get_stock_analysis_prompt(stock_data, stock_name, basic_info, news_list)
        
        return model.analyze(prompt, stream)
            
    except Exception as e:
        logger.error(f"分析过程发生错误: {str(e)}", exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(description='股票分析工具')
    parser.add_argument('--symbol', type=str, required=True, help='股票代码')
    parser.add_argument(
        '--model',
        type=str,
        choices=['zhipu', 'kimi'],
        default='zhipu',
        help='选择AI模型'
    )
    parser.add_argument('--stream', action='store_true', help='是否使用流式输出')
    args = parser.parse_args()
    
    try:
        # 初始化选择的AI模型
        if args.model == 'zhipu':
            model = ZhipuAIModel()
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
                if args.model == 'zhipu':
                    content = chunk.choices[0].delta.content
                else:
                    content = chunk["choices"][0]["delta"]["content"]
                    
                if content:
                    print(content, end='', flush=True)
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