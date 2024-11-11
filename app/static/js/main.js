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
    
    // 清所有内容
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
    
    // 添加持仓分析按钮的事件监听器
    const portfolioButton = document.getElementById('runPortfolioAnalysis');
    if (portfolioButton) {
        portfolioButton.addEventListener('click', runPortfolioAnalysis);
    }
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

// 修改 switchTab 函数
function switchTab(tabId) {
    // 隐藏所有标签页内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });
    
    // 移除所有标签按钮的激活状态
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
        button.classList.remove('text-purple-600');
        button.classList.remove('border-b-2');
        button.classList.remove('border-purple-600');
        button.classList.add('text-gray-500');
    });
    
    // 显示选中的标签页内容
    const selectedTab = document.getElementById(tabId);
    if (selectedTab) {
        selectedTab.classList.remove('hidden');
    }
    
    // 激活对应的标签按钮
    const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
        activeButton.classList.add('text-purple-600');
        activeButton.classList.add('border-b-2');
        activeButton.classList.add('border-purple-600');
        activeButton.classList.remove('text-gray-500');
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

            <!-- 术指标 -->
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
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">平仓日</th>
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
            `${response.stockName}(${symbol}) 化分析完成`;
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

// 添加持仓分析相关的函数
function runPortfolioAnalysis(event) {
    event.preventDefault();
    
    const form = document.getElementById('portfolioForm');
    const button = document.getElementById('runPortfolioAnalysis');
    const resultsDiv = document.getElementById('portfolioResults');
    const timestampDiv = document.getElementById('analysisTimestamp');
    
    // 获取表单数据
    const formData = new FormData(form);
    const sendToWechat = document.getElementById('sendToWechat').checked;
    
    const analysisParams = {
        mode: formData.get('mode'),
        date: formData.get('date') || new Date().toISOString().split('T')[0],
        sendToWechat: sendToWechat  // 直接使用checkbox的checked状态
    };
    
    // 更新按钮状态加载动画
    button.disabled = true;
    button.innerHTML = `
        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        分析中...
    `;
    
    // 显示加载提示
    resultsDiv.innerHTML = `
        <div class="animate-pulse flex space-x-4 items-center justify-center py-12">
            <div class="rounded-full bg-purple-200 h-12 w-12"></div>
            <div class="flex-1 space-y-4 max-w-lg">
                <div class="h-4 bg-purple-200 rounded w-3/4"></div>
                <div class="space-y-2">
                    <div class="h-4 bg-purple-200 rounded"></div>
                    <div class="h-4 bg-purple-200 rounded w-5/6"></div>
                </div>
            </div>
        </div>
    `;
    
    fetch('/portfolio_analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(analysisParams)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let html = '<div class="grid gap-4">';
            data.results.forEach((result, index) => {
                // 解析交易数据
                const tradeData = parseTradeData(result.content);
                // 获取交易建议的样式
                const signalStyle = getSignalStyle(tradeData['交易建议']);
                
                html += `
                    <div class="bg-white rounded-lg shadow-md border border-gray-200 hover:shadow-lg transition-shadow duration-200">
                        <div class="p-4">
                            <div class="flex justify-between items-start mb-4">
                                <h3 class="text-lg font-semibold text-gray-800">${result.stock}</h3>
                                <span class="px-2 py-1 rounded-full text-sm ${parseFloat(tradeData['涨跌幅']) >= 0 ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100'}">
                                    ${tradeData['涨跌幅'] || '0.00%'}
                                </span>
                            </div>
                            
                            <!-- 交易建议部分 - 使用动态样式 -->
                            <div class="mb-4 ${signalStyle.bg} rounded-lg p-3 border ${signalStyle.border}">
                                <div class="flex items-center">
                                    <svg class="w-5 h-5 ${signalStyle.color} mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${signalStyle.icon}"/>
                                    </svg>
                                    <p class="text-sm font-medium ${signalStyle.color}">
                                        ${tradeData['交易建议'] || '无交易建议'}
                                    </p>
                                </div>
                            </div>
                            
                            <div class="grid grid-cols-2 gap-4 mb-4">
                                <div class="space-y-1">
                                    <p class="text-sm text-gray-500">日期</p>
                                    <p class="font-medium">${tradeData['日期'] || '-'}</p>
                                </div>
                                <div class="space-y-1">
                                    <p class="text-sm text-gray-500">收盘价</p>
                                    <p class="font-medium">${tradeData['收盘价'] || '-'}</p>
                                </div>
                            </div>
                            
                            <!-- 详情按钮 -->
                            <div class="mt-4 flex justify-center">
                                <button onclick="toggleDetails(${index})" 
                                        class="details-toggle-btn group w-full py-2 px-4 rounded-md
                                               bg-blue-50 hover:bg-blue-100 transition-all duration-200 
                                               flex items-center justify-center space-x-2">
                                    <span class="text-sm font-medium text-blue-600 group-hover:text-blue-700">
                                        <span class="details-text">查看详情</span>
                                    </span>
                                    <svg class="details-icon w-4 h-4 text-blue-600 group-hover:text-blue-700 transition-transform duration-200" 
                                         fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                                    </svg>
                                </button>
                            </div>
                            
                            <!-- 详情内容区域 -->
                            <div id="details-${index}" class="hidden mt-4">
                                <div class="border-t border-gray-100 pt-4">
                                    <div class="bg-gray-50 rounded-lg p-6 space-y-4">
                                        <!-- 价格区间信息 -->
                                        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                                <div class="text-sm text-gray-500 mb-1">最高价</div>
                                                <div class="font-medium text-gray-900">${tradeData['最高价'] || '-'}</div>
                                            </div>
                                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                                <div class="text-sm text-gray-500 mb-1">最低价</div>
                                                <div class="font-medium text-gray-900">${tradeData['最低价'] || '-'}</div>
                                            </div>
                                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                                <div class="text-sm text-gray-500 mb-1">开盘价</div>
                                                <div class="font-medium text-gray-900">${tradeData['开盘价'] || '-'}</div>
                                            </div>
                                        </div>

                                        <!-- 技术指标信息 -->
                                        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                                <div class="text-sm text-gray-500 mb-1">多头止损</div>
                                                <div class="font-medium text-gray-900">${tradeData['多头止损'] || '-'}</div>
                                            </div>
                                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                                <div class="text-sm text-gray-500 mb-1">空头止损</div>
                                                <div class="font-medium text-gray-900">${tradeData['空头止损'] || '-'}</div>
                                            </div>
                                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                                <div class="text-sm text-gray-500 mb-1">ZLSMA</div>
                                                <div class="font-medium text-gray-900">${tradeData['ZLSMA'] || '-'}</div>
                                            </div>
                                        </div>

                                        <!-- 策略参数 -->
                                        <div class="bg-white rounded-lg p-4 shadow-sm">
                                            <div class="text-sm text-gray-500 mb-2">策略参数</div>
                                            <div class="text-sm font-mono bg-gray-50 p-3 rounded">
                                                ${result.content.split('\n').find(line => line.includes('period:')) || '无参数信息'}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            resultsDiv.innerHTML = html;
            
            // 更新时间戳
            if (timestampDiv) {
                timestampDiv.textContent = `最后更新时间: ${data.timestamp}`;
            }
        } else {
            resultsDiv.innerHTML = `
                <div class="bg-red-50 border-l-4 border-red-500 p-4">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-red-700">分析失败: ${data.error}</p>
                        </div>
                    </div>
                </div>
            `;
        }
    })
    .catch(error => {
        resultsDiv.innerHTML = `
            <div class="bg-red-50 border-l-4 border-red-500 p-4">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <p class="text-sm text-red-700">请求失败: ${error}</p>
                    </div>
                </div>
            </div>
        `;
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            <span>运行分析</span>
        `;
    });
}

// 优化 toggleDetails 函数
function toggleDetails(index) {
    const detailsDiv = document.getElementById(`details-${index}`);
    const button = detailsDiv.previousElementSibling.querySelector('.details-toggle-btn');
    const icon = button.querySelector('.details-icon');
    const textSpan = button.querySelector('.details-text');
    
    if (detailsDiv.classList.contains('hidden')) {
        // 展开详情
        detailsDiv.classList.remove('hidden');
        requestAnimationFrame(() => {
            detailsDiv.style.animation = 'slideDown 0.3s ease-out forwards';
            detailsDiv.style.opacity = '1';
            icon.style.transform = 'rotate(180deg)';
            textSpan.textContent = '收起详情';
            button.classList.add('bg-blue-100');
        });
    } else {
        // 收起详情
        detailsDiv.style.animation = 'slideUp 0.3s ease-out forwards';
        detailsDiv.style.opacity = '0';
        icon.style.transform = 'rotate(0)';
        textSpan.textContent = '查看详情';
        button.classList.remove('bg-blue-100');
        setTimeout(() => {
            detailsDiv.classList.add('hidden');
        }, 280);
    }
}

// 在文档加载完成后初始化标签页
document.addEventListener('DOMContentLoaded', function() {
    // 添加签页切换事件监听器
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            switchTab(button.getAttribute('data-tab'));
        });
    });
    
    // 初始化表单事件监听器
    const portfolioForm = document.getElementById('portfolioForm');
    if (portfolioForm) {
        portfolioForm.addEventListener('submit', runPortfolioAnalysis);
        
        // 设置默认日期为今天
        const dateInput = document.getElementById('analysisDate');
        if (dateInput) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }
    }
    
    // 默认显示第一个标签页
    switchTab('optimization-tab');
});

// 添加动画相关的样式
const style = document.createElement('style');
style.textContent = `
    /* 原有的样式保持不变 */
    .tab-button.active {
        color: #7C3AED;
        border-bottom: 2px solid #7C3AED;
    }
    
    .tab-content {
        transition: all 0.3s ease-in-out;
    }
    
    .tab-content.hidden {
        display: none;
    }
    
    /* 添加新的动画样式 */
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideUp {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-8px);
        }
    }
    
    .details-icon {
        transition: transform 0.3s ease;
    }
    
    .details-toggle-btn:focus {
        outline: none;
        ring: 2px;
        ring-offset: 2px;
        ring-blue-500;
    }
    
    /* 优化动画效果 */
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideUp {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-8px);
        }
    }
    
    /* 添加卡片悬停效果 */
    .bg-white.rounded-lg.p-3.shadow-sm {
        transition: all 0.2s ease-in-out;
    }
    
    .bg-white.rounded-lg.p-3.shadow-sm:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
`;
document.head.appendChild(style);

// 修改数据解析函数
function parseTradeData(content) {
    console.log('原始内容:', content); // 调试日志
    const lines = content.split('\n');
    const data = {};
    
    lines.forEach(line => {
        if (line.includes(':')) {
            const [key, value] = line.split(':').map(str => str.trim());
            // 移除可能存在的全角冒号
            const cleanKey = key.replace('：', ':').trim();
            data[cleanKey] = value;
        }
    });
    
    console.log('解析结果:', data); // 调试日志
    return data;
}

// 添加交易建议样式配置函数
function getSignalStyle(signal) {
    if (!signal) return {
        color: 'text-gray-600',
        bg: 'bg-gray-50',
        border: 'border-gray-200',
        icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
    };

    if (signal.includes('买入') || signal.includes('加仓')) {
        return {
            color: 'text-green-600',
            bg: 'bg-green-50',
            border: 'border-green-200',
            icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
        };
    } else if (signal.includes('清仓') || signal.includes('卖出')) {
        return {
            color: 'text-red-600',
            bg: 'bg-red-50',
            border: 'border-red-200',
            icon: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z'
        };
    } else if (signal.includes('减仓')) {
        return {
            color: 'text-orange-600',
            bg: 'bg-orange-50',
            border: 'border-orange-200',
            icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'
        };
    } else if (signal.includes('观察') || signal.includes('等待')) {
        return {
            color: 'text-blue-600',
            bg: 'bg-blue-50',
            border: 'border-blue-200',
            icon: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z'
        };
    }

    // 默认样式
    return {
        color: 'text-gray-600',
        bg: 'bg-gray-50',
        border: 'border-gray-200',
        icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
    };
}

// 修改生成HTML的部分，更新交易建议的样式
data.results.forEach((result, index) => {
    const tradeData = parseTradeData(result.content);
    const signalStyle = getSignalStyle(tradeData['交易建议']);
    
    html += `
        <div class="bg-white rounded-lg shadow-md border border-gray-200 hover:shadow-lg transition-shadow duration-200">
            <div class="p-4">
                <!-- ... 其他内容保持不变 ... -->
                
                <!-- 交易建议部分 - 使用动态样式 -->
                <div class="mb-4 ${signalStyle.bg} rounded-lg p-3 border ${signalStyle.border}">
                    <div class="flex items-center">
                        <svg class="w-5 h-5 ${signalStyle.color} mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${signalStyle.icon}"/>
                        </svg>
                        <p class="text-sm font-medium ${signalStyle.color}">
                            ${tradeData['交易建议'] || '无交易建议'}
                        </p>
                    </div>
                </div>
                
                <!-- ... 其他内容保持不变 ... -->
            </div>
        </div>
    `;
});