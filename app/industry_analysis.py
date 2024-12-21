import akshare as ak
import pandas as pd
from openai import OpenAI
from config import Config
from datetime import datetime
import os
from typing import Dict, List, Optional, Tuple, Union, Generator
from data_fetch import get_hot_industries as fetch_hot_industries

class IndustryAnalyzer:
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        初始化行业分析器
        
        参数:
            openai_api_key: OpenAI API密钥（可选）
        """
        # 使用 Config 类获取 API key
        config = Config()
        self.api_key = openai_api_key or config.get_api_key('openai')
        self.client = OpenAI(
            api_key=self.api_key, 
            base_url="https://api.chatanywhere.tech/v1"
        )
            
    def get_hot_industries(self, rise_threshold: float = 2.0, 
                          fund_inflow_threshold: float = 5000) -> pd.DataFrame:
        """
        获取热门行业数据
        
        参数:
            rise_threshold: 涨幅阈值（百分比）
            fund_inflow_threshold: 资金流入阈值（万元）
            
        返回:
            DataFrame包含热门行业数据
        """
        try:
            # 直接获取行业行情数据
            industry_data = ak.stock_board_industry_name_em()
            
            if industry_data.empty:
                print("未获取到行业数据")
                return pd.DataFrame()
                
            # 重命名列
            column_mapping = {
                '板块名称': 'industry_name',
                '涨跌幅': 'change_pct',
                '上涨家数': 'up_count',
                '总市值': 'market_value',
                '换手率': 'turnover_rate',
                '领涨股票': 'leading_stock',
                '领涨股票-涨跌幅': 'leading_stock_pct'
            }
            
            # 选择并重命名列
            df = industry_data[list(column_mapping.keys())].rename(columns=column_mapping)
            
            # 转换数据类型
            # 处理涨跌幅
            df['change_pct'] = pd.to_numeric(
                df['change_pct'].astype(str).str.replace('%', ''),
                errors='coerce'
            ) / 100
            
            # 处理上涨家数
            df['up_count'] = pd.to_numeric(df['up_count'], errors='coerce')
            
            # 处理总市值（去除"亿"字并转换为数值）
            df['market_value'] = pd.to_numeric(
                df['market_value'].astype(str).str.replace('亿', ''),
                errors='coerce'
            )
            
            # 处理换手率
            df['turnover_rate'] = pd.to_numeric(
                df['turnover_rate'].astype(str).str.replace('%', ''),
                errors='coerce'
            ) / 100
            
            # 处理领涨股票涨跌幅
            df['leading_stock_pct'] = pd.to_numeric(
                df['leading_stock_pct'].astype(str).str.replace('%', ''),
                errors='coerce'
            ) / 100
            
            # 筛选热门行业
            hot_industries = df[
                (df['change_pct'] >= rise_threshold/100) &  # 转换为小数
                (df['up_count'] >= 5)  # 至少5家上涨
            ].sort_values(by='change_pct', ascending=False)
            
            if hot_industries.empty:
                print("未找到符合条件的热门行业")
                return pd.DataFrame()
            
            return hot_industries
            
        except Exception as e:
            print(f"获取热门行业数据失败: {e}")
            if 'industry_data' in locals():
                print("列名:", industry_data.columns.tolist())
            return pd.DataFrame()
            
    def analyze_with_llm(self, data: pd.DataFrame, stream: bool = False) -> Union[str, Generator]:
        """使用大语言模型分析行业数据"""
        try:
            # 构建详细的数据摘要
            data_summary = []
            for _, row in data.iterrows():
                industry_name = row['industry_name']
                
                # 基础信息
                industry_info = [
                    f"行业: {industry_name}",
                    f"涨跌幅: {row['change_pct']*100:.2f}%",
                    f"上涨家数: {row['up_count']}",
                    f"总市值: {row['market_value']}亿",
                    f"换手率: {row['turnover_rate']*100:.2f}%",
                    f"领涨股票: {row['leading_stock']}",
                    f"领涨股票涨幅: {row['leading_stock_pct']*100:.2f}%"
                ]
                
                # 获取行业详细数据
                detail = self.analyze_industry_detail(industry_name)
                if detail:
                    industry_info.extend([
                        f"行业成分股总数: {detail['total_stocks']}",
                        f"上涨股票数: {detail['up_stocks']}",
                        f"下跌股票数: {detail['down_stocks']}",
                        f"上涨股票平均涨幅: {detail['avg_up_pct']:.2f}%",
                        f"下跌股票平均跌幅: {detail['avg_down_pct']:.2f}%",
                        f"平均换手率: {detail['avg_turnover_rate']:.2f}%"
                    ])
                
                # 获取龙头股信息
                leaders = self.get_industry_leaders(industry_name)
                if not leaders.empty:
                    industry_info.append("\n行业龙头股:")
                    for _, leader in leaders.iterrows():
                        industry_info.append(
                            f"  - {leader['stock_name']} ({leader['stock_code']}): "
                            f"价格 {leader['price']:.2f}, "
                            f"涨跌幅 {leader['change_pct']:.2f}%, "
                            f"换手率 {leader['turnover_rate']:.2f}%"
                        )
                
                # 添加潜力股信息
                potential_stocks = self.get_industry_potential_stocks(industry_name, top_n=5)
                if not potential_stocks.empty:
                    industry_info.append("\n行业潜力股:")
                    for _, stock in potential_stocks.iterrows():
                        industry_info.append(
                            f"  - {stock['stock_name']} ({stock['stock_code']}): "
                            f"价格 {stock['price']:.2f}, "
                            f"涨跌幅 {stock['change_pct']*100:.2f}%, "
                            f"换手率 {stock['turnover_rate']*100:.2f}%, "
                            f"成交额 {stock['turnover']/10000:.2f}亿\n"
                            f"    选股理由: {stock['selection_reason']}"
                        )
                
                data_summary.append("\n".join(industry_info))
            
            # 构建完整的分析文本
            data_text = "\n\n---\n\n".join(data_summary)
            
            # 更新分析提示
            messages = [
                {
                    "role": "system",
                    "content": """你是一位专业的行业分析师，请基于提供的详细数据进行深入分析。
                    在分析过程中，请务必在提到具体股票时同时给出股票代码，格式为：股票名称(股票代码)。
                    例如：中芯国际(688981)、比亚迪(002594)。
                    
                    分析时请特别关注：
                    1. 行业整体走势与个股表现的一致性
                    2. 龙头股的市场表现和引领作用
                    3. 潜力股的成长特征和投资机会
                    4. 换手率与成交量的配合
                    5. 行业轮动特征"""
                },
                {
                    "role": "user",
                    "content": f"""
                    以下是当前A股市场热门行业的详细数据：
                    
                    {data_text}
                    
                    请从以下几个方面进行分析，并在提到具体股票时，务必同时给出股票代码，格式为：股票名称(股票代码)
                    
                    1. 行业热度分析
                    - 评估行业上涨的广度和深度
                    - 分析行业内部分化情况
                    - 评估行业活跃度
                    
                    2. 龙头股分析
                    - 评估龙头股的市场地位和竞争优势（请列出具体龙头股及其代码）
                    - 分析龙头股的成交特征和资金关注度
                    - 预判龙头股的持续性和带动作用
                    
                    3. 潜力股分析
                    - 分析潜力股的成长特征（请列出具体潜力股及其代码）
                    - 评估潜力股的市场表现和资金关注度
                    - 给出潜力股的投资建议
                    
                    4. 投资策略建议
                    - 针对不同类型个股给出差异化策略（请明确指出股票名称和代码）
                    - 包括买入时机、持仓周期建议
                    - 结合个股特点给出具体建议
                    
                    5. 风险提示
                    - 评估行业估值风险
                    - 分析股价波动风险
                    - 提示可能的政策风险
                    
                    请结合具体数据给出详实的分析依据，并确保在提到具体股票时给出准确的股票代码。
                    """
                }
            ]
            
            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                stream=stream,
                temperature=0.7
            )
            
            if stream:
                return self._handle_stream_response(response)
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"AI分析失败: {e}")
            return "AI分析过程中发生错误"
            
    def _handle_stream_response(self, response):
        """处理流式响应"""
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            
    def get_industry_fund_flows(self, period: str = "今日") -> pd.DataFrame:
        """
        获取行业资金流向数据
        
        参数:
            period: 时间周期，可选 "今日"、"5日"、"10日"
            
        返回:
            包含资金流向数据的DataFrame
        """
        try:
            # 获取资金流向数据
            fund_flows = ak.stock_sector_fund_flow_rank(
                indicator=period,
                sector_type="行业资金流"
            )
            
            if fund_flows.empty:
                print("未获取到资金流向数据")
                return pd.DataFrame()
            
            # 打印实际的列名，帮助调试
            print("资金流向数据列名:", fund_flows.columns.tolist())
            
            # 重命名列（根据实际返回的列名调整）
            column_mapping = {
                '名称': 'industry_name',
                '今日涨跌幅': 'change_pct',
                '主力净流入-净额': 'main_inflow_amount',
                '主力净流入-净占比': 'main_inflow_pct',
                '超大单净流入-净额': 'super_large_inflow_amount',
                '超大单净流入-净占比': 'super_large_inflow_pct',
                '大单净流入-净额': 'large_inflow_amount',
                '大单净流入-净占比': 'large_inflow_pct'
            }
            
            # 检查列是否存在，只重命名存在的列
            available_columns = {k: v for k, v in column_mapping.items() 
                               if k in fund_flows.columns}
            fund_flows = fund_flows.rename(columns=available_columns)
            
            # 转换数值类型
            numeric_columns = [col for col in fund_flows.columns 
                               if '净额' in col or '净占比' in col or '涨跌幅' in col]
            for col in numeric_columns:
                fund_flows[col] = pd.to_numeric(
                    fund_flows[col].astype(str)
                    .str.replace(',', '')
                    .str.replace('%', '')
                    .replace('', '0'),
                    errors='coerce'
                )
                # 将百分比转换为小数
                if '%' in col or '涨跌幅' in col or '占比' in col:
                    fund_flows[col] = fund_flows[col] / 100
                
            return fund_flows
            
        except Exception as e:
            print(f"获取行业资金流向数据失败: {e}")
            return pd.DataFrame()

    def save_analysis_report(self, hot_industries: pd.DataFrame, 
                           ai_analysis: str, report_path: str) -> None:
        """
        保存分析报告
        
        参数:
            hot_industries: 热门行业数据
            ai_analysis: AI分析结果
            report_path: 报告保存路径
        """
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("# 行业分析报告\n\n")
                f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("## 热门行业数据\n\n")
                f.write(hot_industries.to_markdown())
                f.write("\n\n")
                
                f.write("## AI分析结果\n\n")
                f.write(ai_analysis)
                
            print(f"分析报告已保存至: {report_path}")
            
        except Exception as e:
            print(f"保存分析报告失败: {e}") 

    def get_industry_detail_data(self, industry_name: str) -> pd.DataFrame:
        """
        获取行业内个股详细数据
        """
        try:
            # 使用正确的接口获取行业成分股
            stocks_data = ak.stock_board_industry_cons_em(symbol=industry_name)
            
            if stocks_data.empty:
                print(f"未获取到{industry_name}行业的个股数据")
                return pd.DataFrame()
            
            # 获取这些股票的实时行情数据
            # 确保股票代码为字符串格式
            stocks_data['代码'] = stocks_data['代码'].astype(str)
            stock_codes = stocks_data['代码'].tolist()
            quotes = ak.stock_zh_a_spot_em()  # 获取所有A股实时行情
            
            # 确保行情数据中的股票代码也是字符串格式
            quotes['代码'] = quotes['代码'].astype(str)
            
            # 筛选出行业内股票的行情数据
            industry_quotes = quotes[quotes['代码'].isin(stock_codes)]
            
            # 重命名列
            column_mapping = {
                '代码': 'stock_code',
                '名称': 'stock_name',
                '最新价': 'price',
                '涨跌幅': 'change_pct',
                '成交额': 'turnover',
                '换手率': 'turnover_rate',
                '总市值': 'market_value',
                '流通市值': 'float_market_value'
            }
            
            # 选择并重命名列
            available_columns = {k: v for k, v in column_mapping.items() 
                               if k in industry_quotes.columns}
            result_df = industry_quotes[list(available_columns.keys())].rename(
                columns=available_columns
            )
            
            # 确保结果中的股票代码仍然是字符串格式
            result_df['stock_code'] = result_df['stock_code'].astype(str)
            
            # 数据类型转换
            numeric_columns = [col for col in result_df.columns 
                               if col not in ['stock_code', 'stock_name']]
            for col in numeric_columns:
                result_df[col] = pd.to_numeric(
                    result_df[col].astype(str)
                    .str.replace('%', '')
                    .str.replace(',', '')
                    .str.replace('亿', ''),
                    errors='coerce'
                )
                # 将百分比转换为小数
                if col in ['change_pct', 'turnover_rate']:
                    result_df[col] = result_df[col] / 100
                
            return result_df
            
        except Exception as e:
            print(f"获取行业个股数据失败: {e}")
            if 'stocks_data' in locals():
                print("实际返回的列名:", stocks_data.columns.tolist())
            return pd.DataFrame()
            
    def get_industry_fund_flow_trend(self, days: int = 5) -> pd.DataFrame:
        """
        获取行业资金流向趋势数据
        """
        try:
            # 获取行业资金流向趋势数据
            fund_flow = ak.stock_sector_fund_flow_rank(
                indicator=f"{days}日",
                sector_type="行业资金流"
            )
            
            if fund_flow.empty:
                print("未获取到行业资金流向趋势数据")
                return pd.DataFrame()
            
            # 打印实际的列名，帮助调试
            print("资金流向数据列名:", fund_flow.columns.tolist())
            
            # 重命名列并处理数据（根据实际返回的列名调整）
            column_mapping = {
                '名称': 'industry_name',
                '今日涨跌幅': 'change_pct',
                '今日主力净流入-净额': 'main_inflow_amount',
                '今日主力净流入-净占比': 'main_inflow_pct',
                '今日超大单净流入-净额': 'super_large_inflow_amount',
                '今日超大单净流入-净占比': 'super_large_inflow_pct'
            }
            
            # 检查列是否存在，只重命名存在的列
            available_columns = {k: v for k, v in column_mapping.items() 
                               if k in fund_flow.columns}
            
            if not available_columns:
                print("未找到匹配的列名")
                return pd.DataFrame()
            
            fund_flow = fund_flow.rename(columns=available_columns)
            
            # 转换数值类型
            for col in fund_flow.columns:
                if any(keyword in col for keyword in ['净额', '净占比', '涨跌幅']):
                    fund_flow[col] = pd.to_numeric(
                        fund_flow[col].astype(str)
                        .str.replace(',', '')
                        .str.replace('%', '')
                        .replace('', '0'),
                        errors='coerce'
                    )
                    # 将百分比转换为小数
                    if any(keyword in col for keyword in ['%', '涨跌幅', '占比']):
                        fund_flow[col] = fund_flow[col] / 100
                    
            return fund_flow
            
        except Exception as e:
            print(f"获取行业资金流向趋势数据失败: {e}")
            if 'fund_flow' in locals():
                print("实际列名:", fund_flow.columns.tolist())
            return pd.DataFrame()
            
    def analyze_industry_detail(self, industry_name: str) -> dict:
        """
        分析行业详细情况
        
        参数:
            industry_name: 行业名称
            
        返回:
            包含行业分析结果的字典
        """
        try:
            # 获取行业个股数据
            stocks_data = self.get_industry_detail_data(industry_name)
            
            if stocks_data.empty:
                return {}
                
            # 计算行业统计指标
            analysis = {
                'total_stocks': len(stocks_data),
                'up_stocks': len(stocks_data[stocks_data['change_pct'] > 0]),
                'down_stocks': len(stocks_data[stocks_data['change_pct'] < 0]),
                'avg_up_pct': stocks_data[stocks_data['change_pct'] > 0]['change_pct'].mean(),
                'avg_down_pct': stocks_data[stocks_data['change_pct'] < 0]['change_pct'].mean(),
                'avg_turnover_rate': stocks_data['turnover_rate'].mean(),
                'total_turnover': stocks_data['turnover'].sum(),
                'top_gainers': stocks_data.nlargest(3, 'change_pct')[
                    ['stock_name', 'change_pct', 'turnover_rate']
                ].to_dict('records')
            }
            
            return analysis
            
        except Exception as e:
            print(f"分析行业详情失败: {e}")
            return {}

    def get_industry_leaders(self, industry_name: str, top_n: int = 5) -> pd.DataFrame:
        """
        获取行业龙头股数据
        
        参数:
            industry_name: 行业名称
            top_n: 返回前N个龙头股
            
        返回:
            DataFrame包含龙头股数据
        """
        try:
            # 获取行业成分股数据
            stocks_data = self.get_industry_detail_data(industry_name)
            
            if stocks_data.empty:
                return pd.DataFrame()
            
            # 过滤掉688开头的科创板股票
            stocks_data = stocks_data[~stocks_data['stock_code'].astype(str).str.startswith('688')]
            
            # 按市值排序获取龙头股（如果有市值数据）
            if '市值' in stocks_data.columns:
                leaders = stocks_data.nlargest(top_n, '市值')
            else:
                # 如果没有市值数据，则按成交额排序
                leaders = stocks_data.nlargest(top_n, 'turnover')
            
            return leaders
            
        except Exception as e:
            print(f"获取{industry_name}行业龙头股失败: {e}")
            return pd.DataFrame()

    def get_industry_potential_stocks(self, industry_name: str, top_n: int = 5) -> pd.DataFrame:
        """
        获取行业潜力股数据
        
        参数:
            industry_name: 行业名称
            top_n: 返回前N个潜力股，默认5个
        
        返回:
            DataFrame包含潜力股数据
        """
        try:
            # 获取行业成分股数据
            stocks_data = self.get_industry_detail_data(industry_name)
            
            if stocks_data.empty:
                return pd.DataFrame()
            
            # 过滤掉688开头的科创板股票
            stocks_data = stocks_data[~stocks_data['stock_code'].astype(str).str.startswith('688')]
            
            # 计算综合得分
            # 1. 换手率得分（反映市场活跃度）
            stocks_data['turnover_score'] = stocks_data['turnover_rate'] / stocks_data['turnover_rate'].max()
            
            # 2. 涨幅得分（相对于行业平均涨幅）
            avg_change = stocks_data['change_pct'].mean()
            stocks_data['change_score'] = (stocks_data['change_pct'] - avg_change) / stocks_data['change_pct'].std()
            
            # 3. 成交额得分（反映资金关注度）
            stocks_data['volume_score'] = stocks_data['turnover'] / stocks_data['turnover'].max()
            
            # 4. 市值得分（中小市值更有潜力）
            if 'market_value' in stocks_data.columns:
                median_market_value = stocks_data['market_value'].median()
                stocks_data['market_score'] = 1 - (stocks_data['market_value'] / stocks_data['market_value'].max())
            else:
                stocks_data['market_score'] = 1.0
            
            # 计算综合得分 (调整权重)
            stocks_data['potential_score'] = (
                stocks_data['turnover_score'] * 0.3 +    # 换手率权重
                stocks_data['change_score'] * 0.2 +      # 涨幅权重
                stocks_data['volume_score'] * 0.3 +      # 成交额权重
                stocks_data['market_score'] * 0.2        # 市值权重
            )
            
            # 筛选条件：
            # 1. 剔除当日跌幅超过2%的股票
            # 2. 剔除换手率过低的股票（低于行业平均值的一半）
            # 3. 剔除成交额过低的股票
            avg_turnover_rate = stocks_data['turnover_rate'].mean()
            avg_turnover = stocks_data['turnover'].mean()
            
            potential_stocks = stocks_data[
                (stocks_data['change_pct'] > -0.02) &                     # 当日跌幅不超过2%
                (stocks_data['turnover_rate'] > avg_turnover_rate * 0.5) & # 换手率不低于平均值的一半
                (stocks_data['turnover'] > avg_turnover * 0.3)            # 成交额不低于平均值的30%
            ]
            
            # 按综合得分排序，选择得分最高的股票
            potential_stocks = potential_stocks.nlargest(top_n, 'potential_score')
            
            # 添加选股理由
            potential_stocks['selection_reason'] = potential_stocks.apply(
                lambda x: self._get_selection_reason(x, avg_turnover_rate, avg_turnover),
                axis=1
            )
            
            return potential_stocks
            
        except Exception as e:
            print(f"获取{industry_name}行业潜力股失败: {e}")
            return pd.DataFrame()

    def _get_selection_reason(self, stock: pd.Series, avg_turnover_rate: float, avg_turnover: float) -> str:
        """生成选股理由"""
        reasons = []
        
        # 分析换手率
        if stock['turnover_rate'] > avg_turnover_rate * 2:
            reasons.append("换手率显著高于行业平均")
        elif stock['turnover_rate'] > avg_turnover_rate:
            reasons.append("换手率高于行业平均")
        
        # 分析成交额
        if stock['turnover'] > avg_turnover * 2:
            reasons.append("成交活跃度高")
        elif stock['turnover'] > avg_turnover:
            reasons.append("成交量适中")
        
        # 分析涨幅
        if stock['change_pct'] > 0:
            reasons.append("走势强势")
        else:
            reasons.append("整理充分")
        
        # 分析市值
        if 'market_value' in stock.index:
            if stock['market_value'] < 100:
                reasons.append("小市值优势")
            elif stock['market_value'] < 300:
                reasons.append("市值适中")
        
        return "、".join(reasons)

    def extract_stocks_from_analysis(self, analysis_text: str) -> List[str]:
        """
        从AI分析文本中提取股票代码
        
        参数:
            analysis_text: AI分析结果文本
            
        返回:
            股票代码列表
        """
        import re
        
        # 匹配股票代码的模式（括号中的6位数字）
        pattern = r'\((\d{6})\)'
        
        # 提取所有匹配的股票代码
        stock_codes = re.findall(pattern, analysis_text)
        
        # 去重
        return list(set(stock_codes))

    def get_stocks_quotes(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取股票的最新行情数据
        
        参数:
            stock_codes: 股票代码列表
            
        返回:
            DataFrame包含股票行情数据
        """
        try:
            # 使用 akshare 获取实时行情数据
            quotes_list = []
            for code in stock_codes:
                try:
                    # 获取个股行情
                    quote = ak.stock_zh_a_spot_em()
                    # 筛选特定股票
                    stock_quote = quote[quote['代码'] == code]
                    if not stock_quote.empty:
                        quotes_list.append(stock_quote)
                except Exception as e:
                    print(f"获取股票{code}行情失败: {e}")
                    continue
            
            if not quotes_list:
                return pd.DataFrame()
            
            # 合并所有行情数据
            quotes_df = pd.concat(quotes_list, ignore_index=True)
            
            # 重命名列
            column_mapping = {
                '代码': 'stock_code',
                '名称': 'stock_name',
                '最新价': 'price',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'amplitude',
                '最高': 'high',
                '最低': 'low',
                '今开': 'open',
                '昨收': 'pre_close',
                '换手率': 'turnover_rate',
                '市盈率-动态': 'pe_ttm',
                '市净率': 'pb'
            }
            
            # 选择并重命名列
            available_columns = {k: v for k, v in column_mapping.items() 
                               if k in quotes_df.columns}
            quotes_df = quotes_df[list(available_columns.keys())].rename(
                columns=available_columns
            )
            
            # 数据类型转换
            numeric_columns = [col for col in quotes_df.columns 
                               if col not in ['stock_code', 'stock_name']]
            for col in numeric_columns:
                quotes_df[col] = pd.to_numeric(
                    quotes_df[col].astype(str)
                    .str.replace('%', '')
                    .str.replace(',', ''),
                    errors='coerce'
                )
                
            return quotes_df
            
        except Exception as e:
            print(f"获取股票行情数据失败: {e}")
            return pd.DataFrame()

    def save_stocks_quotes(self, quotes_df: pd.DataFrame, save_path: str) -> None:
        """
        保存股票行情数据到CSV文件
        
        参数:
            quotes_df: 股票行情DataFrame
            save_path: 保存路径
        """
        try:
            quotes_df.to_csv(save_path, index=False, encoding='utf-8-sig')
            print(f"股票行情数据已保存至: {save_path}")
        except Exception as e:
            print(f"保存股票行情数据失败: {e}")

def main():
    """主函数：运行行业分析"""
    import argparse
    import sys
    
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='行业分析工具')
    parser.add_argument('--stream', action='store_true', help='是否使用流式输出')
    parser.add_argument('--save_dir', type=str, default='results', help='结果保存目录')
    parser.add_argument('--rise_threshold', type=float, default=2.0, help='涨幅阈值（百分比）')
    parser.add_argument('--fund_threshold', type=float, default=5000, help='资金流入阈值（万元）')
    args = parser.parse_args()
    
    try:
        # 确保结果存目录存在
        os.makedirs(args.save_dir, exist_ok=True)
        
        # 初始化分析器
        analyzer = IndustryAnalyzer()
        
        # 生成输出文件名
        now = datetime.now()
        today = now.strftime('%Y%m%d')
        report_file = os.path.join(args.save_dir, f'industry_analysis_{today}.md')
        
        # 获取热门行业数据
        print("正在获取热门行业数据...")
        hot_industries = analyzer.get_hot_industries(
            rise_threshold=args.rise_threshold,
            fund_inflow_threshold=args.fund_threshold
        )
        
        if hot_industries.empty:
            print("未找到符合条件的热门行业")
            return
            
        print(f"\n找到 {len(hot_industries)} 个热门行业:")
        print("\n热门行业数据:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(hot_industries.to_string(index=False))
        
        # 获取行业资金流向数据
        print("\n正在获取行业资金流向数据...")
        fund_flows = analyzer.get_industry_fund_flows()
        
        # 合并热门行业和资金流向数据
        if not fund_flows.empty:
            merge_columns = ['industry_name']
            # 检查要合并的列是否存在
            if 'main_inflow_pct' in fund_flows.columns:
                merge_columns.append('main_inflow_pct')
            if 'super_large_inflow_amount' in fund_flows.columns:
                merge_columns.append('super_large_inflow_amount')
            
            hot_industries = pd.merge(
                hot_industries,
                fund_flows[merge_columns],
                on='industry_name',
                how='left'
            )
        
        # 使用AI分析数据
        print("\n正在进行AI分析...")
        if args.stream:
            print("\nAI分析结果:")
            analysis_result = []
            for chunk in analyzer.analyze_with_llm(hot_industries, stream=True):
                print(chunk, end='', flush=True)
                analysis_result.append(chunk)
            analysis_text = ''.join(analysis_result)
        else:
            analysis_text = analyzer.analyze_with_llm(hot_industries)
            print("\nAI分析结果:")
            print(analysis_text)
        
        # 保存分析报告
        print(f"\n正在保存分析报告到 {report_file}...")
        analyzer.save_analysis_report(
            hot_industries=hot_industries,
            ai_analysis=analysis_text,
            report_path=report_file
        )
        
        # 提取分析中提到的股票
        print("\n正在提取分析中提到的股票...")
        stock_codes = analyzer.extract_stocks_from_analysis(analysis_text)
        if stock_codes:
            print(f"找到 {len(stock_codes)} 只股票:")
            print(stock_codes)
            
            # 获取股票行情
            print("\n正在获取股票行情数据...")
            quotes_df = analyzer.get_stocks_quotes(stock_codes)
            
            if not quotes_df.empty:
                # 保存股票行情数据
                quotes_file = os.path.join(
                    args.save_dir, 
                    f'stocks_quotes_{today}.csv'
                )
                analyzer.save_stocks_quotes(quotes_df, quotes_file)
            else:
                print("未获取到股票行情数据")
        else:
            print("未从分析结果中提取到股票代码")
        
        print("\n分析完成！")
        
    except Exception as e:
        print(f"程序执行错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 