import subprocess
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime, timedelta
import argparse
import os

# 定义持仓股票清单
portfolio = {
    '000921': '海信家电',
    '002229': '鸿博股份',
    '600667': '太极实业',
    '001286': '陕西能源',
    '002779': '中坚科技',
    '300762': '上海瀚讯',
    '002747': '埃斯顿',
    '600789': '鲁抗医药',
    '002053': '云南能投',
    '601519': '大智慧',
    '300363': '博腾股份',
    '300077': '国民技术',
    '002786': '银宝山新',
    '600580': '卧龙电驱',
    'ARKK': 'ARK创新',
    'VGT': '信息科技',
    'TSLA': '特斯拉',
    '601398': '工商银行',
    '600678': '四川金顶',
    '300315': '掌趣科技'
}  # 可以根据实际情况修改

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

def optimize_and_backtest(symbol):
    # 读取优化结果
    opt_file = f"results/{symbol}_optimization_results.csv"
    if not os.path.exists(opt_file):
        # 运行优化器
        optimize_cmd = f"python optimizer.py --symbol {symbol}"
        subprocess.run(optimize_cmd, shell=True, check=True)
        
    file_mtime = datetime.fromtimestamp(os.path.getmtime(opt_file))
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if file_mtime < today:
        print(f"股票 {symbol} 的优化结果已过期,需要重新生成")
        # 运行优化器
        optimize_cmd = f"python optimizer.py --symbol {symbol}"
        subprocess.run(optimize_cmd, shell=True, check=True)
        
    opt_results = pd.read_csv(opt_file)
    if opt_results.empty:
        print(f"股票 {symbol} 的优化结果为空")
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
    for line in output_lines:
        if line.startswith((datetime.now() - timedelta(days=0)).strftime('%Y-%m-%d')):
            trading_advice.append(line.strip())
        elif "最新交易日交易建议:" in line:
            capture_advice = True
        elif capture_advice and line.strip() == "":
            break
        elif capture_advice:
            trading_advice.append(line.strip())        

    return symbol, '\n'.join(trading_advice) + '\n' + formatted_best_params

def send_to_wechat(content):
    # 替换为您的Server酱 SCKEY
    sckey = "SCT257266Tdc4MxFyOWnZ9PINv52Rh2zOh"
    url = f"https://sctapi.ftqq.com/{sckey}.send"  # 更新为新的API域名
    
    # 修改content，在每行后添加两个换行符
    formatted_content = content.replace('\n', '\n\n')
    
    payload = {
        "title": "交易建议汇总",
        "desp": formatted_content
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("成功发送到微信")
    else:
        print("发送失败")

def main():
    args = parse_args()
    results = []
    
    # 根据模式选择股票清单
    if args.mode == 'portfolio':
        stocks_to_analyze = portfolio
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
    with ThreadPoolExecutor(max_workers=len(stocks_to_analyze)) as executor:
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
    for symbol, advice in results:
        print(f"\n{stocks_to_analyze[symbol]}（{symbol}）")
        print(advice)
        wechat_content += f"## {stocks_to_analyze[symbol]}（{symbol}）\n\n{advice}\n\n"
    
    # 发送到微信
    if args.mode == 'portfolio' and args.send_wechat:
        send_to_wechat(wechat_content)

if __name__ == "__main__":
    main()
