import subprocess
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests  # 新增导入

# 定义持仓股票清单
portfolio = {
    '300077': '聚光科技',
    '300383': '光环新网',
    '300687': '赛意信息',
    '603206': '嘉环科技',
    '600141': '兴发集团'
}  # 可以根据实际情况修改

def optimize_and_backtest(symbol):
    # 运行优化器
    optimize_cmd = f"python optimizer.py {symbol}"
    subprocess.run(optimize_cmd, shell=True, check=True)

    # 读取优化结果
    opt_results = pd.read_csv(f"{symbol}_optimization_results.csv")
    if opt_results.empty:
        print(f"股票 {symbol} 的优化结果为空")
        return symbol, "无法获取优化结果"

    best_params = opt_results.iloc[0]

    # 构建回测命令
    backtest_cmd = (
        f"python chandelier_zlsma_test.py {symbol} "
        f"-l {int(best_params['length'])} "
        f"-m {best_params['mult']:.2f} "
        f"-z {int(best_params['zlsma_length'])} "
        f"-i {best_params['investment_fraction']:.2f} "
        f"-p {int(best_params['max_pyramiding'])}"
    )

    # 运行回测
    result = subprocess.run(backtest_cmd, shell=True, capture_output=True, text=True)
    
    # 提取最新交易日交易建议
    output_lines = result.stdout.split('\n')
    trading_advice = []
    capture_advice = False
    for line in output_lines:
        if "最新交易日交易建议:" in line:
            capture_advice = True
        elif capture_advice and line.strip() == "":
            break
        elif capture_advice:
            trading_advice.append(line.strip())
    
    return symbol, '\n'.join(trading_advice)

def send_to_wechat(content):
    # 替换为您的Server酱 SCKEY
    sckey = "SCT257266Tdc4MxFyOWnZ9PINv52Rh2zOh"
    url = f"https://sctapi.ftqq.com/{sckey}.send"  # 更新为新的API域名
    payload = {
        "title": "交易建议汇总",
        "desp": content
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("成功发送到微信")
    else:
        print("发送失败")

def main():
    results = []
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=len(portfolio)) as executor:
        future_to_symbol = {executor.submit(optimize_and_backtest, symbol): symbol for symbol in portfolio}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f'{portfolio[symbol]}（{symbol}）生成了一个异常: {exc}')

    # 打印结果并准备发送内容
    print("\n=== 交易建议汇总 ===")
    wechat_content = "# 交易建议汇总\n\n"
    for symbol, advice in results:
        print(f"\n{portfolio[symbol]}（{symbol}）")
        print(advice)
        wechat_content += f"## {portfolio[symbol]}（{symbol}）\n{advice}\n\n"
    
    # 发送到微信
    send_to_wechat(wechat_content)

if __name__ == "__main__":
    main()