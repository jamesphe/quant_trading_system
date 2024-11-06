from flask import request, jsonify
from datetime import datetime, timedelta

@app.route('/analyze_stock', methods=['POST'])
def analyze_stock():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        
        if not symbol:
            return jsonify({'error': '请提供股票代码'})
            
        # 获取最近3个月的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # 调用ai_stock_analysis.py中的分析函数
        from ai_stock_analysis import get_kimi_analysis, get_stock_data
        
        # 获取股票数据
        stock_data = get_stock_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
        if stock_data is None or stock_data.empty:
            return jsonify({'error': f'无法获取股票 {symbol} 的数据'})
            
        # 获取分析结果
        analysis_result = get_kimi_analysis(stock_data)
        
        # 将分析结果转换为Markdown格式
        markdown_result = f"""
# {symbol} 股票分析报告

## 分析日期
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 分析结果
{analysis_result}
"""
        
        return jsonify({
            'analysis': markdown_result
        })
        
    except Exception as e:
        logger.error(f"分析过程发生错误: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}) 