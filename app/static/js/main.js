function optimize() {
    const symbol = document.getElementById('symbol').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!symbol || !startDate || !endDate) {
        alert('请填写完整的参数信息');
        return;
    }

    // 显示加载动画，隐藏回测结果区域
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');
    document.getElementById('stockInfo').classList.add('hidden');
    document.getElementById('backtestResults').classList.add('hidden');

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
        
        // 显示优化结果
        displayResults(data);
    })
    .catch(error => {
        console.error('优化请求错误:', error);
        document.getElementById('loading').classList.add('hidden');
        alert('优化过程中发生错误: ' + error);
    });
}

function displayResults(data) {
    console.log('开始显示结果:', data); // 调试日志

    // 首先确保股票信息显示
    const stockInfo = document.getElementById('stockInfo');
    const stockName = document.getElementById('stockName');
    const stockCode = document.getElementById('stockCode');
    
    console.log('股票信息元素:', { stockInfo, stockName, stockCode }); // 调试日志
    
    if (data.stockName) {
        console.log('显示股票名称:', data.stockName); // 调试日志
        stockName.textContent = data.stockName;
        stockCode.textContent = `股票代码：${document.getElementById('symbol').value}`;
        stockInfo.classList.remove('hidden');
    }

    const resultsDiv = document.getElementById('results');
    const bestParamsDiv = document.getElementById('bestParams');
    const metricsDiv = document.getElementById('metrics');
    
    console.log('结果显示元素:', { resultsDiv, bestParamsDiv, metricsDiv }); // 调试日志
    
    // 清空现有内容
    bestParamsDiv.innerHTML = '';
    metricsDiv.innerHTML = '';
    
    // 显示最优参数
    console.log('开始显示最优参数:', data.bestParams); // 调试日志
    for (const [key, value] of Object.entries(data.bestParams)) {
        console.log('处理参数:', key, value); // 调试日志
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
    console.log('开始显示策略指标:', metrics); // 调试日志
    
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
                console.log('渲染信号:', signal); // 调试日志
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
        console.log('处理指标项:', item.key); // 调试日志
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
    console.log('显示结果区域'); // 调试日志
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

// 修改 DOMContentLoaded 事件处理函数
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    
    // 设置默认日期
    const today = new Date();
    const lastYear = new Date();
    lastYear.setFullYear(today.getFullYear() - 1);
    
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    document.getElementById('startDate').value = lastYear.toISOString().split('T')[0];
    
    // 初始化标签页
    initializeTabs();
});

// 添加初始化标签页的函数
function initializeTabs() {
    // 从 URL 获取当前标签页，如果没有则默认为 'optimization'
    const urlParams = new URLSearchParams(window.location.search);
    const currentTab = urlParams.get('tab') || 'optimization';
    
    // 手动调用切换函数
    switchTab(currentTab);
    
    console.log('Tabs initialized:', {
        currentTab,
        selectedTabExists: !!document.getElementById(`${currentTab}-tab`),
        activeButtonExists: !!document.querySelector(`[data-tab="${currentTab}"]`)
    });
}

// 修改 switchTab 函数，确保动画效果
function switchTab(tabName) {
    console.log('Switching to tab:', tabName);
    
    // 获取所有标签页内容
    const tabContents = document.querySelectorAll('.tab-content');
    
    // 隐藏所有标签页内容
    tabContents.forEach(tab => {
        tab.style.display = 'none';
        tab.classList.remove('active');
    });
    
    // 显示选中的标签页内容
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.style.display = 'block';
        // 使用 requestAnimationFrame 确保过渡效果正常工作
        requestAnimationFrame(() => {
            selectedTab.classList.add('active');
        });
    }
    
    // 更新标签按钮样式
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(button => {
        button.classList.remove('active-tab');
    });
    
    const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeButton) {
        activeButton.classList.add('active-tab');
        
        // 更新指示器位置
        const indicator = document.querySelector('.tab-indicator');
        if (indicator) {
            const buttonRect = activeButton.getBoundingClientRect();
            const navRect = document.querySelector('.tab-nav').getBoundingClientRect();
            
            indicator.style.width = `${buttonRect.width}px`;
            indicator.style.transform = `translateX(${buttonRect.left - navRect.left}px)`;
        }
        
        // 更新 URL
        const url = new URL(window.location);
        url.searchParams.set('tab', tabName);
        window.history.pushState({}, '', url);
    }
}

// 添加表单提交处理函数
function handleSubmit(event) {
    event.preventDefault(); // 阻止表单默认提交行为
    optimize();
}

async function handleBacktest() {
    const symbol = document.getElementById('symbol').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!symbol || !startDate || !endDate) {
        alert('请填写完整的参数信息');
        return;
    }

    // 只显示加载动画，不隐藏结果区域
    document.getElementById('loading').classList.remove('hidden');
    
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
        
        // 隐藏加载动画
        document.getElementById('loading').classList.add('hidden');
        
        if (!data.success) {
            alert(data.error || '回测失败');
            return;
        }
        
        // 显示回测结果
        displayBacktestResults(data);
        
    } catch (error) {
        document.getElementById('loading').classList.add('hidden');
        alert('回测过程发生错误: ' + error);
    }
}

// 个股分析处理函数
async function handleAnalysis(event) {
    event.preventDefault();
    console.log('Analysis form submitted');
    
    const symbol = document.getElementById('analysisSymbol').value;
    
    if (!symbol) {
        alert('请输入股票代码');
        return;
    }
    
    console.log('Analyzing stock:', symbol);
    
    // 显示加载动画
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('analysisResults').classList.add('hidden');
    
    try {
        const response = await fetch('/analyze_stock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol
            })
        });
        
        const data = await response.json();
        console.log('Analysis response:', data);
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // 显示分析结果
        const analysisContent = document.getElementById('analysisContent');
        if (analysisContent) {
            analysisContent.innerHTML = marked.parse(data.analysis);
            document.getElementById('analysisResults').classList.remove('hidden');
            console.log('Analysis results displayed');
        } else {
            console.error('Analysis content element not found');
        }
        
    } catch (error) {
        console.error('Analysis error:', error);
        alert('分析过程发生错误: ' + error);
    } finally {
        document.getElementById('loading').classList.add('hidden');
    }
}

function displayBacktestResults(data) {
    console.log('显示回测结果:', data);
    
    const backtestResults = document.getElementById('backtestResults');
    backtestResults.innerHTML = `
        <div class="bg-white rounded-xl shadow-lg p-6 transform transition-all duration-500 ease-in-out">
            <!-- 基本信息 -->
            <div class="mb-6 fade-in" style="animation-delay: 0.1s">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">基本信息</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="metric-item">
                        <span class="metric-label">初始资金</span>
                        <span class="metric-value">¥${data.basic_info.initial_cash.toLocaleString('zh-CN', {maximumFractionDigits: 2})}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">最终资金</span>
                        <span class="metric-value">¥${data.basic_info.final_cash.toLocaleString('zh-CN', {maximumFractionDigits: 2})}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">总收益</span>
                        <span class="metric-value ${data.basic_info.total_profit >= 0 ? 'text-green-600' : 'text-red-600'}">
                            ¥${data.basic_info.total_profit.toLocaleString('zh-CN', {maximumFractionDigits: 2})}
                        </span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">收益率</span>
                        <span class="metric-value ${data.basic_info.roi >= 0 ? 'text-green-600' : 'text-red-600'}">
                            ${data.basic_info.roi.toFixed(2)}%
                        </span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">胜率</span>
                        <span class="metric-value">${data.basic_info.win_rate.toFixed(2)}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">最大回撤</span>
                        <span class="metric-value text-red-600">${data.basic_info.max_drawdown.toFixed(2)}%</span>
                    </div>
                </div>
            </div>

            <!-- 最新行情 -->
            <div class="mb-6 fade-in" style="animation-delay: 0.2s">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">最新行情</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="metric-item">
                        <span class="metric-label">日期</span>
                        <span class="metric-value">${data.latest_data.date}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">收盘价</span>
                        <span class="metric-value">¥${data.latest_data.close.toFixed(2)}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">涨跌幅</span>
                        <span class="metric-value ${data.latest_data.change_pct >= 0 ? 'text-green-600' : 'text-red-600'}">
                            ${data.latest_data.change_pct.toFixed(2)}%
                        </span>
                    </div>
                </div>
            </div>

            <!-- 技术指标 -->
            <div class="mb-6 fade-in" style="animation-delay: 0.3s">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">技术指标</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <!-- Chandelier Exit Long -->
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h4 class="text-sm font-medium text-gray-700 mb-2">多头出场</h4>
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">当前值:</span>
                                <span class="text-sm font-medium">${data.indicators.chandelier_exit_long.current.toFixed(2)}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">前一值:</span>
                                <span class="text-sm font-medium">${data.indicators.chandelier_exit_long.previous.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Chandelier Exit Short -->
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h4 class="text-sm font-medium text-gray-700 mb-2">空头出场</h4>
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">当前值:</span>
                                <span class="text-sm font-medium">${data.indicators.chandelier_exit_short.current.toFixed(2)}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">前一值:</span>
                                <span class="text-sm font-medium">${data.indicators.chandelier_exit_short.previous.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- ZLSMA -->
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h4 class="text-sm font-medium text-gray-700 mb-2">ZLSMA</h4>
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">当前值:</span>
                                <span class="text-sm font-medium">${data.indicators.zlsma.current.toFixed(2)}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">前一值:</span>
                                <span class="text-sm font-medium">${data.indicators.zlsma.previous.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 当前信号 -->
            <div class="fade-in" style="animation-delay: 0.5s">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">当前信号</h3>
                <div class="p-4 bg-gray-50 rounded-lg">
                    <p class="text-gray-700">${data.signal}</p>
                </div>
            </div>

            <!-- 交易记录 -->
            <div class="mb-6 fade-in" style="animation-delay: 0.4s">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">交易记录</h3>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">交易号</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">开仓日期</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">开仓价格</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">平仓日期</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">净收益</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            ${data.trades.map(trade => `
                                <tr class="hover:bg-gray-50 transition-colors duration-200">
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${trade.trade_number}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${trade.open_date}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">¥${trade.open_price.toFixed(2)}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${trade.close_date}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm ${trade.net_pnl >= 0 ? 'text-green-600' : 'text-red-600'}">
                                        ¥${trade.net_pnl.toFixed(2)}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    // 显示回测结果并添加动画效果
    backtestResults.classList.remove('hidden');
    backtestResults.style.opacity = '0';
    backtestResults.style.transform = 'translateY(20px)';
    
    // 使用 requestAnimationFrame 确保过渡效果正常工作
    requestAnimationFrame(() => {
        backtestResults.style.transition = 'all 0.5s ease-in-out';
        backtestResults.style.opacity = '1';
        backtestResults.style.transform = 'translateY(0)';
    });
}

// 修改回测按钮的点击处理函数
async function runBacktest() {
    try {
        const symbol = document.getElementById('symbol').value;
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;

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
        handleBacktestResponse(data);
    } catch (error) {
        showError('回测请求失败: ' + error.message);
    }
}

// 添加错误显示函数
function showError(message) {
    const errorDiv = document.getElementById('error-message') || document.createElement('div');
    errorDiv.id = 'error-message';
    errorDiv.className = 'alert alert-danger mt-3';
    errorDiv.textContent = message;
    document.querySelector('#results-container').prepend(errorDiv);
}

// 在开始优化时显示股票名称
function startOptimization() {
    const symbol = document.getElementById('symbol').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    // 显示加载提示
    document.getElementById('loadingText').innerHTML = `正在优化分析 ${symbol}...`;
    document.getElementById('loadingSection').style.display = 'block';
    
    // ... 发送优化请求的代码 ...
}

// 处理优化结果时更新显示
function handleOptimizationResponse(response) {
    if (response.error) {
        // ... 错误处理代码 ...
    } else {
        document.getElementById('loadingText').innerHTML = 
            `${response.stockName}(${symbol}) 优化分析完成`;
        // ... 显示其他结果的代码 ...
    }
}

// 回测相关的函数也做类似修改
function startBacktest() {
    const symbol = document.getElementById('symbol').value;
    
    document.getElementById('loadingText').innerHTML = `正在回测分析 ${symbol}...`;
    document.getElementById('loadingSection').style.display = 'block';
    
    // ... 发送回测请求的代码 ...
}

function handleBacktestResponse(response) {
    if (!response.success) {
        // ... 错误处理代码 ...
    } else {
        document.getElementById('loadingText').innerHTML = 
            `${response.stockName}(${symbol}) 回测分析完成`;
        // ... 显示其他结果的代码 ...
    }
}

// 在开始新的优化或回测前清除之前的信息
document.getElementById('optimizeForm').addEventListener('submit', function(event) {
    event.preventDefault();
    optimize();
});