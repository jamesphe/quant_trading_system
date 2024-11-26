import subprocess
from datetime import datetime
import time
import sys
import os

def run_command(command, description):
    """
    执行命令并打印输出
    """
    print(f"\n{'='*80}")
    print(f"开始执行: {description}")
    print(f"{'='*80}\n")
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # 实时打印输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
        # 获取返回码
        return_code = process.poll()
        
        if return_code != 0:
            print(f"\n错误: {description} 执行失败")
            _, stderr = process.communicate()
            print(f"错误信息: {stderr}")
            sys.exit(1)
            
        print(f"\n{description} 执行完成")
        return True
        
    except Exception as e:
        print(f"\n执行 {description} 时发生错误: {str(e)}")
        sys.exit(1)

def main():
    date = datetime.now().strftime('%Y-%m-%d')
    
    # 1. 运行 optimize_all_stocks.py
    run_command(
        ["python", "app/optimize_all_stocks.py"],
        "股票优化分析"
    )
    
    # 2. 运行 add_stock_names.py
    run_command(
        ["python", "app/add_stock_names.py", date],
        "添加股票名称"
    )
    
    # 3. 运行 get_latest_prices.py
    run_command(
        ["python", "app/get_latest_prices.py", date],
        "获取最新价格"
    )
    
    # 4. 运行 industry_fund_flow_saver.py
    run_command(
        ["python", "app/industry_fund_flow_saver.py"],
        "保存行业资金流向"
    )
    
    # 5. 运行 ai_stock_analysis.py
    run_command(
        ["python", "app/ai_stock_analysis.py", "--mode", "csv", "--date", date, "--ai", "kimi"],
        "AI分析股票"
    )
    
    print("\n所有任务执行完成!")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    duration = end_time - start_time
    print(f"\n总执行时间: {duration:.2f} 秒") 