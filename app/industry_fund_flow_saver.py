import pandas as pd
from data_fetch import get_industry_fund_flow_rank
from datetime import datetime

def save_industry_fund_flow(sector_type="行业资金流", output_file=None):
    """
    获取行业资金流向排名数据并保存到本地CSV文件

    参数:
    - sector_type: str, 可选 "行业资金流", "概念资金流", "地域资金流"
    - output_file: str, 输出CSV文件的名称（如果为None，则自动生成）

    返回:
    - 保存的文件路径
    """
    try:
        print(f"开始获取 {sector_type} 的行业资金流向排名数据...")
        
        # 获取行业资金流向排名数据
        industry_flow_data = get_industry_fund_flow_rank(sector_type)
        
        if industry_flow_data.empty:
            print("未获取到数据，无法保存。")
            return None
        
        # 如果未指定输出文件名，则自动生成
        if output_file is None:
            current_time = datetime.now().strftime("%Y%m%d")
            output_file = f"{sector_type}_{current_time}.csv"
        
        # 保存数据到CSV文件
        industry_flow_data.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已成功保存到文件: {output_file}")
        
        return output_file
    
    except Exception as e:
        print(f"保存 {sector_type} 的行业资金流向排名数据时发生错误: {e}")
        return None

if __name__ == "__main__":
    # 示例用法
    sector_types = ["行业资金流","概念资金流"]
    
    for sector_type in sector_types:
        saved_file = save_industry_fund_flow(sector_type)
        if saved_file:
            print(f"{sector_type} 数据已保存到: {saved_file}")
        else:
            print(f"保存 {sector_type} 数据失败")
        print("---")
