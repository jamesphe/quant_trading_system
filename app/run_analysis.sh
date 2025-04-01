#!/bin/bash

# 设置日志文件路径
LOG_DIR="/var/log/stock_analysis"
LOG_FILE="${LOG_DIR}/analysis_$(date +%Y-%m-%d_%H-%M-%S).log"

# 创建日志目录（如果不存在）
mkdir -p "$LOG_DIR"

# 将所有输出重定向到日志文件，同时保持标准输出
exec 1> >(tee -a "$LOG_FILE") 2>&1

# 函数：执行命令并打印输出
run_command() {
    local command="$1"
    local description="$2"
    
    echo -e "\n================================================================================"
    echo "开始执行: $description"
    echo "================================================================================"
    
    if eval "$command"; then
        echo -e "\n$description 执行完成"
    else
        echo -e "\n错误: $description 执行失败"
        echo "错误代码: $?"
        exit 1
    fi
}

# 主函数
main() {
    local date=$(date +%Y-%m-%d)
    
    # 1. 运行 optimize_all_stocks.py
    run_command "python optimize_all_stocks.py" "股票优化分析"
    
    # 2. 运行 add_stock_names.py
    run_command "python add_stock_names.py $date" "添加股票名称"
    
    # 3. 运行 get_latest_prices.py
    run_command "python get_latest_prices.py $date" "获取最新价格"
    
    # 4. 运行 industry_fund_flow_saver.py
    run_command "python industry_fund_flow_saver.py" "保存行业资金流向"
    
    # 5. 运行 ai_stock_analysis.py
    run_command "python ai_stock_analysis.py --mode csv --date $date --ai kimi" "Kimi AI分析股票"
    run_command "python ai_stock_analysis.py --mode csv --date $date --ai openai" "OpenAI AI分析股票"
    
    echo -e "\n所有任务执行完成!"
}

# 添加脚本开始的时间戳
echo "================================================================================"
echo "脚本开始执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"

# 执行主函数并计时
start_time=$(date +%s)
main
end_time=$(date +%s)
duration=$((end_time - start_time))
echo -e "\n总执行时间: $duration 秒"

# 添加脚本结束的时间戳
echo "================================================================================"
echo "脚本结束执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "日志文件保存在: $LOG_FILE"
echo "================================================================================" 