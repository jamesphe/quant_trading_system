import pandas as pd
import akshare as ak
import sys
from datetime import datetime
import os
import numpy as np
import talib

def get_stock_data(symbol):
    try:
        # 获取个股资金流向数据
        market = "sh" if symbol.startswith("6") else "sz"
        stock_df = ak.stock_individual_fund_flow(stock=symbol, market=market)
        
        # 获取历史K线数据用于计算技术指标
        hist_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                      start_date=(datetime.now() - pd.Timedelta(days=30)).strftime('%Y%m%d'),
                                      end_date=datetime.now().strftime('%Y%m%d'), 
                                      adjust="qfq")
        
        # 获取最新的一行数据
        latest_data = stock_df.iloc[-1]
        
        # 计算最近3日和最近5日的累计主力净流入-净额
        last_3_days_net_inflow = stock_df['主力净流入-净额'].iloc[-3:].sum()
        last_5_days_net_inflow = stock_df['主力净流入-净额'].iloc[-5:].sum()
        
        # 计算短线交易技术指标
        result = {
            'latest_price': latest_data['收盘价'],
            'latest_change': latest_data['涨跌幅'],
            'main_net_inflow': latest_data['主力净流入-净额'],
            'main_net_inflow_rate': latest_data['主力净流入-净占比'],
            'last_3_days_net_inflow': last_3_days_net_inflow,
            'last_5_days_net_inflow': last_5_days_net_inflow
        }
        
        # 添加新的短线交易指标
        if not hist_data.empty and len(hist_data) > 14:
            # 1. ROC (Rate of Change) - 价格变化速率
            close_prices = hist_data['收盘'].values
            result['roc_5'] = calculate_roc(close_prices, 5)
            
            # 2. 日内波动率 - 最高价与最低价之间的百分比差异
            result['intraday_volatility'] = (hist_data['最高'].iloc[-1] - hist_data['最低'].iloc[-1]) / hist_data['收盘'].iloc[-1] * 100
            
            # 3. ATR值 - 平均真实波幅
            high = hist_data['最高'].values
            low = hist_data['最低'].values
            close = hist_data['收盘'].values
            result['atr_14'] = calculate_atr(high, low, close, 14)
            
            # 4. EMA短期交叉状态
            result['ema_cross'] = check_ema_cross(close_prices)
            
            # 5. KDJ指标
            kdj_k, kdj_d, kdj_j = calculate_kdj(hist_data)
            result['kdj_k'] = kdj_k
            result['kdj_d'] = kdj_d
            result['kdj_j'] = kdj_j
            result['kdj_signal'] = get_kdj_signal(kdj_k, kdj_d, kdj_j)
            
            # 6. MACD指标
            macd, macd_signal, macd_hist = calculate_macd(close_prices)
            result['macd'] = macd
            result['macd_signal'] = macd_signal
            result['macd_hist'] = macd_hist
            result['macd_signal_type'] = 1 if macd_hist > 0 else (-1 if macd_hist < 0 else 0)
            
            # 7. 布林带指标
            upper, middle, lower = calculate_bollinger_bands(close_prices)
            result['boll_upper'] = upper
            result['boll_middle'] = middle
            result['boll_lower'] = lower
            result['boll_width'] = (upper - lower) / middle * 100  # 布林带宽度
            
            # 8. 资金流向变化率
            if len(stock_df) > 5:
                result['fund_flow_change_rate'] = calculate_fund_flow_change(stock_df)
            
        return result
    except Exception as e:
        print(f"获取股票 {symbol} 数据时发生错误: {e}")
        return None

def calculate_roc(prices, period=5):
    """计算ROC (Rate of Change)"""
    if len(prices) <= period:
        return 0
    return ((prices[-1] / prices[-period-1]) - 1) * 100

def calculate_atr(high, low, close, period=14):
    """计算ATR (Average True Range)"""
    try:
        if len(high) < period + 1:
            return 0
            
        tr1 = np.max(np.vstack((high[1:], close[:-1])).T, axis=1) - np.min(np.vstack((low[1:], close[:-1])).T, axis=1)
        tr1 = np.append([high[0] - low[0]], tr1)
        atr = np.mean(tr1[-period:])
        return atr
    except:
        return 0

def check_ema_cross(prices):
    """检查EMA交叉状态 (1:金叉, -1:死叉, 0:无交叉)"""
    try:
        if len(prices) < 10:
            return 0
            
        ema5 = np.array(pd.Series(prices).ewm(span=5, adjust=False).mean())
        ema10 = np.array(pd.Series(prices).ewm(span=10, adjust=False).mean())
        
        # 检查是否金叉
        if ema5[-2] <= ema10[-2] and ema5[-1] > ema10[-1]:
            return 1
        # 检查是否死叉
        elif ema5[-2] >= ema10[-2] and ema5[-1] < ema10[-1]:
            return -1
        else:
            return 0
    except:
        return 0

def calculate_kdj(data, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    try:
        data_len = len(data)
        if data_len < n:
            return 50, 50, 50
            
        data_close = data['收盘'].values
        data_high = data['最高'].values
        data_low = data['最低'].values
        
        # 计算RSV
        rsv = np.zeros(data_len)
        for i in range(n-1, data_len):
            high_n = max(data_high[i-n+1:i+1])
            low_n = min(data_low[i-n+1:i+1])
            rsv[i] = (data_close[i] - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
        
        # 计算K、D、J值
        k = np.zeros(data_len)
        d = np.zeros(data_len)
        j = np.zeros(data_len)
        
        k[n-1] = 50
        d[n-1] = 50
        
        for i in range(n, data_len):
            k[i] = (m1 * k[i-1] + (100 - m1) * rsv[i]) / 100
            d[i] = (m2 * d[i-1] + (100 - m2) * k[i]) / 100
            j[i] = 3 * k[i] - 2 * d[i]
        
        return k[-1], d[-1], j[-1]
    except:
        return 50, 50, 50

def get_kdj_signal(k, d, j):
    """获取KDJ信号 (1:金叉, -1:死叉, 0:无信号)"""
    if k > d:
        return 1
    elif k < d:
        return -1
    else:
        return 0

def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """计算MACD指标"""
    try:
        if len(prices) < max(fast_period, slow_period, signal_period):
            return 0, 0, 0
            
        # 计算EMA
        ema_fast = np.array(pd.Series(prices).ewm(span=fast_period, adjust=False).mean())
        ema_slow = np.array(pd.Series(prices).ewm(span=slow_period, adjust=False).mean())
        
        # 计算DIF
        dif = ema_fast - ema_slow
        
        # 计算DEA
        dea = np.array(pd.Series(dif).ewm(span=signal_period, adjust=False).mean())
        
        # 计算MACD柱状图
        macd_hist = 2 * (dif - dea)
        
        return dif[-1], dea[-1], macd_hist[-1]
    except:
        return 0, 0, 0

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """计算布林带指标"""
    try:
        if len(prices) < period:
            return prices[-1], prices[-1], prices[-1]
            
        # 计算移动平均线
        ma = np.mean(prices[-period:])
        
        # 计算标准差
        std = np.std(prices[-period:])
        
        # 计算上轨、中轨和下轨
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        
        return upper, ma, lower
    except:
        return prices[-1], prices[-1], prices[-1]

def calculate_fund_flow_change(stock_df):
    """计算资金流向变化率"""
    try:
        if len(stock_df) < 5:
            return 0
            
        # 计算最近5天和前5天的主力净流入总和
        recent_5_days = stock_df['主力净流入-净额'].iloc[-5:].sum()
        previous_5_days = stock_df['主力净流入-净额'].iloc[-10:-5].sum() if len(stock_df) >= 10 else 0
        
        # 计算变化率
        if previous_5_days == 0:
            return 0 if recent_5_days == 0 else (1 if recent_5_days > 0 else -1)
        else:
            return (recent_5_days - previous_5_days) / abs(previous_5_days) * 100
    except:
        return 0

def get_all_stocks_realtime_data():
    try:
        # 获取所有 A 股实时行情数据
        all_stocks_df = ak.stock_zh_a_spot_em()
        # 将股票代码设置为索引，方便后续查找
        return all_stocks_df.set_index('代码')
    except Exception as e:
        print(f"获取实时行情数据时发生错误: {e}")
        return None

def update_target_stocks(date_suffix=None):
    # 获取命令行参数中的日期
    if date_suffix is None:
        # 默认为当天日期
        date_suffix = datetime.now().strftime("%Y-%m-%d")
    
    input_file = f'stock_data/target_stocks_{date_suffix}.csv'
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件 '{input_file}' 不存在!")
        print("请检查日期格式是否正确，以及文件是否存在。")
        print("可用的文件列表:")
        
        # 列出stock_data目录下的所有target_stocks文件
        if os.path.exists('stock_data'):
            target_files = [f for f in os.listdir('stock_data') if f.startswith('target_stocks_')]
            for f in target_files:
                print(f"  - {f}")
        else:
            print("  stock_data目录不存在")
        
        return
    
    df = pd.read_csv(input_file, dtype={'symbol': str})
    
    # 添加基本列
    df['latest_price'] = None
    df['latest_change'] = None
    df['turnover_rate'] = None
    
    # 添加新的短线交易指标列
    df['roc_5'] = None
    df['intraday_volatility'] = None
    df['atr_14'] = None
    df['ema_cross'] = None
    df['kdj_signal'] = None
    df['macd_signal_type'] = None
    df['boll_width'] = None
    df['fund_flow_change_rate'] = None
    
    # 获取所有股票的实时数据
    all_stocks_data = get_all_stocks_realtime_data()
    
    if all_stocks_data is not None:
        # 更新目标股票的数据
        for index, row in df.iterrows():
            symbol = row['symbol'].zfill(6)
            print(f"正在处理股票 {symbol}...")
            
            if symbol in all_stocks_data.index:
                stock_data = all_stocks_data.loc[symbol]
                df.at[index, 'latest_price'] = stock_data['最新价']
                df.at[index, 'latest_change'] = stock_data['涨跌幅']
                df.at[index, 'turnover_rate'] = stock_data['换手率']
            else:
                print(f"未找到股票 {symbol} 的实时数据")
        
        # 获取其他数据（如资金流向和技术指标）
        for index, row in df.iterrows():
            symbol = row['symbol'].zfill(6)
            stock_data = get_stock_data(symbol)
            if stock_data:
                # 更新基本数据
                df.at[index, 'main_net_inflow'] = stock_data['main_net_inflow']
                df.at[index, 'main_net_inflow_rate'] = stock_data['main_net_inflow_rate']
                df.at[index, 'last_3_days_net_inflow'] = stock_data['last_3_days_net_inflow']
                df.at[index, 'last_5_days_net_inflow'] = stock_data['last_5_days_net_inflow']
                
                # 更新新增的短线交易指标
                if 'roc_5' in stock_data:
                    df.at[index, 'roc_5'] = stock_data['roc_5']
                if 'intraday_volatility' in stock_data:
                    df.at[index, 'intraday_volatility'] = stock_data['intraday_volatility']
                if 'atr_14' in stock_data:
                    df.at[index, 'atr_14'] = stock_data['atr_14']
                if 'ema_cross' in stock_data:
                    df.at[index, 'ema_cross'] = stock_data['ema_cross']
                if 'kdj_signal' in stock_data:
                    df.at[index, 'kdj_signal'] = stock_data['kdj_signal']
                if 'macd_signal_type' in stock_data:
                    df.at[index, 'macd_signal_type'] = stock_data['macd_signal_type']
                if 'boll_width' in stock_data:
                    df.at[index, 'boll_width'] = stock_data['boll_width']
                if 'fund_flow_change_rate' in stock_data:
                    df.at[index, 'fund_flow_change_rate'] = stock_data['fund_flow_change_rate']
    else:
        print("无法获取实时行情数据，将使用原有方法更新")
        for index, row in df.iterrows():
            symbol = row['symbol'].zfill(6)
            print(f"正在处理股票 {symbol}...")
            
            stock_data = get_stock_data(symbol)
            if stock_data:
                # 更新基本数据
                df.at[index, 'latest_price'] = stock_data['latest_price']
                df.at[index, 'latest_change'] = stock_data['latest_change']
                df.at[index, 'main_net_inflow'] = stock_data['main_net_inflow']
                df.at[index, 'main_net_inflow_rate'] = stock_data['main_net_inflow_rate']
                df.at[index, 'last_3_days_net_inflow'] = stock_data['last_3_days_net_inflow']
                df.at[index, 'last_5_days_net_inflow'] = stock_data['last_5_days_net_inflow']
                
                # 更新新增的短线交易指标
                if 'roc_5' in stock_data:
                    df.at[index, 'roc_5'] = stock_data['roc_5']
                if 'intraday_volatility' in stock_data:
                    df.at[index, 'intraday_volatility'] = stock_data['intraday_volatility']
                if 'atr_14' in stock_data:
                    df.at[index, 'atr_14'] = stock_data['atr_14']
                if 'ema_cross' in stock_data:
                    df.at[index, 'ema_cross'] = stock_data['ema_cross']
                if 'kdj_signal' in stock_data:
                    df.at[index, 'kdj_signal'] = stock_data['kdj_signal']
                if 'macd_signal_type' in stock_data:
                    df.at[index, 'macd_signal_type'] = stock_data['macd_signal_type']
                if 'boll_width' in stock_data:
                    df.at[index, 'boll_width'] = stock_data['boll_width']
                if 'fund_flow_change_rate' in stock_data:
                    df.at[index, 'fund_flow_change_rate'] = stock_data['fund_flow_change_rate']
            else:
                print(f"未找到股票 {symbol} 的数据")
    
    # 把df中的字段名称转换为中文
    df = df.rename(columns={
        'symbol': '股票代码', 'stock_name': '股票名称', 'latest_trading_amount': '最新交易量',
        'sharpe_ratio': '夏普比率', 'best_win_rate': '最佳胜率',
        'best_max_drawdown': '最佳最大回撤', 'best_return': '最佳回报',
        'last_signal': '最新信号', 'length': '长度', 'mult': '倍数',
        'zlsma_length': 'ZLSMA长度', 'investment_fraction': '投资比例',
        'max_pyramiding': '最大加仓', 'latest_price': '最新价格',
        'latest_change': '最新涨跌幅', 'turnover_rate': '换手率',
        'main_net_inflow': '主力净流入', 'main_net_inflow_rate': '主力净流入率',
        'last_3_days_net_inflow': '最近3日净流入', 'last_5_days_net_inflow': '最近5日净流入',
        'roc_5': '5日变化率', 'intraday_volatility': '日内波动率',
        'atr_14': '14日ATR', 'ema_cross': 'EMA交叉信号',
        'kdj_signal': 'KDJ信号', 'macd_signal_type': 'MACD信号',
        'boll_width': '布林带宽度', 'fund_flow_change_rate': '资金流变化率'
    })
    
    # 按涨跌幅降序排序
    df = df.sort_values(by='最新涨跌幅', ascending=False)
    
    # 确保stock_data目录存在
    os.makedirs('stock_data', exist_ok=True)
    
    # 保存更新后的数据到stock_data目录
    save_path = os.path.join('stock_data', f'updated_target_stocks_{date_suffix}.csv')
    df.to_csv(save_path, index=False)
    print(f"数据更新完成，已保存到 {save_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        date_suffix = sys.argv[1]
    else:
        date_suffix = datetime.now().strftime('%Y-%m-%d')
    update_target_stocks(date_suffix)
