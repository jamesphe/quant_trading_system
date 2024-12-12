// 在文件开头添加全局变量来跟踪排序状态
let currentSortColumn = null;
let sortStates = {};  // 用于跟踪每列的排序状态: null(不排序) -> 'asc' -> 'desc'

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

// 日期选择器类
class DatePicker {
    constructor(options) {
        this.options = {
            inputId: '',
            defaultDate: new Date(),
            minDate: null,
            maxDate: new Date(),
            onChange: null,
            format: 'YYYY-MM-DD',
            placeholder: '选择日期',
            ...options
        };
        
        this.init();
    }
    
    init() {
        const input = document.getElementById(this.options.inputId);
        if (!input) return;
        
        // 创建容器
        const container = document.createElement('div');
        container.className = 'date-picker-container relative';
        input.parentNode.replaceChild(container, input);
        
        // 创建显示输入框
        this.displayInput = document.createElement('input');
        this.displayInput.type = 'text';
        this.displayInput.className = `date-picker-input w-full h-12 px-4 py-2 
            text-base rounded-lg border border-gray-300 
            focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500
            hover:border-purple-300 transition-colors duration-200
            bg-white cursor-pointer select-none`;
        this.displayInput.placeholder = this.options.placeholder;
        this.displayInput.readOnly = true;
        
        // 创建原生日期输入框 - 修改这里
        this.hiddenInput = document.createElement('input');
        this.hiddenInput.type = 'date';
        this.hiddenInput.id = this.options.inputId;
        // 完全隐藏原生输入框
        this.hiddenInput.style.cssText = `
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        `;
        
        // 设置日期范围
        if (this.options.minDate) {
            this.hiddenInput.min = this.formatDate(this.options.minDate);
            this.displayInput.setAttribute('data-min', this.formatDisplayDate(this.options.minDate));
        }
        if (this.options.maxDate) {
            this.hiddenInput.max = this.formatDate(this.options.maxDate);
            this.displayInput.setAttribute('data-max', this.formatDisplayDate(this.options.maxDate));
        }
        
        // 添加日期图标
        const icon = document.createElement('div');
        icon.className = 'date-picker-icon absolute right-4 top-1/2 transform -translate-y-1/2 pointer-events-none';
        icon.innerHTML = `
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
        `;
        
        // 组装组件
        container.appendChild(this.displayInput);
        container.appendChild(this.hiddenInput);
        container.appendChild(icon);
        
        // 设置默认值
        if (this.options.defaultDate) {
            this.setDate(this.options.defaultDate);
        }
        
        // 绑定事件
        this.bindEvents();
    }
    
    bindEvents() {
        // 处理点击事件
        const handleClick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // 临时调整原生日期选择器的样式以接收点击
            this.hiddenInput.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                z-index: 2;
                -webkit-appearance: none;
            `;
            
            // 触发原生日期选择器
            this.hiddenInput.focus();
            this.hiddenInput.click();
        };
        
        // 同时监听 click 和 touch 事件
        this.displayInput.addEventListener('click', handleClick);
        this.displayInput.addEventListener('touchend', handleClick, { passive: false });
        
        // 处理日期变化
        this.hiddenInput.addEventListener('change', (e) => {
            const selectedDate = new Date(e.target.value);
            
            if (this.validateDateRange(selectedDate)) {
                this.setDate(selectedDate);
                
                if (typeof this.options.onChange === 'function') {
                    this.options.onChange(selectedDate, e.target.value);
                }
            } else {
                this.hiddenInput.value = this.formatDate(this.getDate() || this.options.defaultDate);
                showToast('请选择有效的日期范围', 'warning');
            }
            
            // 重置原生日期选择器样式为完全隐藏
            this.hiddenInput.style.cssText = `
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0, 0, 0, 0);
                white-space: nowrap;
                border: 0;
            `;
        });
        
        // 阻止默认的触摸行为
        this.displayInput.addEventListener('touchstart', (e) => {
            e.preventDefault();
        }, { passive: false });
    }
    
    validateDateRange(date) {
        if (this.options.minDate && date < this.options.minDate) {
            return false;
        }
        if (this.options.maxDate && date > this.options.maxDate) {
            return false;
        }
        return true;
    }
    
    setDate(date) {
        const formattedDate = this.formatDate(date);
        this.hiddenInput.value = formattedDate;
        this.displayInput.value = this.formatDisplayDate(date);
    }
    
    getDate() {
        return this.hiddenInput.value ? new Date(this.hiddenInput.value) : null;
    }
    
    formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    formatDisplayDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}年${month}月${day}日`;
    }
}

// 初始化所有日期选择器
function initializeDatePickers() {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    // 初始化所有日期选择器
    const datePickerConfigs = [
        {
            inputId: 'pickDate',
            defaultDate: today,  // 改为今天
            maxDate: today,      // 改为今天
            onChange: (date, dateString) => {
                console.log('每日选股日期已更改:', dateString);
                updateDailyPicks(dateString);
            }
        },
        {
            inputId: 'analysisDate',
            defaultDate: today,
            maxDate: today,
            onChange: (date, dateString) => {
                console.log('分析日期已更改:', dateString);
                updateAnalysis(dateString);
            }
        },
        {
            inputId: 'startDate',
            defaultDate: new Date(today.getFullYear() - 1, today.getMonth(), today.getDate()),
            maxDate: today,
            onChange: (date, dateString) => {
                console.log('开始日期已更改:', dateString);
            }
        },
        {
            inputId: 'endDate',
            defaultDate: today,
            maxDate: today,
            onChange: (date, dateString) => {
                console.log('结束日期已更改:', dateString);
            }
        },
        {
            inputId: 'targetDate',
            defaultDate: yesterday,  // 保留默认日期为昨天
            // 移除 maxDate 限制
            onChange: (date, dateString) => {
                console.log('目标股票日期已更改:', dateString);
                updateTargetStocks(dateString);
            }
        }
    ];
    
    // 初始化每个日期选择器
    datePickerConfigs.forEach(config => {
        new DatePicker(config);
    });
}

// 修改 DOMContentLoaded 事件处理函数
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    
    // 初始化标签页
    initializeTabs();
    
    // ���始化日期选择器
    initializeDatePickers();
    
    // 初始化其他组件
    initializeOtherComponents();
    
    // 绑定持仓分析按钮事件
    const portfolioForm = document.getElementById('portfolioForm');
    if (portfolioForm) {
        console.log('找到持仓分析表单，添加提交事件监听器');
        portfolioForm.addEventListener('submit', function(event) {
            console.log('��仓分析表单提交被触发');
            runPortfolioAnalysis(event);
        });
    } else {
        console.warn('未找到持仓分析表单');
    }
    
    // 初始化朗读功能
    SpeechController.init();
});

// 添加日期更新处理函数
function updateDailyPicks(date) {
    console.log('更新每日选股分析，���期:', date);
    // 如果需要自动触发分析，可以在这里调用 handleDailyPicks
    const form = document.getElementById('dailyPicksForm');
    if (form) {
        form.dispatchEvent(new Event('submit'));
    }
}

function updateAnalysis(date) {
    console.log('更新分析，日期:', date);
    // 这里可以添加分析日期变化后的处理逻辑
}

// 添加其他组件初始化函数
function initializeOtherComponents() {
    // 初始化表单提交事件
    const dailyPicksForm = document.getElementById('dailyPicksForm');
    if (dailyPicksForm) {
        dailyPicksForm.addEventListener('submit', handleDailyPicks);
    }
    
    // 初始化模型选择器
    const modelSelect = document.getElementById('analysisModel');
    if (modelSelect) {
        modelSelect.addEventListener('change', function() {
            console.log('选择的模型:', this.value);
        });
    }
}

// 确保 handleDailyPicks 函数正确处理日期
async function handleDailyPicks(event) {
    event.preventDefault();
    
    const pickDate = document.getElementById('pickDate').value;
    if (!pickDate) {
        showToast('请选择分析日期', 'warning');
        return;
    }
    
    // 将日期格式从 YYYY-MM-DD 转换为 YYYYMMDD
    const formattedDate = pickDate.replace(/-/g, '');
    const analysisModel = document.getElementById('analysisModel').value;
    const resultsDiv = document.getElementById('dailyPicksResults');
    const contentDiv = document.getElementById('dailyPicksContent');

    try {
        // 显示加载状态
        resultsDiv.classList.remove('hidden');
        contentDiv.innerHTML = `
            <div class="flex justify-center items-center py-8">
                <div class="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
                <div class="ml-3 text-gray-600">正在获取分析结果...</div>
            </div>
        `;

        const response = await fetch('/api/daily_picks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: formattedDate,
                model: analysisModel
            })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '获取分析结果失败');
        }

        // 显示后端返回的 HTML 内容
        contentDiv.innerHTML = data.content;
        
        // 添加样式
        contentDiv.classList.add('prose', 'max-w-none', 'mx-auto');
        
        // 应用自定义样式
        applyMarkdownStyles(contentDiv);

    } catch (error) {
        console.error('分析请求失败:', error);
        showToast(error.message, 'error');
        contentDiv.innerHTML = `
            <div class="text-red-500 text-center py-4">
                ${error.message}
            </div>
        `;
    }
}

// 修改日期选择器初始化函数
function initializeDatePicker(today) {
    const pickDateInput = document.getElementById('pickDate');
    if (pickDateInput) {
        // 设置默认值为今天
        const defaultDate = today.toISOString().split('T')[0];
        pickDateInput.value = defaultDate;
        pickDateInput.max = defaultDate; // 限制最大日期为今天
        
        // 添加日期变化事件监听
        pickDateInput.addEventListener('change', function(e) {
            console.log('日期已更改:', this.value);
            // 这里可以添加日期变化后的其他处理逻辑
        });
        
        // 添加点击事件监听器
        pickDateInput.addEventListener('click', function(e) {
            // 确保在移动设备上也能正常工作
            if (this.type === 'date') {
                return; // 原生日期选择器会自动打开
            }
            // 对于不支持原生日期器的设备，可以在这里添加自定义日期选择器
        });
    }
}

// 格式化日期为YYYY-MM-DD
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// 格式化显示日为YYYY年MM月DD日
function formatDisplayDate(dateStr) {
    const date = new Date(dateStr);
    return `${date.getFullYear()}年${(date.getMonth() + 1).toString().padStart(2, '0')}月${date.getDate().toString().padStart(2, '0')}日`;
}

// 修改初始化标签页的函数
function initializeTabs() {
    // 为所有标签按钮添加点击事件
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            console.log('Tab button clicked:', tabId); // 调试日志
            switchTab(tabId);
        });
    });
    
    // 默认显示第一个标签页
    const firstTab = document.querySelector('.tab-button');
    if (firstTab) {
        const defaultTabId = firstTab.getAttribute('data-tab');
        switchTab(defaultTabId);
    }
}

// 修改 switchTab ���数
function switchTab(tabId) {
    console.log('Switching to tab:', tabId); // 调试日志
    
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
    const activeButton = document.querySelector(`button[data-tab="${tabId}"]`);
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

    // 显示加载动画，不隐藏结果区域
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

// 修改 handleAnalysis 函数
async function handleAnalysis(event) {
    event.preventDefault();
    
    // 获取必需的DOM元素
    const symbolInput = document.getElementById('analysisSymbol');
    const modelSelect = document.getElementById('modelSelect');
    const additionalInfoInput = document.getElementById('additionalInfo');
    const resultsDiv = document.getElementById('analysisResults');
    const contentDiv = document.getElementById('analysisContent');
    
    // 检查必需的元素是否存在
    if (!symbolInput || !modelSelect || !resultsDiv || !contentDiv) {
        showToast('页面元素加载失败，请刷新页面重试', 'error');
        return;
    }

    const symbol = symbolInput.value;
    const model = modelSelect.value;
    const additionalInfo = additionalInfoInput ? additionalInfoInput.value.trim() : '';
    
    // 验证输入
    if (!symbol) {
        showToast('请输入股票代码', 'warning');
        return;
    }
    
    // 在分析开始前停止朗读
    if (typeof SpeechController !== 'undefined') {
        SpeechController.stop();
    }

    const submitButton = event.target.querySelector('button[type="submit"]');
    if (!submitButton) {
        showToast('提交按钮未找到，请刷新页面重试', 'error');
        return;
    }

    // 更新按钮状态
    submitButton.disabled = true;
    const originalButtonContent = submitButton.innerHTML;
    submitButton.innerHTML = `
        <div class="flex items-center justify-center space-x-2">
            <div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
            <span>分析中...</span>
        </div>
    `;
    
    try {
        // 显示结果区域和加载提示
        resultsDiv.classList.remove('hidden');
        contentDiv.innerHTML = `
            <div class="flex flex-col items-center justify-center py-8 space-y-4">
                <div class="relative">
                    <div class="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
                    <div class="absolute top-0 left-0 h-12 w-12 rounded-full border-4 border-indigo-200 opacity-20"></div>
                </div>
                <div class="text-center">
                    <p class="text-lg font-medium text-gray-600">AI正在分析 ${symbol}</p>
                    <p class="text-sm text-gray-500 mt-2">这可能需要一些时间...</p>
                </div>
            </div>
        `;

        const response = await fetch('/analyze_stock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                model: model,
                additionalInfo: additionalInfo
            })
        });

        // 创建EventSource来处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let analysisText = '';
        let isFirstChunk = true;
        let hasReceivedAnalysis = false;

        while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.error) {
                            showToast(data.error, 'error');
                            contentDiv.innerHTML = `
                                <div class="flex items-center p-4 bg-red-50 rounded-lg">
                                    <svg class="w-6 h-6 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                    </svg>
                                    <span class="text-red-700">${data.error}</span>
                                </div>
                            `;
                            return;
                        }
                        
                        const content = data.content || '';
                        
                        // ���查���否是提示信息
                        if (content.includes('正在获取股票数据') || content.includes('正在进行分析')) {
                            if (!hasReceivedAnalysis) {
                                contentDiv.innerHTML = `
                                    <div class="flex items-center justify-center space-x-2 text-gray-600">
                                        <div class="animate-spin rounded-full h-4 w-4 border-2 border-indigo-500 border-t-transparent"></div>
                                        <span>${content}</span>
                                    </div>
                                `;
                            }
                            continue;
                        }
                        
                        // 收到实际分析内容
                        if (!hasReceivedAnalysis) {
                            hasReceivedAnalysis = true;
                            contentDiv.innerHTML = `
                                <div class="chat-message-container fade-in">
                                    <div class="chat-message">
                                        <div class="markdown-content"></div>
                                    </div>
                                </div>
                            `;
                        }
                        
                        // 累积文本内容
                        analysisText += content;
                        
                        // 更新显示
                        const markdownContent = contentDiv.querySelector('.markdown-content');
                        if (markdownContent) {
                            markdownContent.innerHTML = marked.parse(analysisText);
                            
                            // 添加样式
                            applyMarkdownStyles(markdownContent);
                            
                            // 平滑滚�����到底部
                            smoothScrollToBottom(contentDiv);
                            
                            // 添加打字机效果的CSS类
                            markdownContent.classList.add('typing-effect');
                        }
                        
                    } catch (e) {
                        console.warn('解析数据块失败:', e);
                    }
                }
            }
        }
        
    } catch (error) {
        showToast(error.message, 'error');
        contentDiv.innerHTML = `
            <div class="flex items-center p-4 bg-red-50 rounded-lg">
                <svg class="w-6 h-6 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span class="text-red-700">请求失败: ${error.message}</span>
            </div>
        `;
    } finally {
        // 恢复按钮状态
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonContent;
        }
    }
}

// 修改 applyMarkdownStyles 函数
function applyMarkdownStyles(element) {
    // 添加容器类
    element.classList.add('markdown-content', 'prose', 'prose-indigo', 'max-w-none');
    
    // 处理代码块
    const preTags = element.getElementsByTagName('pre');
    Array.from(preTags).forEach(pre => {
        // 添加代码块样式
        pre.classList.add('relative');
        
        // 如包含表格数据，添加水平滚动
        if (pre.textContent.includes('|')) {
            pre.classList.add('overflow-x-auto');
        }
    });
    
    // 处理表格
    const tables = element.getElementsByTagName('table');
    Array.from(tables).forEach(table => {
        table.classList.add('table-auto', 'border-collapse', 'w-full');
        
        // 添加表格容器以支持水平滚动
        const wrapper = document.createElement('div');
        wrapper.classList.add('overflow-x-auto');
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
    
    // 处理交易建议部分
    const headers = element.getElementsByTagName('h2');
    Array.from(headers).forEach(header => {
        if (header.textContent.includes('交易建议')) {
            const nextElement = header.nextElementSibling;
            if (nextElement) {
                nextElement.classList.add('bg-indigo-50', 'p-4', 'rounded-lg', 'border', 'border-indigo-100');
            }
        }
    });
    
    // 高亮重要信息
    const paragraphs = element.getElementsByTagName('p');
    Array.from(paragraphs).forEach(p => {
        if (p.textContent.includes('建议') || 
            p.textContent.includes('注意') || 
            p.textContent.includes('风险')) {
            p.classList.add('highlight');
        }
    });

    // 处理链接
    const links = element.getElementsByTagName('a');
    Array.from(links).forEach(link => {
        link.classList.add('text-indigo-600', 'hover:text-indigo-800', 'hover:underline');
        // 如果是外部链接，添加新窗口打开
        if (link.hostname !== window.location.hostname) {
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        }
    });

    // 处理列表
    const lists = element.querySelectorAll('ul, ol');
    lists.forEach(list => {
        list.classList.add('space-y-1', 'my-4');
        const items = list.getElementsByTagName('li');
        Array.from(items).forEach(item => {
            item.classList.add('text-gray-700');
        });
    });

    // 处理引用块
    const blockquotes = element.getElementsByTagName('blockquote');
    Array.from(blockquotes).forEach(quote => {
        quote.classList.add(
            'border-l-4',
            'border-indigo-200',
            'pl-4',
            'py-2',
            'my-4',
            'text-gray-600',
            'bg-indigo-50',
            'rounded-r-lg'
        );
    });

    // 处理代码
    const inlineCodes = element.querySelectorAll('code:not(pre code)');
    inlineCodes.forEach(code => {
        code.classList.add(
            'bg-gray-100',
            'text-indigo-600',
            'rounded',
            'px-1.5',
            'py-0.5',
            'text-sm',
            'font-mono'
        );
    });
}

function smoothScrollToBottom(element) {
    const scrollHeight = element.scrollHeight;
    const currentScroll = element.scrollTop;
    const targetScroll = scrollHeight - element.clientHeight;
    const scrollDistance = targetScroll - currentScroll;
    
    if (scrollDistance > 0) {
        const duration = 300;
        const startTime = performance.now();
        
        function scroll(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            element.scrollTop = currentScroll + scrollDistance * easeInOutCubic(progress);
            
            if (progress < 1) {
                requestAnimationFrame(scroll);
            }
        }
        
        requestAnimationFrame(scroll);
    }
}

function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg transform transition-all duration-300 ease-in-out z-50 ${
        type === 'error' ? 'bg-red-500' :
        type === 'warning' ? 'bg-yellow-500' :
        type === 'success' ? 'bg-green-500' :
        'bg-blue-500'
    } text-white`;
    
    toast.innerHTML = `
        <div class="flex items-center space-x-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="${
                          type === 'error' ? 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' :
                          type === 'warning' ? 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' :
                          type === 'success' ? 'M5 13l4 4L19 7' :
                          'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
                      }"/>
            </svg>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // 添加入场动画
    requestAnimationFrame(() => {
        toast.style.transform = 'translateX(0)';
        toast.style.opacity = '1';
    });
    
    // 3秒后移除
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function displayBacktestResults(data) {
    console.log('显示回测果:', data);
    
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
                        <span class="metric-label">收益</span>
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
                        <h4 class="text-sm font-medium text-gray-700 mb-2">多头出</h4>
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
                    <p class="text-gray-700">${data.signal} （ ${data.reason} ）</p>
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
    
    // 显回测结果并添加动画效果
    backtestResults.classList.remove('hidden');
    backtestResults.style.opacity = '0';
    backtestResults.style.transform = 'translateY(20px)';
    
    // 使用 requestAnimationFrame 保过渡效果正常工作
    requestAnimationFrame(() => {
        backtestResults.style.transition = 'all 0.5s ease-in-out';
        backtestResults.style.opacity = '1';
        backtestResults.style.transform = 'translateY(0)';
    });
}

// 修改回按钮的点击理函数
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

// 添加错误显示函
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

// 处理优化结果时新显示
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
    
    // ... 发送回测请求代码 ...
}

function handleBacktestResponse(response) {
    if (!response.success) {
        // ... 错误处理代 ...
    } else {
        document.getElementById('loadingText').innerHTML = 
            `${response.stockName}(${symbol}) 回测分析完`;
        // ... 显示其他结果的代码 ...
    }
}

// 在开始新的优化或回测前清除之前的信息
document.getElementById('optimizeForm').addEventListener('submit', function(event) {
    event.preventDefault();
    optimize();
});

// 添加持仓析相关的函数
function runPortfolioAnalysis(event) {
    event.preventDefault();
    
    const form = document.getElementById('portfolioForm');
    const button = document.getElementById('runPortfolioAnalysis');
    const resultsDiv = document.getElementById('portfolioResults');
    
    if (!form || !button || !resultsDiv) {
        showToast('系统错误：找不到必要的页面元素', 'error');
        return;
    }
    
    // 获取表数据
    const formData = new FormData(form);
    const sendToWechat = document.getElementById('sendToWechat').checked;
    
    const analysisParams = {
        mode: formData.get('mode') || 'portfolio',
        date: formData.get('date') || new Date().toISOString().split('T')[0],
        sendToWechat: sendToWechat
    };
    
    // 更新按钮状态和显示加载动画
    button.disabled = true;
    const originalButtonContent = button.innerHTML;
    button.innerHTML = `
        <div class="flex items-center justify-center space-x-2">
            <div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
            <span>分析中...</span>
        </div>
    `;
    
    // 显��加载示
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
    
    // 发送请求
    fetch('/portfolio_analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(analysisParams)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const html = displayPortfolioResults(data);
            resultsDiv.innerHTML = html;
            showToast('分析完成', 'success');
        } else {
            throw new Error(data.error || '分析失败，未知错误');
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
                        <p class="text-sm text-red-700">分析失败: ${error.message}</p>
                    </div>
                </div>
            </div>
        `;
        showToast('分析失败: ' + error.message, 'error');
    })
    .finally(() => {
        // 恢复按状态
        button.disabled = false;
        button.innerHTML = originalButtonContent;
    });
}

// 添加切换到技术分析面的函数
function switchToTechnicalAnalysis(stockCode) {
    // 切换到参数优化标签页
    switchTab('optimization-tab');
    
    // 设置股票代码
    document.getElementById('symbol').value = stockCode;
    
    // 设默认的日期范围（比如过去一年）
    const today = new Date();
    const lastYear = new Date();
    lastYear.setFullYear(today.getFullYear() - 1);
    
    document.getElementById('startDate').value = lastYear.toISOString().split('T')[0];
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    
    // 自动��发优化
    document.getElementById('optimizeForm').dispatchEvent(new Event('submit'));
}

// 添加切换到AI分析页面的函数
function switchToAIAnalysis(stockCode) {
    // 切换到个股分析标签页
    switchTab('analysis-tab');
    
    // 设置股票代码
    document.getElementById('analysisSymbol').value = stockCode;
    
    // 自动触发分析
    document.getElementById('analysisForm').dispatchEvent(new Event('submit'));
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
    console.log('DOM loaded, initializing tabs...'); // 调试日志
    initializeTabs();
    
    // 其他初始化代码...
    
    // 初始化朗读功能
    SpeechController.init();
});

// 添加动画相关的样式
const style = document.createElement('style');
style.textContent = `
    /* 原有的样式持不变 */
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
    
    /* 添卡片悬停效果 */
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

// 修改 displayPortfolioResults 函数
function displayPortfolioResults(data) {
    let html = '<div class="grid gap-4">';
    
    data.results.forEach((result, index) => {
        const tradeData = parseTradeData(result.content);
        const signalStyle = getSignalStyle(tradeData['交易建议']);
        
        // 从股票名称中提取股票代码
        const stockCode = result.stock.match(/（([^)]+)）/)?.[1] || '';
        
        html += `
            <div class="bg-white rounded-lg shadow-md border border-gray-200 hover:shadow-lg transition-shadow duration-200">
                <div class="p-4">
                    <!-- 标题行：股票名���和分析按钮 -->
                    <div class="flex flex-col sm:flex-row sm:items-center space-y-3 sm:space-y-0 sm:justify-between mb-4">
                        <div class="flex items-center space-x-2">
                            <h3 class="text-lg font-semibold text-gray-800">${result.stock}</h3>
                            <span class="px-2 py-1 rounded-full text-sm ${parseFloat(tradeData['涨跌幅']) >= 0 ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100'}">
                                ${tradeData['涨跌幅'] || '0.00%'}
                            </span>
                        </div>
                        <!-- 分析按钮组 -->
                        <div class="flex space-x-2 w-full sm:w-auto">
                            <button onclick="switchToTechnicalAnalysis('${stockCode}')"
                                    class="flex-1 sm:flex-none h-10 px-3 sm:px-2.5 py-2 bg-blue-500 hover:bg-blue-600 
                                           text-white text-sm font-medium rounded-lg transition-colors duration-200 
                                           flex items-center justify-center space-x-1">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                                </svg>
                                <span>技术分析</span>
                            </button>
                            <button onclick="switchToAIAnalysis('${stockCode}')"
                                    class="flex-1 sm:flex-none h-10 px-3 sm:px-2.5 py-2 bg-purple-500 hover:bg-purple-600 
                                           text-white text-sm font-medium rounded-lg transition-colors duration-200 
                                           flex items-center justify-center space-x-1">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                          d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                </svg>
                                <span>AI分析</span>
                            </button>
                        </div>
                    </div>
                    
                    <!-- 交易建议部分 -->
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
                    
                    <!-- 详情按 -->
                    <div class="mt-4">
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
                                        <div class="text-sm text-gray-500 mb-1">最低��</div>
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
    return html;
}

// 处理每日选股表单提交
async function handleDailyPicks(event) {
    event.preventDefault();
    
    const pickDate = document.getElementById('pickDate').value;
    if (!pickDate) {
        showToast('请选择分析日期', 'warning');
        return;
    }
    
    // 将日期格式从 YYYY-MM-DD 转换为 YYYYMMDD
    const formattedDate = pickDate.replace(/-/g, '');
    const analysisModel = document.getElementById('analysisModel').value;
    const resultsDiv = document.getElementById('dailyPicksResults');
    const contentDiv = document.getElementById('dailyPicksContent');

    try {
        // 显示加载状态
        resultsDiv.classList.remove('hidden');
        contentDiv.innerHTML = `
            <div class="flex justify-center items-center py-8">
                <div class="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
                <div class="ml-3 text-gray-600">正在获取分析结果...</div>
            </div>
        `;

        const response = await fetch('/api/daily_picks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: formattedDate,
                model: analysisModel
            })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '获取分析结果失败');
        }

        // 显示后端返回的 HTML 内容
        contentDiv.innerHTML = data.content;
        
        // 添加样式
        contentDiv.classList.add('prose', 'max-w-none', 'mx-auto');
        
        // 应用自定义样式
        applyMarkdownStyles(contentDiv);

    } catch (error) {
        console.error('分析请求失败:', error);
        showToast(error.message, 'error');
        contentDiv.innerHTML = `
            <div class="text-red-500 text-center py-4">
                ${error.message}
            </div>
        `;
    }
}

// 添加日期选择器的事件监听
document.addEventListener('DOMContentLoaded', function() {
    // 设置日期选择器的默认值为今天
    const pickDate = document.getElementById('pickDate');
    if (pickDate) {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        pickDate.value = `${year}-${month}-${day}`;
        
        // 添加日期变化事件监听
        pickDate.addEventListener('change', function() {
            console.log('选择的日期:', this.value);
        });
    }

    // 为表单添加提交事件监听
    const dailyPicksForm = document.getElementById('dailyPicksForm');
    if (dailyPicksForm) {
        dailyPicksForm.addEventListener('submit', handleDailyPicks);
    }
});

// Toast 提示函数
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300 ${
        type === 'error' ? 'bg-red-500' : 'bg-green-500'
    } text-white`;
    toast.style.animation = 'slideIn 0.3s ease-out';
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// 修改 SpeechController 对象，使用讯飞语音合成
const SpeechController = {
    isReading: false,
    isPaused: false,  // 添加暂停状态
    audio: null,
    currentChunkIndex: 0,
    chunks: [],
    
    // 初始化朗读功能
    init() {
        console.log('初始化朗读功能...');
        const readBtn = document.getElementById('readAnalysisBtn');
        if (readBtn) {
            console.log('找到朗读按钮');
            readBtn.addEventListener('click', () => {
                console.log('朗读按钮被点击');
                if (this.isReading) {
                    this.stop();
                    this.isPaused = true;  // 设置暂停状态
                } else if (this.isPaused && this.chunks.length > 0) {
                    // 如果是暂停状态且有未读完的内容，继续朗读
                    this.isReading = true;
                    this.updateButtonState();
                    this.readNextChunk();
                } else {
                    // 重新开始朗读
                    this.isPaused = false;
                    this.read();
                }
            });
        }
    },
    
    // 开始朗读
    async read() {
        console.log('尝试开始朗读...');
        const content = document.getElementById('analysisContent');
        if (!content) {
            console.error('未找到内容元素');
            return;
        }
        
        // 获取并处理文本内容
        let textContent = content.innerText;
        if (!textContent) {
            console.warn('没有可朗读的内容');
            return;
        }
        
        // 处理文本内容
        textContent = textContent
            .replace(/\n+/g, '。')
            .replace(/↵/g, '。')
            .replace(/===+/g, '')
            .replace(/\s+/g, ' ')
            .replace(/。+/g, '。')
            .trim();
        
        // 分段处理文本
        this.chunks = [];
        while (textContent.length > 0) {
            let endIndex = 1000;
            if (textContent.length > 1000) {
                const lastPeriod = textContent.substring(0, 1000).lastIndexOf('。');
                endIndex = lastPeriod > 0 ? lastPeriod + 1 : 1000;
            }
            this.chunks.push(textContent.substring(0, endIndex));
            textContent = textContent.substring(endIndex);
        }
        
        // 开始朗读第一段
        this.currentChunkIndex = 0;
        this.isReading = true;
        this.updateButtonState(); // 立即更新按钮状态为"停止朗读"
        await this.readNextChunk();
    },
    
    // 朗读下一段
    async readNextChunk() {
        if (!this.isReading || this.currentChunkIndex >= this.chunks.length) {
            this.isReading = false;
            this.updateButtonState();
            return;
        }
        
        try {
            const chunk = this.chunks[this.currentChunkIndex];
            
            // 请求讯飞语音合成
            const response = await fetch('/api/xfyun/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: chunk })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '语音合成请求失败');
            }
            
            // 获取音频blob
            const blob = await response.blob();
            if (blob.size === 0) {
                throw new Error('获取到的音频数据为空');
            }
            
            // 如果有正在播放的音频，先停止
            if (this.audio) {
                this.audio.pause();
                URL.revokeObjectURL(this.audio.src);
                this.audio = null;
            }
            
            // 创建新的音频实例
            const audioUrl = URL.createObjectURL(blob);
            this.audio = new Audio(audioUrl);
            
            // 设置事件处理
            this.audio.onplay = () => {
                this.isReading = true;
                this.updateButtonState(); // 确保播放开始时更新按钮状态
            };
            
            this.audio.onended = async () => {
                URL.revokeObjectURL(audioUrl);
                this.audio = null;
                this.currentChunkIndex++;
                if (this.currentChunkIndex < this.chunks.length) {
                    await this.readNextChunk();
                } else {
                    this.isReading = false;
                    this.updateButtonState(); // 所有段落朗读完成后更新按钮状态
                }
            };
            
            this.audio.onerror = (e) => {
                console.error('音频播放错误:', e);
                URL.revokeObjectURL(audioUrl);
                this.audio = null;
                this.isReading = false;
                this.updateButtonState(); // 发生错误时更新按钮状态
                showToast('播放音频时发生错误', 'error');
            };
            
            // 开始播放
            await this.audio.play();
            
        } catch (error) {
            console.error('语音合成失败:', error);
            showToast(error.message || '语音合成失败，请稍后重试', 'error');
            this.isReading = false;
            this.updateButtonState(); // 发生错误时更新按钮状态
        }
    },
    
    // 停止朗读
    stop() {
        console.log('停止朗读');
        this.isReading = false;
        if (this.audio) {
            this.audio.pause();
            this.audio.currentTime = 0;
            URL.revokeObjectURL(this.audio.src);
            this.audio = null;
        }
        // 不清空 chunks 和 currentChunkIndex，以支持继续朗读
        this.updateButtonState();
    },
    
    // 更新按钮状态
    updateButtonState() {
        const readBtn = document.getElementById('readAnalysisBtn');
        if (!readBtn) {
            console.warn('��找到朗读按钮，无法更新状态');
            return;
        }
        
        if (this.isReading) {
            readBtn.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/>
                </svg>
                <span class="text-sm font-medium">停止朗读</span>
            `;
            readBtn.classList.remove('bg-indigo-50', 'hover:bg-indigo-100', 'text-indigo-600');
            readBtn.classList.add('bg-red-50', 'hover:bg-red-100', 'text-red-600');
        } else if (this.isPaused && this.chunks.length > 0) {
            readBtn.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span class="text-sm font-medium">继续朗读</span>
            `;
            readBtn.classList.remove('bg-red-50', 'hover:bg-red-100', 'text-red-600');
            readBtn.classList.add('bg-green-50', 'hover:bg-green-100', 'text-green-600');
        } else {
            readBtn.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                </svg>
                <span class="text-sm font-medium">朗读分析</span>
            `;
            readBtn.classList.remove('bg-red-50', 'hover:bg-red-100', 'text-red-600');
            readBtn.classList.remove('bg-green-50', 'hover:bg-green-100', 'text-green-600');
            readBtn.classList.add('bg-indigo-50', 'hover:bg-indigo-100', 'text-indigo-600');
        }
    }
};


// 处理目标股票表单提交
async function handleTargetStocks(event) {
    event.preventDefault();
    
    const date = document.getElementById('targetDate').value;
    if (!date) {
        showToast('请选择日期', 'warning');
        return;
    }
    
    await updateTargetStocks(date);
}

// 修改 displayTargetStocks 函数，添加原始索引
function displayTargetStocks(stocks) {
    const tbody = document.getElementById('targetStocksBody');
    tbody.innerHTML = '';
    
    // 重置排序状态（移除重复声明）
    currentSortColumn = null;
    sortStates = {};
    
    stocks.forEach((stock, index) => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 transition-colors duration-200';
        row.dataset.originalIndex = index;  // 保存原始顺序
        
        // 修改涨跌幅的颜色逻辑：红色表示上涨，绿色表示下跌
        const changeValue = parseFloat(stock['最新涨跌幅'] || 0);
        const changeColor = changeValue >= 0 ? 'text-red-600' : 'text-green-600';
        
        // 处理最佳胜率和最佳回报的颜色
        const winRateValue = parseFloat(stock['最佳胜率'] || 0);
        const returnValue = parseFloat(stock['最佳回报'] || 0);
        
        // 根据胜率值设置颜色
        const winRateColor = winRateValue >= 0.6 ? 'text-green-600' : 
                           winRateValue >= 0.5 ? 'text-blue-600' : 'text-red-600';
                           
        // 根据回报值设置颜色
        const returnColor = returnValue >= 0.2 ? 'text-green-600' : 
                          returnValue >= 0 ? 'text-blue-600' : 'text-red-600';
        
        // 确保价格显示正确
        const price = parseFloat(stock['最新价格']);
        const priceDisplay = isNaN(price) ? '-' : price.toFixed(2);
        
        row.innerHTML = `
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm">
                <a href="javascript:void(0)" 
                   onclick="switchToTechnicalAnalysis('${stock['股票代码']}')"
                   class="text-blue-600 hover:text-blue-800 hover:underline">
                    ${stock['股票代码']}
                </a>
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm">
                <a href="javascript:void(0)" 
                   onclick="switchToAIAnalysis('${stock['股票代码']}')"
                   class="text-purple-600 hover:text-purple-800 hover:underline">
                    ${stock['股票名称']}
                </a>
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-500">
                ${stock['所属行业'] || '-'}
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-900">
                ${priceDisplay}
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm ${changeColor}">
                ${changeValue >= 0 ? '+' : ''}${changeValue.toFixed(2)}%
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-900">
                ${Number(stock['换手率']).toFixed(2)}%
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm ${winRateColor} font-medium">
                ${(winRateValue * 100).toFixed(2)}%
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm ${returnColor} font-medium">
                ${(returnValue * 100 >= 0 ? '+' : '')}${(returnValue * 100).toFixed(2)}%
            </td>
            <td class="hidden sm:table-cell px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-900">
                ${Number(stock['夏普比率']).toFixed(2)}
            </td>
        `;
        
        tbody.appendChild(row);
    });
    
    // 更新所有表头的排序图标
    document.querySelectorAll('th[data-sort]').forEach(th => {
        const icon = th.querySelector('.sort-icon');
        const columnName = th.getAttribute('data-sort');
        if (columnName === '股票代码') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '股票名称') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '所属行业') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '最新价格') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '最新涨跌幅') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '换手率') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '最佳胜率') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '最佳回报') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else if (columnName === '夏普比率') {
            switch (sortStates[columnName]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        }
    });
}

// 修改 sortStocks 函数中的列索引获取逻辑
function getColumnIndex(column) {
    const columnMap = {
        '股票代码': 0,
        '股票名称': 1,
        '所属行业': 2,
        '最新价格': 3,
        '最新涨跌幅': 4,
        '换手率': 5,
        '最佳胜率': 6,
        '最佳回报': 7,
        '夏普比率': 8
    };
    return columnMap[column] || 0;
}

// 在文档加载完成后初始化事件监听
document.addEventListener('DOMContentLoaded', function() {
    // 初始化目标股票表单提交事件
    const targetStocksForm = document.getElementById('targetStocksForm');
    if (targetStocksForm) {
        targetStocksForm.addEventListener('submit', handleTargetStocks);
    }
    
    // 初始化表头排序点击事件
    document.querySelectorAll('th[data-sort]').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.getAttribute('data-sort');
            sortStocks(column);
        });
    });
});

// 添加更新价格的处理函数
async function updatePrices() {
    const date = document.getElementById('targetDate').value;  // 已经是 YYYY-MM-DD 格式
    if (!date) {
        showToast('请选择日期', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/update_prices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: date  // 直接使用 YYYY-MM-DD 格式
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error);
        }
        
        showToast('价格更新成功', 'success');
        
        // 重新加载数据
        await handleTargetStocks(new Event('submit'));
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 在文档加载完成后添加事件监听
document.addEventListener('DOMContentLoaded', function() {
    // ... 现有的初始化代码 ...
    
    // 添加更新价格按钮的事件监听
    const updatePricesBtn = document.getElementById('updatePricesBtn');
    if (updatePricesBtn) {
        updatePricesBtn.addEventListener('click', updatePrices);
    }
});

// 在 SpeechController 对象后添加以下代码

// 复制功能处理
document.addEventListener('DOMContentLoaded', function() {
    const copyBtn = document.getElementById('copyAnalysisBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', async function() {
            const content = document.getElementById('analysisContent');
            if (!content) {
                showToast('未找到分析内容', 'error');
                return;
            }

            try {
                const textContent = content.innerText;
                
                // 首先尝试使用 navigator.clipboard API
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(textContent);
                } else {
                    // 后备方案：创建临时文本区域
                    const textArea = document.createElement('textarea');
                    textArea.value = textContent;
                    
                    // 防止滚动到底部
                    textArea.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 2em;
                        height: 2em;
                        padding: 0;
                        border: none;
                        outline: none;
                        boxShadow: none;
                        background: transparent;
                    `;
                    
                    document.body.appendChild(textArea);
                    
                    if (navigator.userAgent.match(/ipad|iphone/i)) {
                        // iOS 设备特殊处理
                        textArea.contentEditable = true;
                        textArea.readOnly = false;
                        
                        const range = document.createRange();
                        range.selectNodeContents(textArea);
                        
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                        textArea.setSelectionRange(0, 999999);
                    } else {
                        // 其他设备
                        textArea.select();
                    }
                    
                    try {
                        document.execCommand('copy');
                    } catch (err) {
                        console.error('复制失败:', err);
                        throw new Error('复制命令执行失败');
                    } finally {
                        document.body.removeChild(textArea);
                    }
                }
                
                // 更新按钮状态以提供视觉反馈
                const originalContent = this.innerHTML;
                this.innerHTML = `
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M5 13l4 4L19 7"/>
                    </svg>
                    <span class="text-sm font-medium">已复制</span>
                `;
                this.classList.remove('bg-green-50', 'hover:bg-green-100', 'text-green-600');
                this.classList.add('bg-green-100', 'text-green-700');
                
                // 显示成功提示
                showToast('分析内容已复制到剪贴板', 'success');
                
                // 2秒后恢复按钮原始状态
                setTimeout(() => {
                    this.innerHTML = originalContent;
                    this.classList.remove('bg-green-100', 'text-green-700');
                    this.classList.add('bg-green-50', 'hover:bg-green-100', 'text-green-600');
                }, 2000);
                
            } catch (err) {
                console.error('复制失败:', err);
                showToast('复失败，请重试', 'error');
            }
        });
    }
});

// 在文件末尾添加 updateTargetStocks 函数
async function updateTargetStocks(date) {
    try {
        // 显示加载状态
        const tbody = document.getElementById('targetStocksBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="px-6 py-4 text-center">
                    <div class="flex justify-center items-center space-x-3">
                        <div class="animate-spin rounded-full h-5 w-5 border-2 border-purple-500 border-t-transparent"></div>
                        <span class="text-gray-600">正在获取数据...</span>
                    </div>
                </td>
            </tr>
        `;

        const response = await fetch('/api/target_stocks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ date: date })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '获取数据失败');
        }

        // 显示数据
        displayTargetStocks(data.data);

    } catch (error) {
        console.error('获取目标股票数据失败:', error);
        showToast(error.message, 'error');
        
        // 显示错误状态
        const tbody = document.getElementById('targetStocksBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="px-6 py-4 text-center">
                    <div class="text-red-500">
                        ${error.message}
                    </div>
                </td>
            </tr>
        `;
    }
}

// 添加排序函数
function sortStocks(column) {
    const tbody = document.getElementById('targetStocksBody');
    const rows = Array.from(tbody.getElementsByTagName('tr'));
    
    // 初始化该列的排序状态(如果还没有)
    if (!sortStates[column]) {
        sortStates[column] = null;
    }
    
    // 更新排序状态
    if (currentSortColumn !== column) {
        // 切换到新列时，重置其他列的状态
        Object.keys(sortStates).forEach(key => {
            sortStates[key] = null;
        });
        // 新列设置为升序
        sortStates[column] = 'asc';
        currentSortColumn = column;
    } else {
        // 同一列循环: null -> asc -> desc -> null
        switch (sortStates[column]) {
            case null:
                sortStates[column] = 'asc';
                break;
            case 'asc':
                sortStates[column] = 'desc';
                break;
            case 'desc':
                sortStates[column] = null;
                break;
        }
    }
    
    // 更新所有表头的排序图标
    document.querySelectorAll('th[data-sort]').forEach(th => {
        const icon = th.querySelector('.sort-icon');
        const columnName = th.getAttribute('data-sort');
        if (columnName === column) {
            switch (sortStates[column]) {
                case 'asc':
                    icon.textContent = '↑';
                    break;
                case 'desc':
                    icon.textContent = '↓';
                    break;
                default:
                    icon.textContent = '↕';
                    break;
            }
        } else {
            icon.textContent = '↕';
        }
    });
    
    // 如果是不排序状态，恢复原始顺序
    if (sortStates[column] === null) {
        rows.sort((a, b) => {
            return parseInt(a.dataset.originalIndex || 0) - parseInt(b.dataset.originalIndex || 0);
        });
    } else {
        // 排序行
        rows.sort((a, b) => {
            let aValue = getCellValue(a, column);
            let bValue = getCellValue(b, column);
            
            // 数值比较
            if (['最新价格', '最新涨跌幅', '换手率', '最佳胜率', '最佳回报', '夏普比率'].includes(column)) {
                aValue = parseFloat(aValue.replace(/[+%]/g, '')) || 0;
                bValue = parseFloat(bValue.replace(/[+%]/g, '')) || 0;
            }
            
            // 比较
            if (aValue === bValue) return 0;
            const compareResult = aValue > bValue ? 1 : -1;
            return sortStates[column] === 'asc' ? compareResult : -compareResult;
        });
    }
    
    // 重新插入排序后的行
    rows.forEach(row => tbody.appendChild(row));
}

// 获取单元格值的辅助函数
function getCellValue(row, column) {
    const columnIndex = getColumnIndex(column);
    const cell = row.cells[columnIndex];
    
    // 如果单元格包含链接，获取链接文本
    const link = cell.querySelector('a');
    if (link) {
        return link.textContent.trim();
    }
    
    return cell.textContent.trim();
}

// 获取列索引的辅助函数
function getColumnIndex(column) {
    const columnMap = {
        '股票代码': 0,
        '股票名称': 1,
        '所属行业': 2,
        '最新价格': 3,
        '最新涨跌幅': 4,
        '换手率': 5,
        '最佳胜率': 6,
        '最佳回报': 7,
        '夏普比率': 8
    };
    return columnMap[column] || 0;
}

// 在文档加载完成后初始化排序事件监听
document.addEventListener('DOMContentLoaded', function() {
    // 为所有可排序的表头添加点击事件
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.getAttribute('data-sort');
            sortStocks(column);
        });
    });
});

