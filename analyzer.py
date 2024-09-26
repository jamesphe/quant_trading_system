# analyzer.py

def print_analyzer_results(strategy):
    """
    打印分析器的结果，包括夏普比率和最大回撤

    参数：
    - strategy: 回测返回的策略对象
    """
    # 夏普比率
    sharpe_ratio = strategy.analyzers.sharpe.get_analysis()
    print(f"Sharpe Ratio: {sharpe_ratio.get('sharperatio', None)}")

    # 最大回撤
    drawdown = strategy.analyzers.drawdown.get_analysis()
    print(f"最大回撤: {drawdown['max']['drawdown']:.2f}%")