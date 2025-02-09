import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI
from config import Config


class MainForceAnalyzer:
    def __init__(self, stock_code: str, openai_api_key: str = None):
        """
        初始化主力资金分析器
        
        参数:
            stock_code: 股票代码
            openai_api_key: OpenAI API密钥（可选）
        """
        self.stock_code = stock_code
        
        # 使用 Config 类获取 API key
        config = Config()
        self.api_key = openai_api_key or config.get_api_key('openai')
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.chatanywhere.tech/v1"
        )
        
    def get_fund_flow(self, days: int = 30) -> pd.DataFrame:
        """获取资金流向数据"""
        try:
            # 确定市场类型
            market = "sh" if self.stock_code.startswith('6') else "sz" if self.stock_code.startswith(('0', '3')) else "bj"
            
            # 使用正确的 akshare 接口和参数
            fund_flow = ak.stock_individual_fund_flow(
                stock=self.stock_code,
                market=market
            )
            
            # 检查并打印列名，帮助调试
            print("资金流向数据列名:", fund_flow.columns.tolist())
            
            # 转换日期列并排序
            fund_flow['日期'] = pd.to_datetime(fund_flow['日期'])
            fund_flow = fund_flow.sort_values(by="日期").tail(days)
            
            # 计算累计净流入
            fund_flow['累计主力净流入'] = fund_flow['主力净流入-净额'].cumsum()
            fund_flow['累计超大单净流入'] = fund_flow['超大单净流入-净额'].cumsum()
            
            # 重命名列以保持一致性
            fund_flow = fund_flow.rename(columns={
                '主力净流入-净额': '主力净流入',
                '主力净流入-净占比': '主力净占比',
                '超大单净流入-净额': '超大单净流入',
                '超大单净流入-净占比': '超大单净占比',
                '大单净流入-净额': '大单净流入',
                '大单净流入-净占比': '大单净占比',
                '中单净流入-净额': '中单净流入',
                '中单净流入-净占比': '中单净占比',
                '小单净流入-净额': '小单净流入',
                '小单净流入-净占比': '小单净占比'
            })
            
            return fund_flow
        except Exception as e:
            print(f"获取资金流向数据失败: {e}")
            print("完整错误信息:", fund_flow.columns if 'fund_flow' in locals() else "数据未获取")
            return pd.DataFrame()
    
    def get_lhb_data(self, start_date: str = None) -> dict:
        """获取龙虎榜数据"""
        try:
            # 获取最近30天的龙虎榜数据
            lhb_data = ak.stock_lhb_ggtj_sina(symbol="30")
            
            # 检查并打印列名，帮助调试
            print("龙虎榜数据列名:", lhb_data.columns.tolist())
            
            # 过滤出指定股票的数据
            lhb_filtered = lhb_data[lhb_data['股票代码'] == self.stock_code]
            
            # 如果数据为空，尝试其他时间范围
            if lhb_filtered.empty:
                for period in ["60", "10", "5"]:
                    try:
                        lhb_data = ak.stock_lhb_ggtj_sina(symbol=period)
                        lhb_filtered = lhb_data[lhb_data['股票代码'] == self.stock_code]
                        if not lhb_filtered.empty:
                            break
                    except Exception as e:
                        print(f"获取{period}天龙虎榜数据失败: {e}")
                        continue
            
            # 构建返回数据
            result = {
                'raw_data': lhb_filtered,
                'summary': {
                    '上榜次数': 0,
                    '累计净额': 0,
                    '买入席位数': 0,
                    '卖出席位数': 0,
                    '买入卖出比': 0,
                    '净买入比例': 0
                }
            }
            
            # 只有在有数据时才更新统计信息
            if not lhb_filtered.empty:
                try:
                    result['summary'].update({
                        '上榜次数': int(lhb_filtered['上榜次数'].iloc[0]),
                        '累计净额': float(lhb_filtered['净额'].iloc[0]),
                        '买入席位数': int(lhb_filtered['买入席位数'].iloc[0]),
                        '卖出席位数': int(lhb_filtered['卖出席位数'].iloc[0])
                    })
                    
                    # 计算比率
                    if float(lhb_filtered['累积卖出额'].iloc[0]) != 0:
                        result['summary']['买入卖出比'] = float(lhb_filtered['累积购买额'].iloc[0]) / float(lhb_filtered['累积卖出额'].iloc[0])
                    
                    if float(lhb_filtered['累积购买额'].iloc[0]) != 0:
                        result['summary']['净买入比例'] = float(lhb_filtered['净额'].iloc[0]) / float(lhb_filtered['累积购买额'].iloc[0]) * 100
                except Exception as e:
                    print(f"计算统计数据时出错: {e}")
            
            return result
            
        except Exception as e:
            print(f"获取龙虎榜数据失败: {e}")
            print("完整错误信息:", lhb_data.columns if 'lhb_data' in locals() else "数据未获取")
            return {
                'raw_data': pd.DataFrame(),
                'summary': {
                    '上榜次数': 0,
                    '累计净额': 0,
                    '买入席位数': 0,
                    '卖出席位数': 0,
                    '买入卖出比': 0,
                    '净买入比例': 0
                }
            }
    
    def analyze_volume_price(self) -> pd.DataFrame:
        """分析量价关系"""
        try:
            # 使用新的日线数据接口
            stock_data = ak.stock_zh_a_hist(
                symbol=self.stock_code,
                start_date=(datetime.now() - timedelta(days=60)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d')
            )
            
            # 检查并打印列名，帮助调试
            print("股票数据列名:", stock_data.columns.tolist())
            
            # 统一日期列名
            stock_data['trade_date'] = pd.to_datetime(stock_data['日期'])
            stock_data.set_index('trade_date', inplace=True)
            
            # 使用正确的成交量列名
            volume_col = '成交量'
            stock_data['volume_ma5'] = stock_data[volume_col].rolling(5).mean()
            
            # 判断是否放量或缩量
            is_volume_up = stock_data[volume_col] > stock_data['volume_ma5'] * 1.5
            stock_data['is_volume_up'] = is_volume_up
            
            return stock_data.tail(30)  # 返回最近30天数据
        except Exception as e:
            print(f"分析量价关系失败: {e}")
            print("完整错误信息:", stock_data.columns if 'stock_data' in locals() else "数据未获取")
            return pd.DataFrame()
    
    def get_margin_data(self) -> pd.DataFrame:
        """获取融资融券数据"""
        try:
            margin_data = ak.stock_margin_sse()
            # 添加融资融券分析逻辑
            return margin_data
        except Exception as e:
            print(f"获取融资融券数据失败: {e}")
            return pd.DataFrame()
    
    def save_analysis_to_md(self, analysis_result: dict) -> None:
        """将分析结果保存为 Markdown 文件"""
        try:
            # 创建 AIResult 目录（如果不存在）
            import os
            output_dir = "AIResult"
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名：股票代码_日期.md
            current_date = datetime.now().strftime('%Y%m%d')
            filename = f"{output_dir}/mfa_{self.stock_code}_{current_date}.md"
            
            # 构建 Markdown 内容
            md_content = f"""# {self.stock_code} 主力资金分析报告 ({current_date})

## 主要指标
- 主力资金趋势: {analysis_result['main_force_trend']}
- 龙虎榜特征: {analysis_result['lhb_summary']}
- 量价信号: {analysis_result['volume_price_signal']}
- 风险等级: {analysis_result['risk_level']}

## AI深度分析
{analysis_result['ai_analysis']}

---
*分析生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            # 写入文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            print(f"分析结果已保存到: {filename}")
            
        except Exception as e:
            print(f"保存分析结果失败: {e}")
    
    def comprehensive_analysis(self) -> dict:
        """综合分析"""
        fund_flow = self.get_fund_flow()
        lhb_data = self.get_lhb_data()
        volume_price = self.analyze_volume_price()
        
        # 准备分析数据
        analysis_data = {
            'main_force': self._analyze_main_force_trend(fund_flow),
            'lhb': self._analyze_lhb(lhb_data),
            'volume': self._analyze_volume_price_signal(volume_price),
            'risk': self._calculate_risk_level(fund_flow, volume_price)
        }
        
        # 使用AI进行深度分析
        ai_analysis = self._analyze_with_llm(analysis_data)
        
        analysis_result = {
            'main_force_trend': analysis_data['main_force'],
            'lhb_summary': analysis_data['lhb'],
            'volume_price_signal': analysis_data['volume'],
            'risk_level': analysis_data['risk'],
            'ai_analysis': ai_analysis
        }
        
        # 保存分析结果
        self.save_analysis_to_md(analysis_result)
        
        return analysis_result
    
    def _analyze_main_force_trend(self, fund_flow: pd.DataFrame) -> str:
        """分析主力资金趋势"""
        if fund_flow.empty:
            return "数据不足"
            
        recent_flow = fund_flow.tail(5)
        net_inflow = recent_flow['主力净流入'].sum()
        
        if net_inflow > 0:
            return "主力净流入" if net_inflow > 10000000 else "小幅净流入"
        else:
            return "主力净流出" if net_inflow < -10000000 else "小幅净流出"
    
    def _analyze_lhb(self, lhb_data: dict) -> str:
        """分析龙虎榜特征"""
        if lhb_data['raw_data'].empty:
            return "近期无龙虎榜数据"
            
        # 使用摘要数据进行分析
        summary = lhb_data['summary']
        
        # 构建分析结果
        analysis = []
        
        # 分析上榜次数
        if summary['上榜次数'] > 0:
            analysis.append(f"上榜{summary['上榜次数']}次")
        
        # 分析资金流向
        if summary['累计净额'] != 0:
            direction = "净流入" if summary['累计净额'] > 0 else "净流出"
            amount = abs(summary['累计净额'])
            analysis.append(f"资金{direction}{amount:.2f}万")
        
        # 分析席位情况
        if summary['买入席位数'] > 0 or summary['卖出席位数'] > 0:
            analysis.append(f"买入席位{summary['买入席位数']}个")
            analysis.append(f"卖出席位{summary['卖出席位数']}个")
        
        # 分析买卖比例
        if summary['买入卖出比'] > 0:
            analysis.append(f"买卖比{summary['买入卖出比']:.2f}")
        
        return "，".join(analysis) if analysis else "数据不足"
    
    def _analyze_volume_price_signal(self, volume_price: pd.DataFrame) -> str:
        """分析量价信号"""
        if volume_price.empty:
            return "数据不足"
            
        recent_data = volume_price.tail(5)
        volume_signal = "放量" if recent_data['is_volume_up'].any() else "缩量"
        
        return volume_signal
    
    def _calculate_risk_level(
        self, 
        fund_flow: pd.DataFrame, 
        volume_price: pd.DataFrame
    ) -> str:
        """计算风险等级"""
        risk_score = 0
        
        # 根据各种指标计算风险分数
        if not fund_flow.empty:
            if fund_flow['主力净流入'].tail(5).sum() < 0:
                risk_score += 2
                
        if not volume_price.empty:
            if volume_price['is_volume_up'].tail(3).any():
                risk_score += 1
                
        risk_levels = {
            0: "低风险",
            1: "中低风险",
            2: "中风险",
            3: "中高风险",
            4: "高风险"
        }
        
        return risk_levels.get(risk_score, "风险等级未知")
    
    def _analyze_with_llm(self, analysis_data: dict) -> str:
        """使用大语言模型进行深度分析"""
        try:
            # 构建分析提示
            prompt = f"""
            请基于以下数据对股票{self.stock_code}的主力资金动向进行深度分析:
            
            1. 主力资金趋势: {analysis_data['main_force']}
            2. 龙虎榜特征: {analysis_data['lhb']}
            3. 量价信号: {analysis_data['volume']}
            4. 风险等级: {analysis_data['risk']}
            
            请从以下几个方面进行分析:
            1. 主力资金动向判断
            2. 机构参与度评估
            3. 操作风险提示
            4. 建议关注要点
            
            请给出详细的分析和具体建议。
            """
            
            # 打印实际的提示词
            print("\n=== 实际提示词 ===")
            print(prompt)
            print("==================\n")
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一位专业的股票分析师"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"AI分析失败: {e}")
            return "AI分析过程中发生错误"


def main():
    """主函数：运行主力资金分析"""
    import argparse
    
    parser = argparse.ArgumentParser(description='主力资金分析工具')
    parser.add_argument('--stock_code', type=str, required=True, help='股票代码')
    parser.add_argument('--days', type=int, default=30, help='分析天数')
    args = parser.parse_args()
    
    try:
        analyzer = MainForceAnalyzer(args.stock_code)
        result = analyzer.comprehensive_analysis()
        
        print("\n=== 主力资金分析结果 ===")
        print(f"主力资金趋势: {result['main_force_trend']}")
        print(f"龙虎榜特征: {result['lhb_summary']}")
        print(f"量价信号: {result['volume_price_signal']}")
        print(f"风险等级: {result['risk_level']}")
        print("\nAI深度分析:")
        print(result['ai_analysis'])
        
    except Exception as e:
        print(f"分析过程发生错误: {e}")


if __name__ == "__main__":
    main() 