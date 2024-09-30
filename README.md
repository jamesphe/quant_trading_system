# 蜡烛图与ZLSMA策略交易系统

## 项目概述

这个项目是一个基于蜡烛图(Chandelier)和零滞后简单移动平均线(ZLSMA)的交易策略系统。它包括策略实现、数据获取、回测、优化功能以及投资组合分析。

## 文件结构

- `strategies/chandelier_zlsma_strategy.py`: 蜡烛图与ZLSMA策略的核心实现
- `test_chandelier_zlsma_strategy.py`: 策略的单元测试
- `data_fetch.py`: 用于获取交易数据的模块
- `chandelier_zlsma_test.py`: 策略的回测脚本
- `optimizer.py`: 策略参数优化脚本
- `portfolio_analysis.py`: 投资组合分析脚本
- `[股票代码]_optimization_results.csv`: 特定股票代码的优化结果

## 功能特点

1. 实现了基于蜡烛图和ZLSMA的交易策略
2. 提供数据获取功能，支持实时和历史数据
3. 包含策略回测功能，可评估策略性能
4. 支持参数优化，以找到最佳策略配置
5. 提供投资组合分析功能，可批量处理多只股票

## 使用说明

1. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

2. 运行单只股票的回测:
   ```
   python chandelier_zlsma_test.py [股票代码]
   ```

3. 运行单只股票的参数优化:
   ```
   python optimizer.py [股票代码]
   ```

4. 运行投资组合分析:
   ```
   python portfolio_analysis.py
   ```

5. 执行单元测试:
   ```
   python -m unittest test_chandelier_zlsma_strategy.py
   ```

6. 查看优化结果:
   打开`[股票代码]_optimization_results.csv`文件查看特定股票的优化参数。

## 注意事项

- 请确保在使用前正确配置数据源和API密钥（如果需要）。
- 交易策略仅供研究和学习使用，实际交易时请谨慎评估风险。
- 在运行投资组合分析之前，请在`portfolio_analysis.py`文件中更新您的持仓股票列表。

## 贡献

欢迎提交问题和拉取请求来改进这个项目。

## 许可证

[在此处添加您的许可证信息]