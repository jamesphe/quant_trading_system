#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票新闻分析工具

用于获取和分析指定股票最近n天的新闻信息。
使用方法：
    python stock_news_analyzer.py 股票代码 [-d 天数]
示例：
    python stock_news_analyzer.py 300059 -d 3
"""

import argparse
from datetime import datetime, timedelta
from data_fetch import get_stock_news, get_stock_name
import pandas as pd


def get_recent_stock_news(symbol: str, days: int = 1) -> pd.DataFrame:
    """
    获取指定股票最近n天的新闻

    参数:
    - symbol: str, 股票代码
    - days: int, 要获取的天数，默认为1天

    返回:
    - DataFrame: 包含过滤后的新闻数据
    """
    # 获取所有新闻
    news_df = get_stock_news(symbol)
    
    if news_df.empty:
        return pd.DataFrame()
    
    # 计算截止时间
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # 过滤最近n天的新闻
    recent_news = news_df[
        (news_df['publish_time'] >= start_time) & 
        (news_df['publish_time'] <= end_time)
    ]
    
    return recent_news


def print_news_info(news_df: pd.DataFrame, stock_code: str, days: int) -> None:
    """
    打印新闻信息

    参数:
    - news_df: DataFrame, 新闻数据
    - stock_code: str, 股票代码
    - days: int, 查询的天数
    """
    stock_name = get_stock_name(stock_code)
    
    if news_df.empty:
        print(f"\n未找到股票 {stock_code}({stock_name}) 最近 {days} 天的新闻")
        return
    
    print(f"\n{stock_code}({stock_name}) 最近 {days} 天找到 {len(news_df)} 条新闻：\n")
    
    for _, row in news_df.iterrows():
        print(f"发布时间：{row['publish_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"来源：{row['source']}")
        print(f"标题：{row['title']}")
        print(f"链接：{row['url']}")
        print("-" * 80)


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description='获取并分析指定股票的最近n天新闻',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('symbol', help='股票代码，例如：300059')
    parser.add_argument(
        '-d', 
        '--days', 
        type=int, 
        default=1, 
        help='要获取的天数，默认为1天'
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 获取并打印新闻数据
    news_df = get_recent_stock_news(args.symbol, args.days)
    print_news_info(news_df, args.symbol, args.days)


if __name__ == "__main__":
    main()
