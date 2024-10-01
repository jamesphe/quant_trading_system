# 股票投资组合分析和交易建议系统

这个项目是一个股票投资组合分析和交易建议系统,使用 Chandelier Exit 和 ZLSMA 策略进行回测和优化。

## 主要功能

1. 对指定的股票组合进行参数优化
2. 使用优化后的参数进行回测
3. 生成每只股票的交易建议
4. 将交易建议汇总发送到微信

## 文件说明

- `portfolio_analysis.py`: 主程序,用于分析投资组合并生成交易建议
- `data_fetch.py`: 用于获取股票数据
- `chandelier_zlsma_test.py`: 使用 Chandelier Exit 和 ZLSMA 策略进行回测
- `strategies/chandelier_zlsma_strategy.py`: 定义了 Chandelier Exit 和 ZLSMA 策略
- `main_multithreaded.py`: 多线程优化程序
- `optimize_us.py`: 美股交易优化程序
- `*_optimization_results.csv`: 各股票的优化结果文件
- `run_analysis.sh`: 用于在 conda 环境中运行分析的 shell 脚本

## 使用方法

1. 确保已安装所有必要的依赖:
   ```
   pip install pandas numpy backtrader requests
   ```

2. 在 `portfolio_analysis.py` 文件中设置您的股票组合:
   ```python
   portfolio = ['300077', '300383', '300687', '603206']  # 根据实际情况修改
   ```

3. 在 `portfolio_analysis.py` 文件中设置您的 Server 酱 SCKEY:
   ```python
   sckey = "YOUR_SCKEY_HERE"  # 替换为您的实际 SCKEY
   ```
   注意: 请确保您使用的是最新的Server酱API。当前使用的API域名为 `sctapi.ftqq.com`。

4. 设置 conda 环境:
   ```
   conda create -n stock_analysis python=3.9
   conda activate stock_analysis
   pip install pandas numpy backtrader requests
   ```

5. 修改 `run_analysis.sh` 文件中的路径:
   ```bash
   #!/bin/bash
   source ~/anaconda3/etc/profile.d/conda.sh
   conda activate stock_analysis
   python /path/to/your/portfolio_analysis.py >> /path/to/logfile.log 2>&1
   ```
   请确保将路径替换为您系统上的实际路径。

6. 给 `run_analysis.sh` 添加执行权限:
   ```
   chmod +x /path/to/your/run_analysis.sh
   ```

7. 设置定时运行:
   - 对于 Linux 或 macOS:
     使用 cron 任务。编辑 crontab (`crontab -e`),添加如下行:
     ```
     0 9 * * * /bin/bash /path/to/your/run_analysis.sh
     ```
     这将使程序每天早上 9 点运行。

   - 对于 Windows:
     创建一个批处理文件 `run_analysis.bat`:
     ```batch
     @echo off
     call C:\Users\YourUsername\Anaconda3\Scripts\activate.bat
     call conda activate stock_analysis
     python C:\path\to\your\portfolio_analysis.py >> C:\path\to\logfile.log 2>&1
     ```
     然后使用任务计划程序创建一个每天运行这个批处理文件的任务。

## 注意事项

- 请确保您有足够的计算资源,因为优化过程可能比较耗时。
- 交易建议仅供参考,请结合实际情况和专业意见进行投资决策。
- 定期检查和更新您的 Server 酱 SCKEY,以确保消息能正常发送到微信。
- 请确保您使用的是最新版本的Server酱API。如果API有更新,请相应地更新代码中的域名。
- 如果您设置了定时任务,请确保运行环境中有所有必要的依赖,并且路径设置正确。
- 定时任务可能需要管理员权限才能正确执行,特别是在 Windows 系统上。
- 定期检查日志文件以确保脚本正常运行。
- 如果您的系统进行了重启或更新,请确保 conda 环境和定时任务仍然正确设置。

## 贡献

欢迎提出问题、建议或直接贡献代码。请通过 GitHub Issues 或 Pull Requests 与我们互动。

## 许可

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。