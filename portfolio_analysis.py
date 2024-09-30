import subprocess
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# 定义持仓股票清单
portfolio = ['300077', '300383', '300687', '603206']  # 可以根据实际情况修改

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
                print(f'{symbol} 生成了一个异常: {exc}')

    # 打印结果
    print("\n=== 交易建议汇总 ===")
    for symbol, advice in results:
        print(f"\n股票代码: {symbol}")
        print(advice)

if __name__ == "__main__":
    main()