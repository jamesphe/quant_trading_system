import subprocess
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime, timedelta
import argparse
import os
from typing import Dict, Tuple, Optional

# 新增目标股票清单
target_stocks = {
    '603628': '清源股份',
    '601519': '大智慧',
    '300524': '新晨科技',
    '300459': '汤姆猫',
    '300398': '飞凯材料'
}

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='股票分析工具')
    parser.add_argument('--mode', type=str, choices=['portfolio', 'target'],
                      default='portfolio', help='分析模式：portfolio(持仓分析)或target(目标股分析)')
    parser.add_argument('--date', type=str, 
                      default=datetime.now().strftime('%Y%m%d'),
                      help='分析日期，格式为YYYYMMDD')
    parser.add_argument('--send-wechat', action='store_true',
                      help='是否发送结果到微信')
    return parser.parse_args()

def optimize_and_backtest(symbol: str, strategy_name: str = 'ChandelierZlSmaStrategy') -> Tuple[str, str]:
    """
    优化并回测单个股票
    
    Args:
        symbol: 股票代码
        strategy_name: 策略名称
        
    Returns:
        Tuple[str, str]: (股票代码, 分析结果文本)
    """
    # 读取优化结果
    opt_file = f"results/{symbol}_{strategy_name}_optimization_results.csv"
    
    # 检查是否需要重新优化
    need_optimize = True
    if os.path.exists(opt_file):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(opt_file))
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        need_optimize = file_mtime < today
    
    if need_optimize:
        print(f"股票 {symbol} 需要重新优化")
        optimize_cmd = f"python optimizer.py --symbol {symbol} --strategy {strategy_name}"
        subprocess.run(optimize_cmd, shell=True, check=True)
    
    # 读取优化结果
    try:
        opt_results = pd.read_csv(opt_file)
        if opt_results.empty:
            return symbol, "无法获取优化结果"

        best_params = opt_results.iloc[0]
        
        # 格式化最佳参数
        formatted_best_params = (
            f"period: {int(best_params['period'])}, "
            f"mult: {best_params['mult']:.2f}, "
            f"investment_fraction: {best_params['investment_fraction']:.2f}, "
            f"max_pyramiding: {int(best_params['max_pyramiding'])}"
        )

        # 构建回测命令
        backtest_cmd = (
            f"python chandelier_zlsma_test.py {symbol} "
            f"-p {int(best_params['period'])} "
            f"-m {best_params['mult']:.2f} "
            f"-i {best_params['investment_fraction']:.2f} "
            f"-y {int(best_params['max_pyramiding'])}"
        )

        # 运行回测
        result = subprocess.run(backtest_cmd, shell=True, capture_output=True, text=True)
        
        # 提取最新交易日交易建议
        output_lines = result.stdout.split('\n')
        trading_advice = []
        capture_advice = False
        
        today = datetime.now().strftime('%Y-%m-%d')
        for line in output_lines:
            if line.startswith(today):
                trading_advice.append(line.strip())
            elif "最新交易日交易建议:" in line:
                capture_advice = True
            elif capture_advice and line.strip() == "":
                break
            elif capture_advice:
                trading_advice.append(line.strip())
        
        # 添加信号强度信息
        signal_strength = float(best_params.get('signal_strength', 0))
        #signal_strength_text = get_signal_strength_description(signal_strength)
        trading_advice.append(f"\n信号强度: {signal_strength:.2f}")
        
        return symbol, '\n'.join(trading_advice) + '\n' + formatted_best_params
        
    except Exception as e:
        print(f"处理股票 {symbol} 时发生错误: {str(e)}")
        return symbol, f"分析过程出错: {str(e)}"

def get_signal_strength_description(strength: float) -> str:
    """
    根据信号强度返回描述文本
    
    Args:
        strength: 信号强度值(0-1之间)
    
    Returns:
        str: 信号强度描述
    """
    if strength >= 0.8:
        return "强烈"
    elif strength >= 0.6:
        return "较强"
    elif strength >= 0.4:
        return "中等"
    elif strength >= 0.2:
        return "较弱"
    else:
        return "微弱"

def send_to_wechat(content: str) -> None:
    """发送内容到微信"""
    sckey = "SCT257266Tdc4MxFyOWnZ9PINv52Rh2zOh"
    url = f"https://sctapi.ftqq.com/{sckey}.send"
    
    # 修改content，在每行后添加两个换行符
    formatted_content = content.replace('\n', '\n\n')
    
    payload = {
        "title": "交易建议汇总",
        "desp": formatted_content
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("成功发送到微信")
        else:
            print(f"发送失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"发送失败: {str(e)}")

def load_portfolio() -> Dict[str, str]:
    """从CSV文件加载持仓股票信息"""
    portfolio_file = os.path.join(os.path.dirname(__file__), 'config/portfolio_stocks.csv')
    try:
        df = pd.read_csv(portfolio_file)
        return dict(zip(df['股票代码'].astype(str), df['股票名称']))
    except Exception as e:
        print(f"加载持仓股票文件时出错: {str(e)}")
        return {}

def main():
    args = parse_args()
    results = []
    
    # 根据模式选择股票清单
    if args.mode == 'portfolio':
        stocks_to_analyze = load_portfolio()
        if not stocks_to_analyze:
            print("无法加载持仓股票列表")
            return
    else:
        try:
            # 转换日期格式：从 YYYY-MM-DD 到 YYYYMMDD
            date = args.date.replace('-', '')
            module_path = f'stock_pool.stock_list_{date}'
            stock_list_module = __import__(module_path, fromlist=['STOCK_LIST'])
            # 直接使用导入的 STOCK_LIST，它已经是正确的格式（包含股票代码和名称）
            stocks_to_analyze = stock_list_module.STOCK_LIST
        except ImportError:
            print(f"无法找到日期 {args.date} 的股票列表文件")
            return
        except Exception as e:
            print(f"加载股票列表时出错: {str(e)}")
            return
    mode_name = "持仓" if args.mode == 'portfolio' else "目标股票"
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=min(len(stocks_to_analyze), 5)) as executor:
        future_to_symbol = {executor.submit(optimize_and_backtest, symbol): symbol 
                          for symbol in stocks_to_analyze}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f'{stocks_to_analyze[symbol]}（{symbol}）生成了一个异常: {exc}')

    # 打印结果并准备发送内容
    print(f"\n=== {mode_name}分析汇总 ===")
    wechat_content = f"# {mode_name}分析汇总\n\n"
    
    # 按信号强度排序结果
    sorted_results = sort_results_by_signal_strength(results, stocks_to_analyze)
    
    for symbol, advice in sorted_results:
        print(f"\n{stocks_to_analyze[symbol]}（{symbol}）")
        print(advice)
        wechat_content += f"## {stocks_to_analyze[symbol]}（{symbol}）\n\n{advice}\n\n"
    
    # 发送到微信
    if args.mode == 'portfolio' and args.send_wechat:
        send_to_wechat(wechat_content)

def sort_results_by_signal_strength(
    results: list,
    stocks_map: Dict[str, str]
) -> list:
    """
    根据信号强度对结果进行排序
    
    Args:
        results: 分析结果列表
        stocks_map: 股票代码到名称的映射
        
    Returns:
        list: 排序后的结果列表
    """
    def extract_signal_strength(result_text: str) -> float:
        try:
            # 查找信号强度行
            for line in result_text.split('\n'):
                if '信号强度:' in line:
                    # 提取括号中的数值
                    strength = float(line.split('(')[-1].split(')')[0])
                    return strength
        except:
            pass
        return 0.0
    
    # 为每个结果添加信号强度并排序
    results_with_strength = [
        (symbol, advice, extract_signal_strength(advice))
        for symbol, advice in results
    ]
    
    # 按信号强度降序排序
    sorted_results = sorted(
        results_with_strength,
        key=lambda x: x[2],
        reverse=True
    )
    
    # 返回排序后的结果（不包含信号强度）
    return [(r[0], r[1]) for r in sorted_results]

if __name__ == "__main__":
    main()
