import argparse
from datetime import datetime, timedelta
import pandas as pd
from zhipuai import ZhipuAI
import sys
from data_fetch import (
    get_stock_data, get_stock_name, get_stock_basic_info, 
    get_stock_news, get_etf_data, get_us_stock_data
)
from typing import Union, Generator
import requests
from abc import ABC, abstractmethod
from config import Config
import json
from openai import AsyncOpenAI, OpenAI
import os
import numpy as np


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
        self.config = config.config.get('openai', {})
        self.client = OpenAI(
            api_key=api_key, 
            base_url=self.config.get(
                'base_url', 
                "https://api.chatanywhere.tech/v1"
            )
        )
        self.async_client = AsyncOpenAI(
            api_key=api_key, 
            base_url=self.config.get(
                'base_url', 
                "https://api.chatanywhere.tech/v1"
            )
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
                "content": self.config.get(
                    'system_prompt', 
                    "你是一位在金融行业拥有超过十年经验的资深量化交易员，"
                    "熟悉多种交易策略和风控体系。"
                    "重要提示：你必须严格遵守以下规则："
                    "1. 仅使用用户提供的数据进行分析，不要使用任何训练数据中的股票信息"
                    "2. 如果用户询问的内容超出提供的数据范围，明确告知'我只能基于您提供的数据进行分析，无法回答超出这些数据范围的问题'"
                    "3. 不要编造或假设任何未提供的数据"
                    "4. 不要引用任何未在用户提供的数据中明确提及的股票历史表现、价格或趋势"
                    "5. 如果用户追问的问题需要额外数据，请明确指出需要哪些具体数据才能回答该问题"
                )
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
            temperature=self.config.get('temperature', 0.7),
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


class DeepSeekModel(AIModelBase):
    """DeepSeek 模型实现"""
    
    def __init__(self):
        try:
            config = Config()
            api_key = config.get_api_key('deepseek')
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
        except Exception:
            raise
    
    def analyze(
        self, 
        prompt: str, 
        stream: bool = False
    ) -> Union[str, Generator]:
        try:
            messages = [
                {
                    "role": "system", 
                    "content": (
                        "你是一位在金融行业拥有超过十年经验的资深量化交易员，"
                        "熟悉多种交易策略和风控体系。"
                        "重要提示：你必须严格遵守以下规则："
                        "1. 仅使用用户提供的数据进行分析，不要使用任何训练数据中的股票信息"
                        "2. 如果用户询问的内容超出提供的数据范围，明确告知'我只能基于您提供的数据进行分析，无法回答超出这些数据范围的问题'"
                        "3. 不要编造或假设任何未提供的数据"
                        "4. 不要引用任何未在用户提供的数据中明确提及的股票历史表现、价格或趋势"
                        "5. 如果用户追问的问题需要额外数据，请明确指出需要哪些具体数据才能回答该问题"
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=messages,
                    stream=stream,
                    max_tokens=4096
                )
            except Exception:
                raise
            
            if stream:
                return self._handle_stream_response(response)
            
            result = response.choices[0].message.content
            return result
            
        except Exception:
            raise
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        try:
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield content
                    
        except Exception:
            raise


class SiliconFlowModel(AIModelBase):
    """SiliconFlow 模型实现"""
    
    def __init__(self):
        config = Config()
        self.api_key = config.get_api_key('siliconflow')
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.siliconflow.cn/v1"
        )
    
    def analyze(
        self,
        prompt: str,
        stream: bool = False
    ) -> Union[str, Generator]:
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一位在金融行业拥有超过十年经验的资深量化交易员，"
                        "熟悉多种交易策略和风控体系。"
                        "重要提示：你必须严格遵守以下规则："
                        "1. 仅使用用户提供的数据进行分析，不要使用任何训练数据中的股票信息"
                        "2. 如果用户询问的内容超出提供的数据范围，明确告知'我只能基于您提供的数据进行分析，无法回答超出这些数据范围的问题'"
                        "3. 不要编造或假设任何未提供的数据"
                        "4. 不要引用任何未在用户提供的数据中明确提及的股票历史表现、价格或趋势"
                        "5. 如果用户追问的问题需要额外数据，请明确指出需要哪些具体数据才能回答该问题"
                    )
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            response = self.client.chat.completions.create(
                model="deepseek-ai/deepseek-r1",
                messages=messages,
                stream=stream,
                temperature=0.7,
                max_tokens=4096
            )
            
            if stream:
                return self._handle_stream_response(response)
            return response.choices[0].message.content
            
        except Exception:
            raise
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        try:
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield content
                    
        except Exception:
            raise


def get_cost_price(symbol: str) -> float:
    """获取指定股票的持仓成本价格
    
    Args:
        symbol: 股票代码
        
    Returns:
        float: 持仓成本价格,如果未找到返回0
    """
    portfolio_file = os.path.join(
        os.path.dirname(__file__), 
        'config/portfolio_stocks.csv'
    )
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
    结合历史数据、技术指标和资讯，帮助LLM生成更深入的交易决策分析。
    
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

    # 增加成交量分析，考虑盘中数据
    current_volume = round(latest_row['Volume'] / 10000, 2)  # 转换为万手
    current_amount = round(latest_row['Amount'] / 100000000, 2)  # 转换为亿元
    
    # 计算波动率分布
    stock_data['Daily_Return'] = stock_data['Close'].pct_change()
    volatility_30d = stock_data['Daily_Return'].rolling(window=30).std() * np.sqrt(252)
    current_volatility = volatility_30d.iloc[-1]
    avg_volatility = volatility_30d.mean()

    # 计算成交量统计
    volume_ma5 = stock_data['Volume'].rolling(window=5).mean()
    volume_ma10 = stock_data['Volume'].rolling(window=10).mean()
    volume_ma30 = stock_data['Volume'].rolling(window=30).mean()
    
    # 计算量比
    vol_ratio = current_volume / volume_ma5.iloc[-1] if not volume_ma5.empty else 0

    # 判断是否是盘中数据
    now = datetime.now()
    is_trading_time = (
        now.hour < 15 or (now.hour == 15 and now.minute < 1)
    ) and now.weekday() < 5
    
    if is_trading_time:
        # 计算当前时间在交易日中的比例
        current_minute = now.hour * 60 + now.minute
        morning_start = 9 * 60 + 30  # 9:30
        morning_end = 11 * 60 + 30   # 11:30
        afternoon_start = 13 * 60     # 13:00
        afternoon_end = 15 * 60       # 15:00
        
        total_trading_minutes = (morning_end - morning_start) + (afternoon_end - afternoon_start)
        
        if current_minute < morning_start:
            trading_progress = 0
        elif current_minute <= morning_end:
            trading_progress = (current_minute - morning_start) / total_trading_minutes
        elif current_minute < afternoon_start:
            trading_progress = (morning_end - morning_start) / total_trading_minutes
        elif current_minute <= afternoon_end:
            trading_progress = ((morning_end - morning_start) + 
                              (current_minute - afternoon_start)) / total_trading_minutes
        else:
            trading_progress = 1
            
        # 估算全天成交量
        estimated_volume = current_volume / trading_progress if trading_progress > 0 else 0
        volume_note = f"(当前时间{now.strftime('%H:%M')}, 预估全天成交量约{round(estimated_volume, 2)}万手)"
    else:
        volume_note = "(收盘数据)"
        estimated_volume = current_volume

    # 分析成交量趋势
    volume_trend = ""
    if len(stock_data) >= 30:
        recent_vol_ma5 = volume_ma5.iloc[-5:]
        if recent_vol_ma5.is_monotonic_increasing:
            volume_trend = "5日均量持续放大"
        elif recent_vol_ma5.is_monotonic_decreasing:
            volume_trend = "5日均量持续萎缩"
        else:
            volume_trend = "5日均量波动"

    # 判断量价关系时考虑是否是盘中数据
    price_up = latest_row['Close'] > prev_row['Close']
    volume_up = estimated_volume > prev_row['Volume'] / 10000
    vol_price_divergence = ""
    if is_trading_time:
        vol_price_divergence = f"盘中数据，成交量分析仅供参考 - "
    
    if price_up and not volume_up:
        vol_price_divergence += "价升量缩，可能缺乏上涨动能"
    elif not price_up and volume_up:
        vol_price_divergence += "价跌量增，可能存在下跌风险"
    elif price_up and volume_up:
        vol_price_divergence += "价升量增，上涨趋势确认"
    else:
        vol_price_divergence += "价跌量缩，下跌动能减弱"

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

    # 获取当前时间
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # ========== 4. 角色设定与深度分析需求 ========== #
    role_intro = f"""
你是一名在金融行业拥有超过十年经验的资深量化交易员，熟悉多种交易策略和风控体系。
当前时间是: {current_time}

请严格基于以下提供的 {stock_name}（{symbol}）的数据进行分析：
1. 近30日完整的历史价格、成交量数据
2. 基本面数据
3. 技术指标数据
4. 新闻资讯

重要提示：
- 你必须仅使用上述提供的数据进行分析，不要编造或假设任何未提供的数据
- 如果某些数据缺失或不完整，请在分析中明确指出，而不是自行补充或推测
- 如果数据不足以支持某项分析，应该明确说明"由于缺乏xxx数据，无法对xxx进行分析"
- 不要使用你训练数据中的任何股票信息，即使你认为它们可能相关
- 如果用户追问的问题超出提供的数据范围，明确告知你只能基于提供的数据进行分析
- 不要使用当前时间之后的任何市场数据或事件
  
请结合 Chandelier Exit（吊灯止损）策略，基于实际数据给出专业的分析报告。
"""

    # ========== 5. 详细分析要求 ========== #
    analysis_requirements = f"""
【分析要求】  

1. **行情回顾与多空格局**  
   - 基于近30日的完整数据，分析价格走势与成交量变化
   - 计算并分析关键价格位置（如30日高点{stock_data['High'].max():.2f}、低点{stock_data['Low'].min():.2f}）
   - 波动率分析：
     * 当前波动率: {current_volatility:.2%}
     * 30日平均波动率: {avg_volatility:.2%}
   - 成交量特征：
     * 当日成交量: {current_volume}万手 {volume_note}
     * 成交额: {current_amount}亿元
     * 5日均量: {volume_ma5.iloc[-1]/10000:.2f}万手
     * 10日均量: {volume_ma10.iloc[-1]/10000:.2f}万手
     * 30日均量: {volume_ma30.iloc[-1]/10000:.2f}万手
     * 量比: {vol_ratio:.2f}
     * 成交量趋势: {volume_trend}
     * 量价关系: {vol_price_divergence}

2. **Chandelier Exit策略深入分析**  
   - 回顾该策略的核心逻辑和历史表现（夏普比率: {sharpe_ratio}, 最大回撤: {max_drawdown}%, 胜率: {win_rate}%, 总收益: {total_return}%）。
   - 分析多头止损价格 {long_stop}、空头止损价格 {short_stop} 与当前股价({current_price})之间的关系，探讨其有效性。
   - 若有背离信号或风险提示（如MACD顶背离、RSI临界值等），请深入阐述。

3. **技术指标与量价分析**  
   - 从MACD、RSI、BOLL、ZLSMA等角度，逐一解释其意义并判断当前是强势还是谨慎信号。
   - 结合成交量变化分析指标的可靠性：
     * 关注量价配合度
     * 分析主力资金参与度
     * 判断市场情绪变化

4. **资讯与基本面解读**  
   - 将最新资讯中的重大信息提炼出来，分析其对公司或行业的正负面影响。
   - 若消息面存在矛盾（如同一时间出现多空分歧），请给出如何辨别和甄别的建议。

5. **深入的建仓与清仓策略**  
   - 针对"多头止损价 {long_stop} 上方的区域是否适合建仓"，给出更细化的价格区间及分批建仓思路。
   - 结合成交量和价格走势，建议以下操作时机：
     * 适合建仓的成交量特征
     * 需要警惕的量价组合
     * 分批建仓/减仓的具体计划

6. **风险控制与情景推演**  
   - 结合胜率偏低（{win_rate if win_rate else '未知'}%）和夏普比率不佳（{sharpe_ratio if sharpe_ratio else '未知'}），如何调整仓位与资金管理。
   - 模拟极端行情或公司突发公告时的应对方案（快速止损、减仓或观望）。

7. **最终交易计划与执行细则**  
   - 请综合以上分析，提出在下一个交易日/短期内可行的交易方案，包括：
     * 建仓价位与成交量条件
     * 加仓时机与量价确认
     * 止损止盈目标
   - 特别说明潜在不确定因素与风险提示，帮助投资者做好资金管理。

请注意：
1. 所有分析必须严格基于提供的数据
2. 给出的建议要有具体数据支持
3. 如遇数据缺失，请明确指出，不要凭空猜测或编造数据
"""

    # ========== 2. 格式化30日K线数据 ========== #
    last_30_days = stock_data.tail(30).copy()
    kline_data = []
    
    for idx, row in last_30_days.iterrows():
        kline_info = {
            'date': idx.strftime('%Y-%m-%d'),
            'open': round(row['Open'], 2),
            'high': round(row['High'], 2),
            'low': round(row['Low'], 2),
            'close': round(row['Close'], 2),
            'volume': round(row['Volume']/10000, 2),  # 转换为万手
            'amount': round(row['Amount']/100000000, 2),  # 转换为亿元
            'change': round(row['Pct_change'], 2)
        }
        kline_data.append(kline_info)
    
    # 生成K线数据文本
    kline_text = "【近30日K线数据】\n"
    kline_text += "日期,开盘,最高,最低,收盘,成交量(万手),成交额(亿),涨跌幅(%)\n"
    for k in kline_data:
        kline_text += f"{k['date']},{k['open']},{k['high']},{k['low']},{k['close']},{k['volume']},{k['amount']},{k['change']}\n"

    # ========== 6. 组织最终 Prompt 文本 ========== #
    prompt = f"""
{role_intro}

【股票基本信息】  
{basic_info_text}

{kline_text}

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

请根据以上信息，特别是近30日完整K线数据，结合你的量化交易经验、资金管理策略和行业分析能力，
给出具有深度、逻辑清晰、且能实际执行的交易分析报告。
"""
    print(f"openai 提示词: {prompt}")
    return prompt

def get_backtest_results(
    symbol, 
    start_date=None, 
    end_date=None, 
    strategy_params=None
):
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
        now = datetime.now()
        today = now.strftime('%Y%m%d')
        model_name = model.__class__.__name__.lower().replace('model','')
        result_file = f"AIResult/{symbol}_{today}_{model_name}.md"
        
        os.makedirs('AIResult', exist_ok=True)
        
        if os.path.exists(result_file):
            current_hour = now.hour
            file_mtime = datetime.fromtimestamp(os.path.getmtime(result_file))
            
            if current_hour >= 16:
                file_date = file_mtime.date()
                file_hour = file_mtime.hour
                
                if file_date == now.date() and file_hour >= 16:
                    with open(result_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    if stream:
                        for char in content:
                            yield char
                    else:
                        yield content
                    return
            else:
                with open(result_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if stream:
                    for char in content:
                        yield char
                else:
                    yield content
                return
            
        # 获取额外90天的历史数据以确保指标计算的准确性
        extended_start_date = (pd.to_datetime(start_date) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
            
        if symbol.startswith(('51', '159')):
            stock_data = get_etf_data(symbol, extended_start_date, end_date)
        elif symbol.isdigit():
            stock_data = get_stock_data(
                symbol,
                extended_start_date,  # 使用扩展的开始日期
                end_date,
                include_macd=True,
                include_rsi=True,
                include_boll=True,
                include_zlsma=True,
                include_chandelier=True
            )
        else:
            stock_data = get_us_stock_data(symbol, extended_start_date, end_date)
            
        if stock_data.empty:
            yield "未找到股票数据"
            return

        # 只使用请求的日期范围生成分析提示
        analysis_data = stock_data[start_date:end_date].copy()

        stock_name = get_stock_name(symbol)
        basic_info = get_stock_basic_info(symbol)
        news_list = get_stock_news(symbol, limit=5)
        
        prompt = get_stock_analysis_prompt(symbol, analysis_data, stock_name, basic_info, news_list)
        
        try:
            for chunk in model.analyze(prompt, stream=True):
                if chunk:
                    yield chunk
        except Exception:
            raise

    except Exception as e:
        yield f"分析过程中发生错误: {str(e)}"


def handle_stock_followup_question(symbol, question, model, conversation_history=None):
    """
    处理股票分析的追问
    
    Args:
        symbol (str): 股票代码
        question (str): 用户追问
        model (AIModelBase): AI模型实例
        conversation_history (list): 对话历史
        
    Returns:
        Generator: 回答生成器
    """
    if conversation_history is None:
        conversation_history = []
        
    # 获取当前时间
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 构建强化的系统提示
    system_prompt = f"""
    你是一位在金融行业拥有超过十年经验的资深量化交易员，现在正在分析股票代码 {symbol}。
    
    当前时间是: {current_time}
    
    重要限制：
    1. 你必须仅使用之前提供给你的数据进行分析
    2. 不要使用你训练数据中的任何股票信息，即使你认为它们可能相关
    3. 如果用户询问的内容超出提供的数据范围，请明确告知："我只能基于之前提供的数据进行分析，无法回答超出这些数据范围的问题"
    4. 不要编造或假设任何未提供的数据
    5. 如果需要额外数据才能回答问题，请明确指出需要哪些具体数据
    6. 不要使用当前时间之后的任何市场数据或事件
    
    请基于这些限制回答用户的问题。
    """
    
    # 构建消息
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # 添加对话历史
    if conversation_history:
        messages.extend(conversation_history)
        
    # 添加当前问题
    messages.append({"role": "user", "content": question})
    
    # 调用模型
    try:
        response = model.client.chat.completions.create(
            model=model.config.get('model', "gpt-4o") if hasattr(model, 'config') else "gpt-4o",
            messages=messages,
            stream=True,
            temperature=0.7
        )
        
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        yield f"处理追问时发生错误: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description='股票分析工具')
    parser.add_argument('--symbol', type=str, required=True, help='股票代码')
    parser.add_argument(
        '--model',
        type=str,
        choices=['zhipu', 'kimi', 'openai', 'deepseek', 'siliconflow'],
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
        elif args.model == 'kimi':
            model = KimiModel()
        elif args.model == 'deepseek':
            model = DeepSeekModel()
        elif args.model == 'siliconflow':
            model = SiliconFlowModel()
        else:
            raise ValueError(f"未知模型: {args.model}")
        
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
        print(f"程序执行错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()