function optimize() {
    const symbol = document.getElementById('symbol').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!symbol || !startDate || !endDate) {
        alert('请填写完整的参数信息');
        return;
    }

    // 显示加载动画
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');

    fetch('/optimize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            symbol: symbol,
            startDate: startDate,
            endDate: endDate
        })
    })
    .then(response => response.json())
    .then(data => {
        // 隐藏加载动画
        document.getElementById('loading').classList.add('hidden');
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        displayResults(data);
    })
    .catch(error => {
        document.getElementById('loading').classList.add('hidden');
        alert('优化过程中发生错误: ' + error);
    });
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    const bestParamsDiv = document.getElementById('bestParams');
    const metricsDiv = document.getElementById('metrics');
    
    // 清空现有内容
    bestParamsDiv.innerHTML = '';
    metricsDiv.innerHTML = '';
    
    // 显示最优参数
    for (const [key, value] of Object.entries(data.bestParams)) {
        const paramDiv = document.createElement('div');
        paramDiv.className = 'metric-item group';
        paramDiv.innerHTML = `
            <span class="metric-label group-hover:text-blue-600">
                ${formatParamName(key)}
            </span>
            <span class="metric-value bg-blue-50 text-blue-600 group-hover:bg-blue-100">
                ${value}
            </span>
        `;
        bestParamsDiv.appendChild(paramDiv);
    }
    
    // 显示策略指标
    const metrics = data.metrics;
    const metricItems = [
        { key: 'sharpeRatio', label: '夏普比率', format: v => v.toFixed(2) },
        { key: 'maxDrawdown', label: '最大回撤', format: v => v.toFixed(2) + '%' },
        { key: 'winRate', label: '胜率', format: v => v.toFixed(2) + '%' },
        { key: 'totalReturn', label: '总收益率', format: v => v.toFixed(2) + '%' },
        { 
            key: 'lastSignal',
            label: '最新信号',
            custom: true,
            render: (signal) => {
                const div = document.createElement('div');
                div.className = 'metric-item';
                div.innerHTML = `
                    <span class="metric-label">最新信号</span>
                    <span class="signal-badge" style="color: ${signal.color}; background-color: ${getBackgroundColor(signal.color)}">
                        ${signal.text}
                    </span>
                `;
                return div;
            }
        }
    ];
    
    metricItems.forEach((item, index) => {
        if (item.custom) {
            metricsDiv.appendChild(item.render(metrics[item.key]));
        } else {
            const metricDiv = document.createElement('div');
            metricDiv.className = 'metric-item group';
            const value = item.format(metrics[item.key]);
            metricDiv.innerHTML = `
                <span class="metric-label group-hover:text-green-600">
                    ${item.label}
                </span>
                <span class="metric-value bg-green-50 text-green-600 group-hover:bg-green-100">
                    ${value}
                </span>
            `;
            metricDiv.style.animation = `fadeIn 0.5s ease-in ${index * 0.1}s both`;
            metricsDiv.appendChild(metricDiv);
        }
    });
    
    // 显示结果区域
    resultsDiv.classList.remove('hidden');
    resultsDiv.style.animation = 'fadeIn 0.5s ease-in';
}

function getBackgroundColor(color) {
    const colorMap = {
        'green': 'rgba(34, 197, 94, 0.08)',
        'red': 'rgba(239, 68, 68, 0.08)',
        'orange': 'rgba(249, 115, 22, 0.08)',
        'blue': 'rgba(59, 130, 246, 0.08)',
        'gray': 'rgba(107, 114, 128, 0.08)'
    };
    return colorMap[color] || 'rgba(107, 114, 128, 0.08)';
}

function formatParamName(key) {
    const nameMap = {
        'period': '周期',
        'mult': '倍数',
        'investment_fraction': '投资比例',
        'max_pyramiding': '最大加仓次数'
    };
    return nameMap[key] || key;
}

// 设置默认日期
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const lastYear = new Date();
    lastYear.setFullYear(today.getFullYear() - 1);
    
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    document.getElementById('startDate').value = lastYear.toISOString().split('T')[0];
});

// 添加表单提交处理函数
function handleSubmit(event) {
    event.preventDefault(); // 阻止表单默认提交行为
    optimize();
}

async function handleBacktest() {
    const symbol = document.getElementById('symbol').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!symbol) {
        alert('请输入股票代码');
        return;
    }
    
    // 显示加载动画
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('backtestResults').classList.add('hidden');
    
    try {
        const response = await fetch('/backtest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                startDate: startDate,
                endDate: endDate
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // 显示回测结果
        document.getElementById('backtestContent').textContent = data.result;
        document.getElementById('backtestResults').classList.remove('hidden');
        
    } catch (error) {
        alert('回测过程发生错误: ' + error);
    } finally {
        document.getElementById('loading').classList.add('hidden');
    }
} 