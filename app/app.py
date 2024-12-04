from flask import (
    Flask, 
    render_template, 
    request, 
    jsonify, 
    Response, 
    stream_with_context
)
import backtrader as bt
from optimizer import optimize_strategy
from data_fetch import (
    get_stock_data, 
    get_etf_data, 
    get_us_stock_data, 
    get_stock_name,
    get_stock_basic_info
)
from strategies import ChandelierZlSmaStrategy
import logging
import pandas as pd
import os
from datetime import datetime, timedelta
import subprocess
import json
from stock_analysis import ZhipuAIModel, KimiModel, OpenAIModel, analyze_stock
import markdown
from pathlib import Path
import requests
import time
import base64
import hashlib
from dotenv import load_dotenv
from websocket import WebSocketApp
import hmac
import ssl
from wsgiref.handlers import format_date_time
from time import mktime
import _thread as thread
from urllib.parse import urlencode

# 加载 .env 文件
load_dotenv()

# 获取讯飞配置
XFYUN_APPID = os.getenv('XFYUN_APPID')
XFYUN_API_KEY = os.getenv('XFYUN_API_KEY')
XFYUN_API_SECRET = os.getenv('XFYUN_API_SECRET')

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Azure 配置
AZURE_KEY = os.getenv('AZURE_KEY')
AZURE_REGION = 'eastasia'


@app.route('/')
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', today=today)


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

        # 检查是否存在优化参数文件且是当天15:00后生成的
        optimization_file = get_optimization_file(symbol)
        current_time = datetime.now()
        cutoff_time = current_time.replace(
            hour=15, 
            minute=0, 
            second=0, 
            microsecond=0
        )
        
        if os.path.exists(optimization_file):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(optimization_file))
            # 判断是否可以使用已有的优化结果文件
            if (file_mtime > cutoff_time or 
                (current_time < cutoff_time and 
                 file_mtime.date() == current_time.date())):
                logger.info(f'使用已有的优化结果文件: {optimization_file}')
                df = pd.read_csv(optimization_file)
                if not df.empty:
                    best_row = df.iloc[0]
                    result = {
                        'stockName': stock_name,
                        'bestParams': {
                            'period': int(best_row['period']),
                            'mult': round(float(best_row['mult']), 2),
                            'investment_fraction': round(
                                float(best_row['investment_fraction']), 2
                            ),
                            'max_pyramiding': int(best_row['max_pyramiding'])
                        },
                        'metrics': {
                            'sharpeRatio': round(float(best_row['sharpe_ratio']), 2),
                            'maxDrawdown': round(float(best_row['max_drawdown']), 2),
                            'winRate': round(float(best_row['win_rate']) * 100, 2),
                            'totalReturn': round(float(best_row['total_return']) * 100, 2),
                            'lastSignal': _convert_signal_to_text(best_row['last_signal'])
                        }
                    }
                    return jsonify(result)

        # 如果没有最新的优化果文件，执行优化流程
        # 根据股票类型获取数据
        if symbol.startswith(('51', '159')):
            stock_data = get_etf_data(symbol, start_date, end_date)
        elif symbol.isdigit():
            stock_data = get_stock_data(symbol, start_date, end_date)
        else:
            stock_data = get_us_stock_data(symbol, start_date, end_date)
        
        if stock_data.empty:
            logger.warning(f'股票 {symbol} 没有可用的数进行回测')
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
            n_trials=50, 
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
            f'{results_dir}/{symbol}_ChandelierZlSmaStrategy_optimization_results.csv',
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
        
        # 验证输入参
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
        optimization_file = get_optimization_file(symbol)
        if os.path.exists(optimization_file):
            # 读化参数
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
            # 使用默认参
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


@app.route('/portfolio_analysis', methods=['POST'])
def portfolio_analysis():
    try:
        data = request.get_json()
        
        # 构建命令行参数
        cmd = ['python', 'portfolio_analysis.py']
        if data.get('mode'):
            cmd.extend(['--mode', data['mode']])
        if data.get('date'):
            cmd.extend(['--date', data['date']])
        if data.get('sendToWechat'):
            cmd.append('--send-wechat')
            
        # 运行portfolio_analysis.py
        result = subprocess.run(
            cmd,
            capture_output=True, 
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode != 0:
            raise Exception(f'分析脚本执行失败: {result.stderr}')
            
        # 解析输出内容
        output_lines = result.stdout.split('\n')
        analysis_results = []
        current_stock = None
        current_content = []
        
        for line in output_lines:
            if line.startswith('==='):
                continue
            if '（' in line and '）' in line:
                if current_stock:
                    analysis_results.append({
                        'stock': current_stock,
                        'content': '\n'.join(current_content)
                    })
                current_stock = line.strip()
                current_content = []
            elif line.strip():
                current_content.append(line.strip())
                
        if current_stock:
            analysis_results.append({
                'stock': current_stock,
                'content': '\n'.join(current_content)
            })
            
        return jsonify({
            'success': True,
            'results': analysis_results,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'分析失败: {str(e)}'
        }), 500


@app.route('/api/daily_picks', methods=['POST'])
def api_daily_picks():
    data = request.json
    date = data.get('date')
    model = data.get('model')
    
    try:
        # 构建文件路径
        file_name = f'stocks_analysis_{model}_{date}.md'
        file_path = Path(__file__).parent / 'AIResult' / file_name
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': f'未找到{date}日的{model}分析结果'
            })
            
        # 读取 markdown 内容并转换为 HTML
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
            
        # 使用 markdown 库转换为 HTML
        html_content = markdown.markdown(
            md_content,
            extensions=[
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.codehilite'
            ]
        )
            
        return jsonify({
            'success': True,
            'date': date,
            'model': model,
            'content': html_content  # 返回转换后的 HTML 内容
        })
        
    except Exception as e:
        logger.error(f'获取每日选股分析发生错误: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/analyze_stock', methods=['POST'])
def analyze_stock_route():
    try:
        logger.debug("开始处理股票分析请求")
        data = request.get_json()
        logger.debug(f"接收到的请求数据: {data}")
        
        symbol = data.get('symbol')
        model_type = data.get('model', 'zhipu')
        logger.debug(f"股票代码: {symbol}, 模型类型: {model_type}")
        
        if not symbol:
            logger.warning("缺少股票代码参数")
            return jsonify({
                'success': False,
                'error': '缺少股票代码参数'
            }), 400

        def generate():
            try:
                # 发送初始消息
                yield 'data: {"content": "正在获取股票数据..."}\n\n'
                
                # 计算日期范围
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=50)).strftime('%Y-%m-%d')
                
                # 初始化选择的AI模型
                if model_type == 'kimi':
                    model = KimiModel()
                elif model_type == 'openai':
                    model = OpenAIModel() 
                else:
                    model = ZhipuAIModel()
                yield 'data: {"content": "正在进行分析..."}\n\n'
                
                # 使用生成器方式获取分析结果
                for chunk in analyze_stock(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    model=model,
                    stream=True
                ):
                    if chunk:
                        # 确保chunk是JSON格式的字
                        if isinstance(chunk, str):
                            yield f'data: {{"content": {json.dumps(chunk)}}}\n\n'
                        else:
                            yield f'data: {json.dumps({"content": chunk})}\n\n'
                
                # 发送完成消息
                yield 'data: {"content": "\\n\\n============================\\n\\n分析完成"}\n\n'
                
            except Exception as e:
                logger.error(f"生成分析内容时出错: {str(e)}", exc_info=True)
                error_msg = json.dumps({"error": str(e)})
                yield f"data: {error_msg}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # 禁用 Nginx 缓冲
            }
        )
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'处理请求时发生错误: {str(e)}'
        }), 500


@app.route('/api/stock/basic_info/<stock_code>')
def get_basic_info(stock_code):
    """获取股票基本信息的API端点"""
    info = get_stock_basic_info(stock_code)
    if info:
        return jsonify({
            'status': 'success',
            'data': info
        })
    else:
        return jsonify({
            'status': 'error',
            'message': f'无法获取股票 {stock_code} 的基本信息'
        }), 404


def _convert_signal_to_text(signal):
    """
    将信号数值转换为文本说明和对应的颜
    返回格式: {'text': '信号说明', 'color': '颜色代码'}
    """
    signal_map = {
        1: {
            'text': "建仓信号",
            'color': 'green'   # 建���号使用绿色
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


def get_optimization_file(symbol, strategy="ChandelierZlSmaStrategy"):
    return f'results/{symbol}_{strategy}_optimization_results.csv'


@app.route('/api/get_azure_token', methods=['POST'])
def get_azure_token():
    try:
        url = f'https://{AZURE_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken'
        headers = {
            'Ocp-Apim-Subscription-Key': AZURE_KEY
        }
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        
        return jsonify({
            'token': response.text,
            'region': AZURE_REGION
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/xfyun/tts', methods=['POST'])
def xfyun_tts():
    try:
        text = request.json.get('text')
        speed = request.json.get('speed', 50)  # 获取语速参数，默认50
        
        if not text:
            return jsonify({'error': '缺少文本内容'}), 400
            
        # 限制文本长度
        if len(text) > 8000:
            text = text[:8000]
            logger.warning('文本超长已截断到8000字符')

        # 创建音频文件的临时路径
        audio_file = os.path.join(os.path.dirname(__file__), 'temp', f'tts_{int(time.time())}.mp3')
        os.makedirs(os.path.dirname(audio_file), exist_ok=True)

        # WebSocket参数类
        class WsParam:
            def __init__(self, appid, api_key, api_secret, text):
                self.APPID = appid
                self.APIKey = api_key
                self.APISecret = api_secret
                self.Text = text
                
                self.CommonArgs = {"app_id": self.APPID}
                self.BusinessArgs = {
                    "aue": "lame",
                    "auf": "audio/L16;rate=16000",
                    "vcn": "xiaoyan",
                    "tte": "utf8",
                    "speed": 50,
                    "volume": 50,
                    "pitch": 50,
                }
                self.Data = {
                    "status": 2,
                    "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")
                }

            def create_url(self):
                url = 'wss://tts-api.xfyun.cn/v2/tts'
                # 生成RFC1123格式的时间戳
                now = datetime.now()
                date = format_date_time(mktime(now.timetuple()))

                # 拼接字符串
                signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
                signature_origin += "date: " + date + "\n"
                signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"

                # hmac-sha256加密
                signature_sha = hmac.new(
                    self.APISecret.encode('utf-8'),
                    signature_origin.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                signature_sha = base64.b64encode(signature_sha).decode()

                authorization_origin = (
                    f'api_key="{self.APIKey}", algorithm="hmac-sha256", '
                    f'headers="host date request-line", signature="{signature_sha}"'
                )
                authorization = base64.b64encode(
                    authorization_origin.encode('utf-8')
                ).decode()

                # 组织url参数
                v = {
                    "authorization": authorization,
                    "date": date,
                    "host": "ws-api.xfyun.cn"
                }
                return url + '?' + urlencode(v)

        # 处理音频数据
        audio_data = bytearray()

        def on_message(ws, message):
            try:
                message = json.loads(message)
                code = message["code"]
                if code != 0:
                    logger.error(f"讯飞服务返回错误: {message}")
                    ws.close()
                    return
                    
                audio = message["data"]["audio"]
                status = message["data"]["status"]
                
                # 解码音频数据并保存
                audio_chunk = base64.b64decode(audio)
                audio_data.extend(audio_chunk)
                
                # 如果是最后一帧，关闭连接
                if status == 2:
                    ws.close()
                
            except Exception as e:
                logger.error(f"处理讯飞响应失败: {str(e)}")
                ws.close()

        def on_error(ws, error):
            logger.error(f"WebSocket错误: {str(error)}")

        def on_close(ws):
            logger.info("WebSocket连接已关闭")

        def on_open(ws):
            def run(*args):
                data = {
                    "common": ws_param.CommonArgs,
                    "business": ws_param.BusinessArgs,
                    "data": ws_param.Data,
                }
                ws.send(json.dumps(data))
            thread.start_new_thread(run, ())

        # 创建WebSocket连接
        ws_param = WsParam(XFYUN_APPID, XFYUN_API_KEY, XFYUN_API_SECRET, text)
        ws_url = ws_param.create_url()
        
        ws = WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        # 返回音频数据
        if audio_data:
            return Response(
                bytes(audio_data),
                mimetype='audio/mpeg',
                headers={
                    'Cache-Control': 'no-cache',
                    'Content-Type': 'audio/mpeg'
                }
            )
        else:
            return jsonify({'error': '未获取到音频数据'}), 500

    except Exception as e:
        logger.error(f'语音合成失败: {str(e)}', exc_info=True)
        return jsonify({'error': f'语音合成失败: {str(e)}'}), 500


@app.route('/api/target_stocks', methods=['POST'])
def get_target_stocks():
    try:
        data = request.get_json()
        date = data.get('date')
        
        if not date:
            return jsonify({
                'success': False,
                'error': '请选择日期'
            }), 400
            
        # 将日期格式统一转换为 YYYY-MM-DD
        try:
            # 尝试将日期转换为 YYYY-MM-DD 格式
            parsed_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            # 如果转换失败,返回错误信息
            return jsonify({
                'success': False,
                'error': '日期格式错误,请使用YYYY-MM-DD格式'
            }), 400

        # 构建文件路径
        file_path = os.path.join(
            os.path.dirname(__file__), 
            'stock_data', 
            f'updated_target_stocks_{parsed_date}.csv'
        )
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': f'未找到{parsed_date}的目标股票数据'
            }), 404

        # 读取CSV文件
        df = pd.read_csv(file_path, dtype={'股票代码': str})
        
        # 选择需要的列
        selected_columns = ['股票代码', '股票名称', 'industry', '最新价格', '最新涨跌幅', '换手率', '夏普比率', '最佳回报', '最佳胜率']
        df = df[selected_columns]
        
        # 转换为字典列表
        stocks = df.to_dict('records')
        
        return jsonify({
            'success': True,
            'data': stocks
        })
        
    except Exception as e:
        logger.error(f'获取目标股票数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'获取数据失败: {str(e)}'
        }), 500


@app.route('/api/update_prices', methods=['POST'])
def update_prices():
    try:
        data = request.get_json()
        date = data.get('date')
        
        if not date:
            return jsonify({
                'success': False,
                'error': '请选择日期'
            }), 400
            
        # 确保日期格式为 YYYY-MM-DD
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': '日期格式错误，请使用YYYY-MM-DD格式'
            }), 400
            
        # 调用更新脚本
        try:
            from get_latest_prices import update_target_stocks
            # 执行更新，传入标准格式的日期
            update_target_stocks(parsed_date)
            
            return jsonify({
                'success': True,
                'message': '价格更新成功'
            })
            
        except FileNotFoundError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
        except Exception as e:
            logger.error(f'更新价格失败: {str(e)}', exc_info=True)
            return jsonify({
                'success': False,
                'error': f'更新价格失败: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f'处理更新请求失败: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'处理请求失败: {str(e)}'
        }), 500


if __name__ == '__main__':
    logger.info("注册的路由:")
    for rule in app.url_map.iter_rules():
        logger.info(f"{rule.endpoint}: {rule.methods} - {rule}")
        
    app.run(debug=True, host='0.0.0.0', port=5100)