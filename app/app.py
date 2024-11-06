from flask import Flask, render_template, request, jsonify
import backtrader as bt
from optimizer import optimize_strategy
from data_fetch import (
    get_stock_data, 
    get_etf_data, 
    get_us_stock_data, 
    get_stock_name
)
from strategies import ChandelierZlSmaStrategy
import logging  # 添加日志模块
import pandas as pd
import os
from datetime import datetime


# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        start_date = data.get('startDate')
        end_date = data.get('endDate')

        # 获取股票名称
        stock_name = get_stock_name(symbol)
        logger.info(f'股票名称: {stock_name}')

        # 根据股票类型获取数据
        if symbol.startswith(('51', '159')):
            stock_data = get_etf_data(symbol, start_date, end_date)
        elif symbol.isdigit():
            stock_data = get_stock_data(symbol, start_date, end_date)
        else:
            stock_data = get_us_stock_data(symbol, start_date, end_date)
        
        if stock_data.empty:
            logger.warning(f'股票 {symbol} 没有可用的数据进行回测')
            return jsonify({'error': f'股票 {symbol} 没有可用的数据进行回测。'})

        # 定义数据源类
        class AkShareData(bt.feeds.PandasData):
            params = (
                ('datetime', None),
                ('open', 'Open'),
                ('high', 'High'),
                ('low', 'Low'),
                ('close', 'Close'),
                ('volume', 'Volume'),
                ('openinterest', -1),
            )

        data_feed = AkShareData(dataname=stock_data)
        
        # 运行优化
        study = optimize_strategy(
            ChandelierZlSmaStrategy, 
            data_feed, 
            n_trials=100, 
            n_jobs=1
        )
        best_trial = study.best_trial

        # 获取最优参数
        best_params = {
            'period': int(best_trial.params['period']),
            'mult': round(best_trial.params['mult'], 2),
            'investment_fraction': round(
                best_trial.params['investment_fraction'], 
                2
            ),
            'max_pyramiding': int(best_trial.params['max_pyramiding'])
        }

        logger.info(f"最优参数: {best_params}")
        logger.info(f"夏普比率: {best_trial.value * -1:.2f}")
        logger.info(f"最大回撤: {best_trial.user_attrs['max_drawdown']:.2f}%")
        logger.info(f"胜率: {best_trial.user_attrs['win_rate']*100:.2f}%")
        logger.info(f"总收益率: {best_trial.user_attrs['total_return']*100:.2f}%")
        logger.info(f"最后信号: {best_trial.user_attrs['last_signal']}")

        # 构建返回结果
        result = {
            'stockName': stock_name,
            'bestParams': best_params,
            'metrics': {
                'sharpeRatio': round(best_trial.value * -1, 2),
                'maxDrawdown': round(best_trial.user_attrs['max_drawdown'], 2),
                'winRate': round(best_trial.user_attrs['win_rate'] * 100, 2),
                'totalReturn': round(
                    best_trial.user_attrs['total_return'] * 100, 
                    2
                ),
                'lastSignal': _convert_signal_to_text(
                    best_trial.user_attrs['last_signal']
                )
            }
        }

        # 保存优化结果到CSV
        optimization_result = {
            'symbol': symbol,
            'strategy': 'ChandelierZlSmaStrategy',
            **best_params,
            'sharpe_ratio': round(best_trial.value * -1, 2),
            'max_drawdown': round(best_trial.user_attrs['max_drawdown'], 2),
            'win_rate': round(best_trial.user_attrs['win_rate'], 2),
            'total_return': round(best_trial.user_attrs['total_return'], 4),
            'last_signal': best_trial.user_attrs['last_signal'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        df = pd.DataFrame([optimization_result])
        results_dir = 'results'
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        # 保存优化结果到CSV文件
        df.to_csv(
            f'{results_dir}/{symbol}_optimization_results.csv',
            index=False
        )

        logger.debug(f"返回果: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"优化过程发生错误: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)})


@app.route('/backtest', methods=['POST'])
def backtest():
    try:
        logger.info('收到 /backtest 请求')
        data = request.get_json()
        
        # 验证输入参数
        if not data:
            return jsonify({
                'success': False,
                'error': '未收到有效的请求数据'
            })
            
        symbol = data.get('symbol')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        # 验证必需的参数
        if not all([symbol, start_date, end_date]):
            return jsonify({
                'success': False,
                'error': '缺少必需的参数：symbol、startDate 或 endDate'
            })
        
        # 获取股票名称
        stock_name = get_stock_name(symbol)
        
        # 导入并执行回测脚本
        import chandelier_zlsma_test
        # 检查是否存在优化参数文件
        optimization_file = f'results/{symbol}_optimization_results.csv'
        if os.path.exists(optimization_file):
            # 读取优化参数
            opt_params = pd.read_csv(optimization_file).iloc[-1]
            result = chandelier_zlsma_test.run_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                printlog=True,
                period=int(opt_params['period']),
                mult=float(opt_params['mult']),
                investment_fraction=float(opt_params['investment_fraction']),
                max_pyramiding=int(opt_params['max_pyramiding'])
            )
        else:
            # 使用默认参数
            result = chandelier_zlsma_test.run_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                printlog=True,
                period=14,
                mult=2.0,
                investment_fraction=0.8,
                max_pyramiding=0
            )
               
        # 确保返回结果包含必要的字段
        if not result:
            return jsonify({
                'success': False,
                'error': '回测执行完成但未返回结果'
            })
            
        # 添加成功标志
        result['success'] = True
        result['stockName'] = stock_name
        return jsonify(result)

    except Exception as e:
        logger.error(f'回测过程发生错误: {str(e)}', exc_info=True)
        error_message = f'回测失败: {str(e)}'
        return jsonify({
            'success': False,
            'error': error_message,
            'details': {
                'exception_type': type(e).__name__,
                'exception_message': str(e)
            }
        }), 500


def _convert_signal_to_text(signal):
    """
    将信号数值转换为文本说明和对应的颜色
    返回格式: {'text': '信号说明', 'color': '颜色代码'}
    """
    signal_map = {
        1: {
            'text': "建仓信号",
            'color': 'green'   # 建仓信号使用绿色
        },
        -1: {
            'text': "清仓信号",
            'color': 'red'     # 清仓信号使用红色
        },
        2: {
            'text': "加仓信号",
            'color': 'green'   # 加仓信号用绿色
        },
        -2: {
            'text': "减仓预警",
            'color': 'orange'  # 减仓预警使用橙色
        },
        3: {
            'text': "建仓预警",
            'color': 'blue'    # 建仓预警使用蓝色
        },
        -3: {
            'text': "减仓预警",
            'color': 'orange'  # 减仓预警使用橙色
        },
        0: {
            'text': "无交易信号",
            'color': 'gray'    # 无信号使用灰色
        }
    }
    return signal_map.get(signal, {'text': "未知信号", 'color': 'gray'})


if __name__ == '__main__':
    logger.info("注册的路由:")
    for rule in app.url_map.iter_rules():
        logger.info(f"{rule.endpoint}: {rule.methods} - {rule}")
        
    app.run(debug=True, host='0.0.0.0', port=5100)