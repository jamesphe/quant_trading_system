from flask import Flask, render_template, request, jsonify, redirect
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
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from utils.email_sender import mail, send_verification_email, generate_verification_code
from flask_mail import Mail
import secrets
from datetime import datetime, timedelta


# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 在创建 Flask app 后添加配置
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 邮件配置
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # 使用您的邮件服务器
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # 替换为您的邮箱
app.config['MAIL_PASSWORD'] = 'your-password'  # 替换为您的邮箱密码
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

# 初始化扩展
db.init_app(app)
mail.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET'])
def login_page():
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('register.html')

@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        # 基本验证
        if not email or not password:
            return jsonify({'error': '邮箱和密码都是必需的'}), 400

        # 验证邮箱格式
        if not email.strip():
            return jsonify({'error': '邮箱不能为空'}), 400

        # 检查邮箱是否已被注册
        if User.query.filter_by(email=email).first():
            return jsonify({'error': '该邮箱已被注册'}), 400

        # 生成验证码和过期时间
        verification_code = generate_verification_code()
        expires = datetime.utcnow() + timedelta(minutes=10)

        # 创建新用户
        user = User(
            email=email,
            verification_code=verification_code,
            verification_code_expires=expires
        )
        user.set_password(password)

        # 保存到数据库
        db.session.add(user)
        db.session.commit()

        # 发送验证码邮件
        send_verification_email(app, email, verification_code)

        return jsonify({'message': '验证码已发送到您的邮箱'}), 200
    except Exception as e:
        logger.error(f"注册过程发生错误: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/verify', methods=['POST'])
def verify():
    try:
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        if user.is_verified:
            return jsonify({'error': '该账号已经验证过了'}), 400

        if (user.verification_code != code or
                datetime.utcnow() > user.verification_code_expires):
            return jsonify({'error': '验证码无效或已过期'}), 400

        user.is_verified = True
        user.verification_code = None
        user.verification_code_expires = None
        db.session.commit()

        return jsonify({'message': '验证成功'}), 200
    except Exception as e:
        logger.error(f"验证过程发生错误: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({'error': '邮箱或密码错误'}), 401

        if not user.is_verified:
            return jsonify({'error': '请先验证您的邮箱'}), 401

        login_user(user)
        return jsonify({'message': '登录成功'}), 200
    except Exception as e:
        logger.error(f"登录过程发生错误: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/optimize', methods=['POST'])
@login_required
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
@login_required
def backtest():
    try:
        logger.info('收到 /backtest 请求')
        data = request.get_json()
        logger.debug(f'请求数据: {data}')  # 添加请求数据日志
        
        # 验证输入参数
        if not data:
            logger.error('未收到有效的请求数据')
            return jsonify({
                'success': False,
                'error': '未收到有效的请求数据'
            })
            
        symbol = data.get('symbol')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        
        logger.info(f'回测参数: symbol={symbol}, start_date={start_date}, end_date={end_date}')
        
        # 验证必需的参数
        if not all([symbol, start_date, end_date]):
            missing_params = []
            if not symbol: missing_params.append('symbol')
            if not start_date: missing_params.append('startDate')
            if not end_date: missing_params.append('endDate')
            error_msg = f'缺少必需的参数：{", ".join(missing_params)}'
            logger.error(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            })
        
        try:
            import chandelier_zlsma_test
        except ImportError as e:
            logger.error(f'导入 chandelier_zlsma_test 失败: {str(e)}')
            return jsonify({
                'success': False,
                'error': f'回测模块导入失败: {str(e)}'
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
                'exception_message': str(e),
                'traceback': str(e.__traceback__)
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


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


if __name__ == '__main__':
    logger.info("注册的路由:")
    for rule in app.url_map.iter_rules():
        logger.info(f"{rule.endpoint}: {rule.methods} - {rule}")
        
    app.run(debug=True, host='0.0.0.0', port=5100)
