// 在文件开头添加全局变量来跟踪排序状态
let currentSortColumn = null;
let sortStates = {};  // 用于跟踪每列的排序状态: null(不排序) -> 'asc' -> 'desc'

// 添加对话历史存储
let conversationHistory = [];

// 在文件开头添加以下格式化函数

// 格式化数字，保留2位小数
function formatNumber(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return '-';
    }
    return Number(value).toFixed(2);
}

// 格式化涨跌幅
function formatChangePercent(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return '-';
    }
    const num = Number(value);
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
}

// 根据数值获取对应的颜色类名
function getValueColor(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return 'text-gray-500';
    }
    const num = Number(value);
    if (num >= 0.6) return 'text-green-600';
    if (num >= 0.5) return 'text-blue-600';
    return 'text-red-600';
}

// 获取夏普比率的颜色
function getSharpeColor(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return 'text-gray-500';
    }
    const num = Number(value);
    if (num >= 2.0) return 'text-green-600';  // 优秀
    if (num >= 1.0) return 'text-blue-600';   // 良好
    if (num >= 0.0) return 'text-yellow-600'; // 一般
    return 'text-red-600';                    // 较差
}

// 修改表单提交处理
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired');
    
    const optimizeForm = document.getElementById('optimizeForm');
    console.log('Optimize form found:', !!optimizeForm);
    
    if (optimizeForm) {
        // 移除所有现有的事件监听器
        const newForm = optimizeForm.cloneNode(true);
        optimizeForm.parentNode.replaceChild(newForm, optimizeForm);
        
        // 添加新的事件监听器
        newForm.addEventListener('submit', function(event) {
            console.log('Form submit event fired');
            
            // 确保阻止默认行为
            event.preventDefault();
            event.stopPropagation();  // 添加这行来阻止事件冒泡
            
            // 禁用提交按钮，防止重复提交
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                console.log('Submit button disabled');
            }
            
            // 调用优化函数
            optimize().finally(() => {
                // 优化完成后重新启用提交按钮
                if (submitButton) {
                    submitButton.disabled = false;
                    console.log('Submit button re-enabled');
                }
            });
            
            // 确保返回 false
            return false;
        });
        
        // 防止回车键触发表单提交
        newForm.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                return false;
            }
        });
    }
});

// 修改 optimize 函数，添加调试日志
function optimize() {
    console.log('optimize function called');
    
    const symbol = document.getElementById('symbol').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    console.log('Parameters:', { symbol, startDate, endDate }); // 添加参数日志

    if (!symbol || !startDate || !endDate) {
        alert('请填写完整的参数信息');
        return Promise.reject(new Error('参数不完整'));
    }

    // 显示加载动画，隐藏回测结果区域
    const loadingEl = document.getElementById('loading');
    const resultsEl = document.getElementById('results');
    const stockInfoEl = document.getElementById('stockInfo');
    const backtestResultsEl = document.getElementById('backtestResults');

    console.log('DOM elements:', { 
        loading: !!loadingEl, 
        results: !!resultsEl, 
        stockInfo: !!stockInfoEl, 
        backtestResults: !!backtestResultsEl 
    }); // 添加DOM元素检查日志

    if (loadingEl) loadingEl.classList.remove('hidden');
    if (resultsEl) resultsEl.classList.add('hidden');
    if (stockInfoEl) stockInfoEl.classList.add('hidden');
    if (backtestResultsEl) backtestResultsEl.classList.add('hidden');

    // 返回 Promise
    return fetch('/optimize', {
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
    .then(response => {
        console.log('Response status:', response.status); // 添加响应状态日志
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Received data:', data); // 添加接收到的数据日志
        
        if (loadingEl) loadingEl.classList.add('hidden');
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        const resultsDiv = document.getElementById('results');
        console.log('Results div found:', !!resultsDiv); // 添加结果容器检查日志
        
        if (!resultsDiv) {
            throw new Error('Results container not found');
        }

        // 显示结果
        try {
            displayResults(data, resultsDiv);
        } catch (displayError) {
            console.error('Error in displayResults:', displayError);
            throw displayError;
        }
    })
    .catch(error => {
        console.error('Error in optimize:', error);
        console.error('Error stack:', error.stack);
        if (loadingEl) loadingEl.classList.add('hidden');
        alert('优化过程中发生错误: ' + error.message);
        throw error;
    });
}

// 添加标题和内容展示相关的样式
const contentStyles = document.createElement('style');
contentStyles.textContent = `
    /* 标题样式 */
    .content-title {
        position: relative;
        padding-left: 1rem;
        margin: 2rem 0 1rem;
        transition: all 0.3s ease;
    }

    .content-title::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(to bottom, #8B5CF6, #6D28D9);
        border-radius: 2px;
        transition: all 0.3s ease;
    }

    .content-title:hover::before {
        width: 6px;
        background: linear-gradient(to bottom, #7C3AED, #5B21B6);
    }

    /* 一级标题 */
    .content-title-h1 {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1F2937;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }

    /* 二级标题 */
    .content-title-h2 {
        font-size: 1.25rem;
        font-weight: 500;
        color: #374151;
    }

    /* 三级标题 */
    .content-title-h3 {
        font-size: 1.125rem;
        font-weight: 500;
        color: #4B5563;
    }

    /* 内容区块 */
    .content-block {
        background: white;
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }

    .content-block:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transform: translateY(-2px);
    }

    /* 内容分割线 */
    .content-divider {
        height: 1px;
        background: linear-gradient(to right, #E5E7EB, #8B5CF6, #E5E7EB);
        margin: 2rem 0;
        opacity: 0.5;
    }

    /* 标签样式 */
    .content-tag {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease;
    }

    /* 不同类型的标签样式 */
    .tag-info {
        background-color: #EEF2FF;
        color: #4F46E5;
    }

    .tag-success {
        background-color: #ECFDF5;
        color: #059669;
    }

    .tag-warning {
        background-color: #FFFBEB;
        color: #D97706;
    }

    .tag-error {
        background-color: #FEF2F2;
        color: #DC2626;
    }

    /* 折叠面板样式 */
    .collapsible-section {
        border: 1px solid #E5E7EB;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        overflow: hidden;
    }

    .collapsible-header {
        padding: 1rem;
        background-color: #F9FAFB;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.3s ease;
    }

    .collapsible-header:hover {
        background-color: #F3F4F6;
    }

    .collapsible-content {
        padding: 0;
        max-height: 0;
        overflow: hidden;
        transition: all 0.3s ease;
    }

    .collapsible-section.active .collapsible-content {
        padding: 1rem;
        max-height: 1000px;
    }

    /* 动画效果 */
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .animate-slide-down {
        animation: slideDown 0.3s ease-out forwards;
    }
`;
document.head.appendChild(contentStyles);

// 添加创建标题的辅助函数
function createTitle(text, level = 1) {
    const title = document.createElement('div');
    title.className = `content-title content-title-h${level} animate-slide-down`;
    title.textContent = text;
    return title;
}

// 添加创建内容块的辅助函数
function createContentBlock(content, tags = []) {
    const block = document.createElement('div');
    block.className = 'content-block animate-slide-down';
    
    // 添加标签
    if (tags.length > 0) {
        const tagsContainer = document.createElement('div');
        tagsContainer.className = 'mb-3';
        tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = `content-tag tag-${tag.type || 'info'}`;
            tagElement.textContent = tag.text;
            tagsContainer.appendChild(tagElement);
        });
        block.appendChild(tagsContainer);
    }
    
    // 添加内容
    const contentElement = document.createElement('div');
    contentElement.className = 'prose prose-indigo max-w-none';
    contentElement.innerHTML = marked.parse(content);
    block.appendChild(contentElement);
    
    return block;
}

// 添加创建折叠面板的辅助函数
function createCollapsibleSection(title, content) {
    const section = document.createElement('div');
    section.className = 'collapsible-section';
    
    const header = document.createElement('div');
    header.className = 'collapsible-header';
    header.innerHTML = `
        <span class="font-medium">${title}</span>
        <svg class="w-5 h-5 transform transition-transform duration-200" 
             fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
    `;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'collapsible-content';
    contentDiv.innerHTML = content;
    
    section.appendChild(header);
    section.appendChild(contentDiv);
    
    // 添加点击事件
    header.addEventListener('click', () => {
        const isActive = section.classList.contains('active');
        section.classList.toggle('active');
        header.querySelector('svg').style.transform = isActive ? 'rotate(0)' : 'rotate(180deg)';
    });
    
    return section;
}

function displayResults(data, resultsDiv) {
    try {
        console.log('displayResults started with data:', data);
        console.log('resultsDiv:', resultsDiv);
        
        // 检查必要的数据字段
        if (!data.stockName) {
            console.error('Missing stockName in data');
            throw new Error('Missing stockName in data');
        }
        if (!data.bestParams || typeof data.bestParams !== 'object') {
            console.error('Invalid or missing bestParams in data');
            throw new Error('Invalid or missing bestParams in data');
        }
        if (!data.metrics || typeof data.metrics !== 'object') {
            console.error('Invalid or missing metrics in data');
            throw new Error('Invalid or missing metrics in data');
        }

        // 显示结果区域
        resultsDiv.classList.remove('hidden');
        resultsDiv.style.animation = 'fadeIn 0.5s ease-in';
        
        // 清除现有内容
        resultsDiv.innerHTML = '';
        
        // 创建主容器
        const mainContainer = document.createElement('div');
        mainContainer.className = 'bg-gradient-to-br from-white to-blue-50 rounded-xl shadow-lg p-6 space-y-8';
        
        console.log('Creating main container with data:', {
            stockName: data.stockName,
            metrics: data.metrics,
            bestParams: data.bestParams
        });

        // 添加股票信息标题和 AI 分析按钮
        console.log('Adding stock info section...');
        const stockInfoTitle = document.createElement('div');
        stockInfoTitle.className = 'flex items-center justify-between mb-6';
        stockInfoTitle.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="flex-shrink-0">
                    <div class="h-10 w-1 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full"></div>
                </div>
                <div>
                    <h1 class="text-2xl font-bold text-gray-900">${data.stockName}</h1>
                    <p class="text-sm text-gray-500">股票代码：${document.getElementById('symbol')?.value || ''}</p>
                </div>
            </div>
            <div class="flex items-center space-x-4">
                <div class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    A股
                </div>
                <button onclick="switchToAIAnalysis('${document.getElementById('symbol')?.value || ''}')"
                        class="inline-flex items-center px-4 py-2 bg-purple-600 hover:bg-purple-700 
                               text-white text-sm font-medium rounded-lg transition-colors duration-200 
                               shadow-md hover:shadow-lg space-x-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    <span>AI 分析</span>
                </button>
            </div>
        `;
        mainContainer.appendChild(stockInfoTitle);
        
        // 添加分析结果标题
        console.log('Adding metrics section...');
        const analysisTitle = document.createElement('div');
        analysisTitle.className = 'flex items-center space-x-3 mb-6';
        analysisTitle.innerHTML = `
            <div class="flex-shrink-0">
                <div class="h-10 w-1 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full"></div>
            </div>
            <h1 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
                分析结果
            </h1>
        `;
        mainContainer.appendChild(analysisTitle);
        
        // 创建策略分析部分
        console.log('Adding strategy section...');
        const strategySection = createStrategySection(data);
        mainContainer.appendChild(strategySection);
        
        // 最后将主容器添加到结果区域
        resultsDiv.appendChild(mainContainer);
        console.log('displayResults completed');
        
    } catch (err) {
        console.error('Error in displayResults:', err);
        console.error('Error stack:', err.stack);
        throw err;
    }
}

// 创建策略分析部分的辅助函数
function createStrategySection(data) {
    const section = document.createElement('div');
    section.className = 'space-y-6';

    const metrics = data.metrics || {};
    const lastSignal = metrics.lastSignal || {};

    // 修改这里：直接使用API返回的signalStrength，而不是计算
    const signalStrength = {
        value: (data.metrics.signalStrength || 0) * 100, // 转换为百分比
        color: getSignalColor(data.metrics.signalStrength * 100),
        description: getSignalDescription(data.metrics.signalStrength * 100)
    };

    // 添加基本信息卡片
    const basicInfo = document.createElement('div');
    basicInfo.className = 'grid grid-cols-1 md:grid-cols-3 gap-4';
    basicInfo.innerHTML = `
        <div class="bg-white rounded-xl shadow-sm p-4 transform hover:scale-105 transition-transform duration-300">
            <div class="text-sm text-gray-500 mb-1">初始资金</div>
            <div class="text-xl font-semibold">¥100,000</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-4 transform hover:scale-105 transition-transform duration-300">
            <div class="text-sm text-gray-500 mb-1">最终资金</div>
            <div class="text-xl font-semibold">¥${(100000 * (1 + metrics.totalReturn/100)).toFixed(2)}</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-4 transform hover:scale-105 transition-transform duration-300">
            <div class="text-sm text-gray-500 mb-1">总收益</div>
            <div class="text-xl font-semibold text-green-600">¥${(100000 * metrics.totalReturn/100).toFixed(2)}</div>
        </div>
    `;
    section.appendChild(basicInfo);

    // 添加详细指标卡片
    const detailsCard = document.createElement('div');
    detailsCard.className = 'grid grid-cols-1 md:grid-cols-2 gap-6';
    detailsCard.innerHTML = `
        <div class="bg-white rounded-xl shadow-sm p-6 space-y-4">
            <h3 class="text-lg font-semibold text-gray-800 border-b pb-2">策略表现</h3>
            <div class="space-y-3">
                <div class="flex justify-between items-center">
                    <span class="text-gray-600">收益率</span>
                    <span class="text-lg font-medium ${metrics.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'}">
                        ${metrics.totalReturn?.toFixed(2)}%
                    </span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-gray-600">胜率</span>
                    <span class="text-lg font-medium text-blue-600">${metrics.winRate?.toFixed(2)}%</span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-gray-600">最大回撤</span>
                    <span class="text-lg font-medium text-red-600">${metrics.maxDrawdown?.toFixed(2)}%</span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-gray-600">夏普比率</span>
                    <span class="text-lg font-medium text-purple-600">${metrics.sharpeRatio?.toFixed(2)}</span>
                </div>
            </div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-6 space-y-4">
            <h3 class="text-lg font-semibold text-gray-800 border-b pb-2">交易信号</h3>
            <div class="space-y-4">
                <div class="flex flex-col">
                    <span class="text-gray-600 mb-2">当前信号</span>
                    <span class="inline-flex items-center px-4 py-2 rounded-lg text-base font-medium ${
                        lastSignal.color === 'green' ? 'bg-green-100 text-green-800' :
                        lastSignal.color === 'red' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                    }">
                        ${lastSignal.text}
                    </span>
                </div>
                <div class="space-y-2">
                    <div class="flex items-center justify-between">
                        <span class="text-sm text-gray-500">信号强度</span>
                        <span class="text-sm font-medium">${signalStrength.description} (${signalStrength.value.toFixed(0)}%)</span>
                    </div>
                    <div class="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div class="h-full ${signalStrength.color} rounded-full transition-all duration-500" 
                             style="width: ${signalStrength.value}%"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    section.appendChild(detailsCard);
    
    // 在 detailsCard 后添加策略参数卡片
    const strategyParamsCard = document.createElement('div');
    strategyParamsCard.className = 'bg-white rounded-xl shadow-sm p-6 mt-6';
    strategyParamsCard.innerHTML = `
        <div class="flex items-center space-x-3 mb-6">
            <div class="flex-shrink-0">
                <div class="h-10 w-1 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full"></div>
            </div>
            <h3 class="text-xl font-bold text-gray-800">最优策略参数</h3>
        </div>
        
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
            ${Object.entries(data.bestParams || {})
                .filter(([key]) => formatParamName(key))
                .map(([key, value]) => `
                    <div class="relative bg-gradient-to-br from-white to-gray-50 rounded-xl p-6 
                                shadow-sm hover:shadow-md transition-all duration-300 
                                transform hover:-translate-y-1">
                        <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r 
                                   from-blue-500 to-purple-500 rounded-t-xl opacity-75"></div>
                        <div class="mt-2">
                            <div class="text-sm font-medium text-gray-500 mb-2">
                                ${formatParamName(key)}
                            </div>
                            <div class="flex items-baseline">
                                <span class="text-2xl font-bold text-gray-900">
                                    ${formatParamValue(value, key)}  <!-- 传入 key 参数 -->
                                </span>
                                ${getParamUnit(key)}
                            </div>
                        </div>
                        <div class="absolute bottom-4 right-4 opacity-10">
                            ${getParamIcon(key)}
                        </div>
                    </div>
                `).join('')}
        </div>
    `;
    section.appendChild(strategyParamsCard);

    return section;
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
    // 只显示这些参数
    const nameMap = {
        'period': '周期',
        'mult': '倍数',
        'strength_threshold': '信号阈值'
    };
    
    // 如果参数不在映射表中，返回空字符串，这样这个参数就不会显示
    return nameMap[key] || '';
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
        },
        {
            inputId: 'industryDate',
            defaultDate: today,
            maxDate: today,
            onChange: (date, dateString) => {
                console.log('行业分析日期已更改:', dateString);
                handleIndustryAnalysis(dateString);
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
    
    // 初始化日期选择器
    initializeDatePickers();
    
    // 初始化其他组件
    initializeOtherComponents();
    
    // 绑定持分析按钮事件
    const portfolioForm = document.getElementById('portfolioForm');
    if (portfolioForm) {
        console.log('找到持仓分析表单，添加提交事件监听器');
        portfolioForm.addEventListener('submit', function(event) {
            console.log('持仓分析表单提交被触发');
            runPortfolioAnalysis(event);
        });
    } else {
        console.warn('未找到持仓分析表单');
    }
    
    // ... 化朗读功能
    SpeechController.init();
});

// 添加日期更新处理函数
function updateDailyPicks(date) {
    console.log('更新每日选股分析，日期:', date);
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
            // 对于不支持原生日期的设备，可以在这里添加自定义日期选择器
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

// 修改 initializeTabs 函数
function initializeTabs() {
    // 为所有标签按钮添加点击事件
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
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

// 修改 switchTab 函数
function switchTab(tabId) {
    console.log('Switching to tab:', tabId);
    
    // 更新标签按钮状态
    document.querySelectorAll('.tab-button').forEach(button => {
        const isActive = button.getAttribute('data-tab') === tabId;
        button.classList.toggle('active', isActive);
        button.classList.toggle('bg-white', isActive);
        button.classList.toggle('shadow-lg', isActive);
        button.classList.toggle('text-purple-600', isActive);
        button.classList.toggle('border-purple-500', isActive);
        button.classList.toggle('hover:bg-purple-50', !isActive);
        button.classList.toggle('text-gray-600', !isActive);
        button.classList.toggle('border-transparent', !isActive);
        
        // 更新图标颜色
        const icon = button.querySelector('svg');
        if (icon) {
            icon.classList.toggle('text-purple-500', isActive);
            icon.classList.toggle('text-gray-400', !isActive);
        }
    });

    // 更新内容显示
    document.querySelectorAll('.tab-content').forEach(content => {
        const isSelected = content.id === tabId;
        if (isSelected) {
            content.classList.remove('hidden');
            requestAnimationFrame(() => {
                content.style.opacity = '1';
                content.style.transform = 'translateY(0)';
            });
        } else {
            content.style.opacity = '0';
            content.style.transform = 'translateY(10px)';
            setTimeout(() => {
                content.classList.add('hidden');
            }, 300);
        }
    });
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

// 修改 handleAnalysis 函数，添加对话历史记录
async function handleAnalysis(event) {
    event.preventDefault();
    
    const symbol = document.getElementById('analysisSymbol').value;
    const model = document.getElementById('modelSelect').value;
    const analysisContent = document.getElementById('analysisContent');
    const resultsDiv = document.getElementById('analysisResults');
    
    if (!symbol) {
        showToast('请输入股票代码', 'warning');
        return;
    }
    
    // 不再重置对话历史，而是添加新的对话
    const question = "请对下一个交易日的走势进行预判，并给出对应的交易策略";
    conversationHistory = [{
        role: "user",
        content: question
    }];
    
    // 显示结果区域
    resultsDiv.classList.remove('hidden');
    
    // 创建消息容器
    const messageDiv = document.createElement('div');
    messageDiv.className = 'ai-message bg-white rounded-lg shadow-lg p-6 mb-6 transform transition-all duration-300 hover:shadow-xl';
    messageDiv.innerHTML = `
        <div class="message-header flex items-center justify-between mb-4 pb-3 border-b border-gray-100">
            <div class="flex items-center space-x-3">
                <div class="bg-gradient-to-br from-purple-100 to-pink-100 rounded-lg p-2">
                    <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                    </svg>
                </div>
                <div>
                    <span class="text-lg font-semibold text-gray-800">AI 分析助手</span>
                    <span class="ml-2 px-2 py-1 text-xs font-medium bg-purple-100 text-purple-600 rounded-full">
                        ${model.toUpperCase()}
                    </span>
                </div>
            </div>
            <button class="copy-btn flex items-center space-x-2 px-3 py-1.5 text-sm text-gray-600 
                         bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200"
                    onclick="copyMessage(this)">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-12a2 2 0 00-2-2h-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                <span>复制</span>
            </button>
        </div>
        <div class="message-content prose prose-lg max-w-none">
            <div class="typing-effect text-gray-600">正在分析，请稍候...</div>
        </div>
    `;
    
    analysisContent.innerHTML = '';
    analysisContent.appendChild(messageDiv);
    
    const contentDiv = messageDiv.querySelector('.message-content');
    
    try {
        const response = await fetch('/analyze_stock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                model: model,
                question: question,
                conversation_history: conversationHistory
            })
        });

        if (!response.ok) {
            throw new Error('请求失败');
        }

        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(5));
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        if (data.content) {
                            fullText += data.content;
                            // 使用 markdown-it 处理分析报告
                            const md = window.markdownit({
                                html: true,
                                linkify: true,
                                typographer: true,
                                highlight: function (str, lang) {
                                    if (lang && hljs.getLanguage(lang)) {
                                        try {
                                            return hljs.highlight(str, { language: lang }).value;
                                        } catch (__) {}
                                    }
                                    return ''; // 使用默认的转义
                                }
                            });

                            // 添加插件支持
                            md.use(window.markdownitEmoji);
                            md.use(window.markdownitFootnote);
                            md.use(window.markdownitTaskLists);

                            // 渲染markdown内容
                            contentDiv.innerHTML = md.render(fullText);
                        }
                    } catch (e) {
                        console.warn('解析数据行失败:', e);
                    }
                }
            }
        }

        // 在成功接收完整响应后，添加AI回复到对话历史
        conversationHistory.push({
            role: "assistant",
            content: fullText
        });

    } catch (error) {
        contentDiv.innerHTML = `
            <div class="text-red-500 p-4 bg-red-50 rounded-lg">
                分析失败: ${error.message}
            </div>
        `;
        showToast(error.message, 'error');
    }
}

// 确保表单绑定了事件处理函数
document.addEventListener('DOMContentLoaded', function() {
    // 移除重复的事件绑定
    const analysisForm = document.getElementById('analysisForm');
    if (analysisForm) {
        // 确保移除任何现有的事件监听器
        analysisForm.removeEventListener('submit', handleAnalysis);
        // 只添加一次事件监听器
        analysisForm.addEventListener('submit', handleAnalysis, { once: true });
    }

    // 追问相关的事件监听器
    const followupForm = document.getElementById('followupForm');
    if (followupForm) {
        followupForm.removeEventListener('submit', sendFollowupQuestion);
        followupForm.addEventListener('submit', function(event) {
            event.preventDefault();
            sendFollowupQuestion();
        });
    }
    
    const followupInput = document.getElementById('followupQuestion');
    if (followupInput) {
        followupInput.removeEventListener('keypress', handleFollowupKeypress);
        followupInput.addEventListener('keypress', handleFollowupKeypress);
    }
});

// 将回车键处理提取为单独的函数
function handleFollowupKeypress(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendFollowupQuestion();
    }
}

// 修改 applyMarkdownStyles 函
function applyMarkdownStyles(element) {
    // 添加容器类
    element.classList.add('markdown-content', 'prose', 'prose-indigo', 'max-w-none');
    
    // 处理格
    const tables = element.getElementsByTagName('table');
    Array.from(tables).forEach(table => {
        // 添加基础表格样式
        table.classList.add(
            'min-w-full',
            'divide-y',
            'divide-gray-200',
            'my-4'
        );
        
        // 处理表头
        const thead = table.querySelector('thead');
        if (thead) {
            thead.classList.add('bg-gray-50');
            const headerCells = thead.getElementsByTagName('th');
            Array.from(headerCells).forEach(cell => {
                cell.classList.add(
                    'px-6',
                    'py-3',
                    'text-left',
                    'text-xs',
                    'font-medium',
                    'text-gray-500',
                    'uppercase',
                    'tracking-wider'
                );
            });
        }
        
        // 处理表体
        const tbody = table.querySelector('tbody');
        if (tbody) {
            tbody.classList.add('bg-white', 'divide-y', 'divide-gray-200');
            const rows = tbody.getElementsByTagName('tr');
            Array.from(rows).forEach(row => {
                row.classList.add('hover:bg-gray-50', 'transition-colors');
                const cells = row.getElementsByTagName('td');
                Array.from(cells).forEach(cell => {
                    cell.classList.add(
                        'px-6',
                        'py-4',
                        'whitespace-nowrap',
                        'text-sm',
                        'text-gray-900'
                    );
                    
                    // 处理数值类型的单元格
                    const content = cell.textContent.trim();
                    if (!isNaN(parseFloat(content))) {
                        // 如果是百分比
                        if (content.includes('%')) {
                            const value = parseFloat(content);
                            cell.classList.add(value >= 0 ? 'text-red-600' : 'text-green-600');
                        }
                        // 如果是大数值（市值等）
                        else if (parseFloat(content) > 10000) {
                            cell.classList.add('font-medium');
                        }
                    }
                });
            });
        }
        
        // 添加表格容器以支持水平滚动
        const wrapper = document.createElement('div');
        wrapper.classList.add('overflow-x-auto', 'shadow', 'rounded-lg', 'border', 'border-gray-200');
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
    
    // 处理标题
    const headers = element.querySelectorAll('h1, h2, h3, h4, h5, h6');
    headers.forEach(header => {
        header.classList.add('font-bold', 'text-gray-900', 'my-4');
        if (header.tagName === 'H1') {
            header.classList.add('text-2xl', 'mt-8', 'mb-6');
        } else if (header.tagName === 'H2') {
            header.classList.add('text-xl', 'mt-6', 'mb-4');
        } else {
            header.classList.add('text-lg', 'mt-4', 'mb-2');
        }
    });
    
    // 处理段落
    const paragraphs = element.getElementsByTagName('p');
    Array.from(paragraphs).forEach(p => {
        p.classList.add('text-gray-600', 'my-4', 'leading-relaxed');
    });
    
    // 处理列表
    const lists = element.querySelectorAll('ul, ol');
    lists.forEach(list => {
        list.classList.add('my-4', 'space-y-2', 'list-inside');
        if (list.tagName === 'UL') {
            list.classList.add('list-disc');
        } else {
            list.classList.add('list-decimal');
        }
        
        // 处理列表项
        const items = list.getElementsByTagName('li');
        Array.from(items).forEach(item => {
            item.classList.add('text-gray-600', 'ml-4');
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
    
    // 处理代码块
    const codeBlocks = element.querySelectorAll('pre code');
    codeBlocks.forEach(code => {
        const pre = code.parentElement;
        pre.classList.add(
            'bg-gray-50',
            'rounded-lg',
            'p-4',
            'my-4',
            'overflow-x-auto',
            'text-sm',
            'font-mono',
            'text-gray-700'
        );
    });
    
    // 处理行内代码
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

    // 处理关键信息标题
    element.querySelectorAll('.key-info-title').forEach(title => {
        title.style.borderLeft = '4px solid #3b82f6';
    });

    // 处理关键信息内容
    element.querySelectorAll('.key-info-content').forEach(content => {
        content.style.backgroundColor = 'white';
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
                    <p class="text-gray-700">
                        ${data.signal === -2 ? '减仓预警' : data.signal} 
                        （ ${data.reason} ）
                    </p>
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
    
    // 使用 requestAnimationFrame 保过渡效果
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

// 在始优化时显示股票名称
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
    
    // 显示加载示
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
    
    // 自动触发优化
    document.getElementById('optimizeForm').dispatchEvent(new Event('submit'));
}

// 修改 switchToAIAnalysis 函数，添加自动触发分析的功能
function switchToAIAnalysis(stockCode) {
    // 切换到个股分析标签页
    switchTab('analysis-tab');
    
    // 设置股票代码
    const analysisSymbol = document.getElementById('analysisSymbol');
    if (analysisSymbol) {
        analysisSymbol.value = stockCode;
        
        // 自动触发分析
        const analysisForm = document.getElementById('analysisForm');
        if (analysisForm) {
            // 使用 setTimeout 确保标签页切换完成后再触发分析
            setTimeout(() => {
                analysisForm.dispatchEvent(new Event('submit'));
            }, 100);
        }
    }
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

// 合并所有样式到一个统一的样式表
const combinedStyles = document.createElement('style');
combinedStyles.textContent = `
    /* 通用标签页按钮样式 */
    .tab-button {
        position: relative;
        white-space: nowrap;
        min-width: 100px;
        transition: all 0.3s ease;
    }

    .tab-button:hover {
        background-color: #F5F3FF;
        color: #6D28D9;
        transform: translateY(-2px);
    }

    .tab-button.active {
        background-color: #EDE9FE;
        color: #6D28D9;
    }

    /* 只保留一个底部指示器 */
    .tab-button.active::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 30%;
        height: 3px;
        background-color: #6D28D9;
        border-radius: 3px;
        transition: all 0.3s ease;
    }

    /* 图标和文字动画 */
    .tab-button svg {
        transition: all 0.3s ease;
    }

    .tab-button:hover svg {
        transform: scale(1.1);
        color: #6D28D9;
    }

    .tab-button.active svg {
        color: #6D28D9;
    }

    .tab-button span {
        transition: all 0.3s ease;
    }

    .tab-button:hover span {
        transform: scale(1.05);
    }

    /* 内容区域动画 */
    .tab-content,
    .industry-tab-content {
        transition: all 0.3s ease;
        opacity: 0;
        transform: translateY(10px);
    }

    .tab-content:not(.hidden),
    .industry-tab-content:not(.hidden) {
        opacity: 1;
        transform: translateY(0);
    }

    /* 响应式设计 */
    @media (max-width: 640px) {
        .tab-button {
            min-width: 80px;
            padding: 0.75rem;
        }
        
        .tab-button svg {
            width: 1.75rem;
            height: 1.75rem;
        }
        
        .tab-button span {
            font-size: 0.75rem;
        }
    }
`;

// 移除旧的样式表（如果存在）
const oldStyles = document.querySelectorAll('style');
oldStyles.forEach(style => {
    if (style.textContent.includes('.tab-button') || 
        style.textContent.includes('.industry-tab-button')) {
        style.remove();
    }
});

// 添加新的统一样式表
document.head.appendChild(combinedStyles);

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
    } else if (signal.includes('观察') || signal.includes('待')) {
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
        
        console.log('tradeData:', tradeData);
        // 解析信号强度（假设在 tradeData 中添加了 '信号强度' 字段）
        const signalStrength = parseFloat(tradeData['信号强度'] || 0) * 100;
        const strengthColor = getSignalColor(signalStrength);
        const strengthDesc = getSignalDescription(signalStrength);
        console.log('signalStrength:', signalStrength);
        console.log('strengthColor:', strengthColor);
        console.log('strengthDesc:', strengthDesc);
        
        html += `
            <div class="bg-white rounded-lg shadow-md border border-gray-200 hover:shadow-lg transition-shadow duration-200">
                <div class="p-4">
                    <!-- 标题行：股票名和分析按钮 -->
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
                    
                    <!-- 交易建议和信号强度部分 -->
                    <div class="mb-4 ${signalStyle.bg} rounded-lg p-3 border ${signalStyle.border}">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center">
                                <svg class="w-5 h-5 ${signalStyle.color} mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${signalStyle.icon}"/>
                                </svg>
                                <p class="text-sm font-medium ${signalStyle.color}">
                                    ${tradeData['交易建议'] || '无交易建议'}
                                </p>
                            </div>
                            <div class="flex items-center space-x-2">
                                <span class="text-sm text-gray-600">信号强度:</span>
                                <div class="flex items-center">
                                    <div class="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                                        <div class="h-full ${strengthColor} rounded-full" style="width: ${signalStrength}%"></div>
                                    </div>
                                    <span class="ml-2 text-sm font-medium ${strengthColor.replace('bg-', 'text-')}">${strengthDesc}</span>
                                </div>
                            </div>
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
                                        <div class="text-sm text-gray-500 mb-1">最低</div>
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
    // 检查 portfolioResults 元素是否存在
    const portfolioResults = document.getElementById('portfolioResults');
    console.log('portfolioResults:', portfolioResults);
    if (!portfolioResults) {
        console.error('找不到 portfolioResults 元素');
        return;
    }

    // 检查 html 是否为空
    if (!html || typeof html !== 'string') {
        console.error('html 内容无效:', html);
        return;
    }

    try {
        portfolioResults.innerHTML = html;
    } catch (error) {
        console.error('设置 portfolioResults 内容时出错:', error);
    }
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
            console.warn('找到朗读按钮，无法更新状态');
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
        
        // 处理信号强度的颜色逻辑
        const signalStrength = parseFloat(stock['signal_strength'] || 0);
        const signalColor = signalStrength >= 0.8 ? 'text-red-600' :  // 强烈信号 - 红色
                          signalStrength >= 0.6 ? 'text-orange-600' :  // 中强信号 - 橙色
                          signalStrength >= 0.4 ? 'text-yellow-600' :  // 一般信号 - 黄色
                          signalStrength >= 0.2 ? 'text-blue-600' :    // 弱信号 - 蓝色
                          'text-gray-600';                             // 无信号 - 灰色
        
        // 处理最佳胜率和最佳回报的颜色
        const winRateValue = parseFloat(stock['最佳胜率'] || 0);
        const returnValue = parseFloat(stock['最佳回报'] || 0);
        const sharpeValue = parseFloat(stock['夏普比率'] || 0);
        
        // 根据胜率值设置颜色
        const winRateColor = winRateValue >= 0.6 ? 'text-green-600' : 
                           winRateValue >= 0.5 ? 'text-blue-600' : 'text-red-600';
                           
        // 根据回报值设置颜色
        const returnColor = returnValue >= 0.2 ? 'text-green-600' : 
                          returnValue >= 0 ? 'text-blue-600' : 'text-red-600';
                          
        // 根据夏普比率设置颜色
        const sharpeColor = sharpeValue >= 2.0 ? 'text-green-600' :  // 优秀 - 绿色
                          sharpeValue >= 1.0 ? 'text-blue-600' :     // 良好 - 蓝色
                          sharpeValue >= 0.0 ? 'text-yellow-600' :   // 一般 - 黄色
                          'text-red-600';                            // 较差 - 红色
        
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
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm ${sharpeColor} font-medium">
                ${Number(sharpeValue).toFixed(2)}
            </td>
            <td class="px-3 sm:px-6 py-2 sm:py-4 whitespace-nowrap text-xs sm:text-sm ${signalColor} font-medium">
                ${(signalStrength * 100).toFixed(0)}%
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
                    icon.textContent = '';
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

// 在文档加载完成后初始化标签页
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...'); // 调试日志
    initializeTabs();
    
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
    // ... 有的始化代码 ...
    
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
        if (!date) {
            showToast('请选择日期', 'warning');
            return;
        }

        const tbody = document.getElementById('targetStocksBody');
        if (!tbody) {
            console.error('未找到目标股票表格主体元素');
            return;
        }

        // 显示加载状态
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="px-6 py-4 text-center">
                    <div class="flex justify-center items-center space-x-2">
                        <div class="animate-spin rounded-full h-4 w-4 border-2 border-purple-500 border-t-transparent"></div>
                        <span class="text-gray-600">正在加载数据...</span>
                    </div>
                </td>
            </tr>
        `;

        // 发送请求获取数据
        const response = await fetch('/api/target_stocks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ date: date })
        });
        
        const data = await response.json();
        
        if (response.status === 404) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="px-6 py-4">
                        <div class="text-center space-y-3">
                            <p class="text-gray-500">未找到 ${date} 的目标股票数据</p>
                            <button onclick="updatePrices()" 
                                    class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors duration-200">
                                点击更新数据
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        if (!data.success) {
            throw new Error(data.error || '获取数据失败');
        }

        // 检查是否有数据
        if (!data.data || !Array.isArray(data.data) || data.data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="px-6 py-4 text-center">
                        <div class="text-gray-500 space-y-2">
                            <p>暂无数据</p>
                            <button onclick="updatePrices()" 
                                    class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors duration-200">
                                更新数据
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        // 渲染数据
        tbody.innerHTML = data.data.map((stock, index) => {
            return `
                <tr class="hover:bg-gray-50" data-original-index="${index}">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600 hover:text-blue-800">
                        <a href="javascript:void(0)" onclick="switchToTechnicalAnalysis('${stock.股票代码}')">
                            ${stock.股票代码}
                        </a>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-purple-600 hover:text-purple-800">
                        <a href="javascript:void(0)" onclick="switchToAIAnalysis('${stock.股票代码}')">
                            ${stock.股票名称}
                        </a>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${stock.所属行业 || '-'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${formatNumber(stock.最新价格)}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm ${stock.最新涨跌幅 >= 0 ? 'text-red-600' : 'text-green-600'}">
                        ${formatChangePercent(stock.最新涨跌幅)}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${formatNumber(stock.换手率)}%
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm ${getValueColor(stock.最佳胜率)} font-medium">
                        ${formatNumber(stock.最佳胜率 * 100)}%
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm ${getValueColor(stock.最佳回报)} font-medium">
                        ${formatNumber(stock.最佳回报 * 100)}%
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm ${getSharpeColor(stock.夏普比率)} font-medium">
                        ${formatNumber(stock.夏普比率)}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm ${getValueColor(stock.信号强度)} font-medium">
                        ${formatNumber(stock.信号强度 * 100)}%
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('获取目标股票数据失败:', error);
        
        const tbody = document.getElementById('targetStocksBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="px-6 py-4">
                        <div class="text-center space-y-3">
                            <p class="text-red-500">${error.message}</p>
                            <button onclick="updatePrices()" 
                                    class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors duration-200">
                                重试更新数据
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }
        
        showToast(error.message, 'error');
    }
}

// 添加辅助函数来设置数值的颜色
function getValueColor(value) {
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return 'text-gray-600';
    if (numValue >= 0.6) return 'text-green-600';
    if (numValue >= 0.5) return 'text-blue-600';
    return 'text-red-600';
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
            
            // 数比较
            if (['最新价格', '最新涨跌幅', '换手率', '最佳率', '最佳回报', '夏普比率', '信号强度'].includes(column)) {
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
    
    // 如果单元格包含接，获取链接文本
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
        '夏普比率': 8,
        '信号强度': 9
    };
    return columnMap[column] || 0;
}

// 在文档加载完成后初始化排序事件监听
document.addEventListener('DOMContentLoaded', function() {
    // 所有可排序的表头添点击件
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.getAttribute('data-sort');
            sortStocks(column);
        });
    });
});

// 添加行业分析相关函数
async function handleIndustryAnalysis(event) {
    // 如果是事件对象，则阻止默认行为
    if (event && event.preventDefault) {
        event.preventDefault();
    }
    
    // 获取日期值
    let date;
    if (typeof event === 'string') {
        date = event;
    } else {
        date = document.getElementById('industryDate').value;
    }
    
    if (!date) {
        showToast('请选择日期', 'warning');
        return;
    }
    
    const formattedDate = date.replace(/-/g, '');
    
    try {
        // 初始化标签页状态
        switchIndustryTab('report');
        
        // 显示加载状态
        const reportContent = document.getElementById('reportContent');
        const industryStocksTableBody = document.getElementById('industryStocksTableBody');
        
        reportContent.innerHTML = `
            <div class="flex justify-center items-center py-8">
                <div class="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
                <div class="ml-3 text-gray-600">正在加载分析报告...</div>
            </div>
        `;
        
        // 获取行业分析报告
        const reportResponse = await fetch('/api/industry/report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ date: formattedDate })
        });
        
        // 如果报告不存在，显示立即分析按钮
        if (reportResponse.status === 404) {
            reportContent.innerHTML = `
                <div class="text-center py-8">
                    <p class="text-gray-600 mb-4">未找到${date}的行业分析报告</p>
                    <button onclick="runIndustryAnalysis('${date}')"
                            class="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg 
                                   shadow-lg hover:shadow-xl transition-all duration-200 
                                   flex items-center justify-center space-x-2 mx-auto">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                        <span>立即分析</span>
                    </button>
                </div>
            `;
            return;
        }

        const reportData = await reportResponse.json();
        
        if (reportData.success) {
            reportContent.innerHTML = marked.parse(reportData.content);
            applyMarkdownStyles(reportContent);
        } else {
            reportContent.innerHTML = `<div class="text-red-500">${reportData.error}</div>`;
        }
        
        // 获取行业股票清单
        const stocksResponse = await fetch('/api/industry/stocks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ date: formattedDate })
        });
        
        const stocksData = await stocksResponse.json();
        
        if (stocksData.success) {
            industryStocksTableBody.innerHTML = stocksData.stocks.map(stock => `
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600 hover:text-blue-800">
                        <a href="javascript:void(0)" onclick="switchToTechnicalAnalysis('${stock.stock_code}')">
                            ${stock.stock_code}
                        </a>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-purple-600 hover:text-purple-800">
                        <a href="javascript:void(0)" onclick="switchToAIAnalysis('${stock.stock_code}')">
                            ${stock.stock_name}
                        </a>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${stock.price}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm ${parseFloat(stock.change_pct) >= 0 ? 'text-red-600' : 'text-green-600'}">
                        ${parseFloat(stock.change_pct) >= 0 ? '+' : ''}${stock.change_pct}%
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${stock.turnover_rate}%</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatAmount(stock.turnover)}</td>
                </tr>
            `).join('');
        } else {
            industryStocksTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 text-center text-red-500">
                        ${stocksData.error}
                    </td>
                </tr>
            `;
        }
        
    } catch (error) {
        console.error('获取行业分析数据失败:', error);
        showToast(error.message, 'error');
    }
}

// 修改 switchIndustryTab 函数
function switchIndustryTab(tabId) {
    // 更新标签按钮状态
    document.querySelectorAll('.industry-tab-button').forEach(button => {
        const isActive = button.getAttribute('data-tab') === tabId;
        button.classList.toggle('active', isActive);
        
        // 更新按钮样式
        if (isActive) {
            // 选中状态
            button.classList.remove('text-gray-500', 'hover:text-gray-700', 'border-transparent');
            button.classList.add(
                'text-purple-700',           // 更深的紫色文字
                'bg-purple-50',              // 浅紫色背景
                'border-b-2',                // 底部边框
                'border-purple-500',         // 紫色边框
                'font-medium'                // 加粗字体
            );
        } else {
            // 未选中状态
            button.classList.remove(
                'text-purple-700',
                'bg-purple-50',
                'border-b-2',
                'border-purple-500',
                'font-medium'
            );
            button.classList.add(
                'text-gray-600',             // 更深的灰色文字
                'hover:text-purple-600',     // 悬停时变紫色
                'hover:bg-purple-50',        // 悬停时添加浅紫色背景
                'border-transparent',        // 透明边框
                'transition-colors',         // 颜色过渡动画
                'duration-200'               // 动画持续时间
            );
        }
    });

    // 更新内容显示
    document.querySelectorAll('.industry-tab-content').forEach(content => {
        const isSelected = content.id === `${tabId}Tab`;
        if (isSelected) {
            content.classList.remove('hidden');
            requestAnimationFrame(() => {
                content.style.opacity = '1';
                content.style.transform = 'translateY(0)';
            });
        } else {
            content.style.opacity = '0';
            content.style.transform = 'translateY(10px)';
            setTimeout(() => {
                content.classList.add('hidden');
            }, 300);
        }
    });
}

// 金额格式化函数
function formatAmount(amount) {
    const num = parseFloat(amount);
    if (num >= 100000000) {
        return (num / 100000000).toFixed(2) + '亿';
    } else if (num >= 10000) {
        return (num / 10000).toFixed(2) + '万';
    }
    return num.toFixed(2);
}

// 在文档加载完成后添加事件监听
document.addEventListener('DOMContentLoaded', function() {
    // ... 现有的初始化代码 ...
    
    // 添加行业分析表单提交事件监听
    const industryAnalysisForm = document.getElementById('industryAnalysisForm');
    if (industryAnalysisForm) {
        industryAnalysisForm.addEventListener('submit', handleIndustryAnalysis);
    }
    
    // 添加标签页切换事件监听
    document.querySelectorAll('.industry-tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            switchIndustryTab(tabId);
        });
    });
    
    // 初始化显示第一个标签页
    const firstIndustryTab = document.querySelector('.industry-tab-button');
    if (firstIndustryTab) {
        const defaultTabId = firstIndustryTab.getAttribute('data-tab');
        switchIndustryTab(defaultTabId);
    }
});

// 添加个股分析处理函数
async function handleStockAnalysis(event) {
    event.preventDefault();
    
    const symbol = document.getElementById('analysisSymbol').value;
    const date = document.getElementById('analysisDate').value;
    
    if (!symbol || !date) {
        showToast('请输入股票代码和选择日期', 'warning');
        return;
    }
    
    try {
        // 显示加载状态
        const resultsDiv = document.getElementById('stockAnalysisResults');
        const analysisContent = document.getElementById('analysisContent');
        
        if (!resultsDiv || !analysisContent) {
            showToast('页面元素不存在', 'error');
            return;
        }
        
        analysisContent.innerHTML = `
            <div class="flex justify-center items-center py-8">
                <div class="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
                <div class="ml-3 text-gray-600">正在分析数据...</div>
            </div>
        `;
        resultsDiv.classList.remove('hidden');
        
        // 发送分析请求
        const response = await fetch('/api/stock/analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                date: date
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `请求失败: ${response.status}`);
        }
        
        if (!data.success) {
            throw new Error(data.error || '分析失败，请重试');
        }
        
        // 更新股票信息
        document.getElementById('analysisStockName').textContent = data.stockName;
        document.getElementById('analysisStockCode').textContent = `股票代码：${symbol}`;
        
        // 使用 markdown-it 处理分析报告
        const md = window.markdownit({
            html: true,
            linkify: true,
            typographer: true,
            highlight: function (str, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(str, { language: lang }).value;
                    } catch (__) {}
                }
                return ''; // 使用默认的转义
            }
        });

        // 添加插件支持
        md.use(window.markdownitEmoji);
        md.use(window.markdownitFootnote);
        md.use(window.markdownitTaskLists);

        // 渲染markdown内容
        analysisContent.innerHTML = md.render(data.content);
        
    } catch (error) {
        console.error('个股分析失败:', error);
        const analysisContent = document.getElementById('analysisContent');
        if (analysisContent) {
            analysisContent.innerHTML = `
                <div class="text-red-500 text-center p-4">
                    ${error.message || '分析失败，请重试'}
                </div>
            `;
        }
        showToast(error.message, 'error');
    }
}

// 添加发送后续问题的函数
async function sendFollowupQuestion() {
    const followupInput = document.getElementById('followupQuestion');
    const question = followupInput.value.trim();
    const model = document.getElementById('modelSelect').value;
    
    if (!question) {
        showToast('请输入问题', 'warning');
        return;
    }
    
    const contentDiv = document.getElementById('analysisContent');
    const symbolInput = document.getElementById('analysisSymbol');
    
    // 创建用户问题容器
    const questionContainer = document.createElement('div');
    questionContainer.className = 'chat-message user-message mb-4';
    questionContainer.innerHTML = `
        <div class="bg-blue-50 rounded-lg p-3">
            <p class="text-blue-800">${question}</p>
        </div>
    `;
    contentDiv.appendChild(questionContainer);
    
    // 创建AI回复容器
    const responseContainer = document.createElement('div');
    responseContainer.className = 'ai-message bg-white rounded-lg shadow-sm p-4 mb-4';
    responseContainer.innerHTML = `
        <div class="message-header">
            <div class="flex items-center">
                <span class="ai-icon text-xl mr-2">🤖</span>
                <span class="text-sm text-gray-500">AI助手</span>
            </div>
            <button class="copy-btn flex items-center space-x-1" onclick="copyMessage(this)">
                <i class="fas fa-copy"></i>
                <span>复制</span>
            </button>
        </div>
        <div class="message-content mt-2 prose prose-indigo max-w-none" data-raw-content=""></div>
    `;
    contentDiv.appendChild(responseContainer);
    
    // 获取消息内容区域的引用
    const messageContent = responseContainer.querySelector('.message-content');
    messageContent.innerHTML = '<div class="typing">正在思考，请稍候...</div>';
    
    // 清空输入框
    followupInput.value = '';
    
    try {
        // 将用户问题添加到对话历史
        conversationHistory.push({
            role: "user",
            content: question
        });

        const response = await fetch('/api/followup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbolInput.value,
                model: model,
                question: question,
                conversation_history: conversationHistory
            })
        });

        // 检查响应状态
        if (!response.ok) {
            throw new Error(`请求失败: ${response.status}`);
        }

        // 检查响应头
        const contentType = response.headers.get('content-type');
        console.log('响应Content-Type:', contentType);

        console.log('开始处理响应流');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        
        // 清除 "正在思考" 的提示
        messageContent.innerHTML = '';
        
        while (true) {
            const {value, done} = await reader.read();
            
            // 检查每次读取的状态
            console.log('读取状态:', { done, hasValue: !!value });
            
            if (done) {
                console.log('响应流结束，完整文本:', fullText);
                if (!fullText) {
                    messageContent.innerHTML = `
                        <div class="text-red-500">
                            未收到任何响应内容
                        </div>
                    `;
                }
                break;
            }
            
            const chunk = decoder.decode(value);
            console.log('原始数据块:', chunk);
            
            // 直接将收到的文本添加到 fullText
            fullText += chunk;
            
            // 使用 markdown-it 处理完整的文本内容
            const md = window.markdownit({
                html: true,
                linkify: true,
                typographer: true,
                highlight: function (str, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(str, { language: lang }).value;
                        } catch (__) {}
                    }
                    return ''; // 使用默认的转义
                }
            });

            // 添加插件支持
            md.use(window.markdownitEmoji);
            md.use(window.markdownitFootnote);
            md.use(window.markdownitTaskLists);

            // 渲染markdown内容
            messageContent.innerHTML = md.render(fullText);
            messageContent.setAttribute('data-raw-content', fullText);
            
            // 应用 Markdown 样式
            applyMarkdownStyles(messageContent);
            
            // 应用代码高亮
            if (window.Prism) {
                Prism.highlightAllUnder(messageContent);
            }
            
            // 滚动到底部
            contentDiv.scrollTop = contentDiv.scrollHeight;
        }
        
        // 检查最终结果
        if (fullText) {
            // 将AI回复添加到对话历史
            conversationHistory.push({
                role: "assistant",
                content: fullText
            });
        }
        
    } catch (error) {
        console.error('追问请求失败:', error);
        messageContent.innerHTML = `
            <div class="text-red-500">
                请求失败: ${error.message}
            </div>
        `;
        showToast(error.message, 'error');
    }
}

// 确保事件监听器只绑定一次
document.addEventListener('DOMContentLoaded', function() {
    const followupForm = document.getElementById('followupForm');
    if (followupForm) {
        // 移除所有现有的事件监听器
        const newForm = followupForm.cloneNode(true);
        followupForm.parentNode.replaceChild(newForm, followupForm);
        
        // 添加新的事件监听器
        newForm.addEventListener('submit', function(event) {
            event.preventDefault();
            sendFollowupQuestion();
        });
    }
});

function copyMessage(button) {
    // 获取消息容器
    const messageContent = button.closest('.ai-message').querySelector('.message-content');
    // 获取原始内容
    const rawContent = messageContent.getAttribute('data-raw-content');
    
    // 复制到剪贴板
    navigator.clipboard.writeText(rawContent || messageContent.textContent).then(() => {
        // 临时改变按钮文字显示复制成功
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> 已复制';
        
        // 显示成功提示
        showToast('复制成功', 'success');
        
        setTimeout(() => {
            button.innerHTML = originalText;
        }, 2000);
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败，请重试', 'error');
    });
}

// ... 现有代码 ...

// 修改标题样式
const titleStyles = document.createElement('style');
titleStyles.textContent = `
    /* 关键信息标题样式 */
    .key-info-title {
        display: flex;
        align-items: center;
        width: 100%;
        margin: 1.5rem 0 1rem;
        padding: 0.5rem 1rem;
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        font-size: 1.125rem;
        font-weight: 600;
        color: #1e293b;
    }

    /* 关键信息内容容器 */
    .key-info-content {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: 1rem;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        margin-bottom: 1.5rem;
    }

    /* 关键信息项样式 */
    .key-info-item {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        padding: 0.5rem;
        border-bottom: 1px dashed #e2e8f0;
    }

    .key-info-item:last-child {
        border-bottom: none;
    }

    /* 关键信息标签样式 */
    .key-info-label {
        flex-shrink: 0;
        font-weight: 600;
        color: #475569;
        min-width: 4rem;
    }

    /* 关键信息值样式 */
    .key-info-value {
        flex: 1;
        color: #1e293b;
        line-height: 1.5;
    }

    /* 利好信息样式 */
    .positive-info {
        color: #059669;
    }

    /* 利空信息样式 */
    .negative-info {
        color: #dc2626;
    }

    /* 中性信息样式 */
    .neutral-info {
        color: #6366f1;
    }
`;
document.head.appendChild(titleStyles);

// 修改创建标题和内容的函数
function createKeyInfoSection(title, items) {
    const section = document.createElement('div');
    section.className = 'key-info-section';

    // 创建标题
    const titleElement = document.createElement('div');
    titleElement.className = 'key-info-title';
    titleElement.textContent = title;
    section.appendChild(titleElement);

    // 创建内容容器
    const content = document.createElement('div');
    content.className = 'key-info-content';

    // 添加每个信息项
    items.forEach(item => {
        const itemElement = document.createElement('div');
        itemElement.className = 'key-info-item';

        const label = document.createElement('span');
        label.className = 'key-info-label';
        label.textContent = item.label;

        const value = document.createElement('span');
        value.className = `key-info-value ${item.type || ''}`;
        value.textContent = item.value;

        itemElement.appendChild(label);
        itemElement.appendChild(value);
        content.appendChild(itemElement);
    });

    section.appendChild(content);
    return section;
}

// 添加格式化技术指标的函数
function formatTechnicalIndicators(indicators) {
    if (!indicators) return '暂无技术指标数据';
    
    return `
### 趋势指标
- MACD: ${indicators.MACD || 'N/A'}
- KDJ: ${indicators.KDJ || 'N/A'}
- RSI: ${indicators.RSI || 'N/A'}

### 支撑压力
- 支撑位: ${indicators.support || 'N/A'}
- 压力位: ${indicators.resistance || 'N/A'}
- BOLL带: ${indicators.BOLL || 'N/A'}

### 成交量
- 量比: ${indicators.volumeRatio || 'N/A'}
- 主力资金: ${indicators.mainForce || 'N/A'}
    `;
}

// 添加格式化交易信号的函数
function formatTradeSignals(signals) {
    if (!signals) return '暂无交易信号数据';
    
    const currentSignal = signals.currentSignal || '无明确信号';
    const trendStrength = signals.trendStrength || 'N/A';
    const reliability = signals.reliability || 'N/A';
    const recentSignals = signals.recentSignals || [];
    
    return `
### 当前信号
${currentSignal}

### 信号强度
- 趋势强度: ${trendStrength}
- 信号可信度: ${reliability}

### 近期信号
${recentSignals.length > 0 ? recentSignals.join('\n') : '暂无近期信号'}
    `;
}

// 添加获取信号标签的函数
function getSignalTag(signal) {
    if (!signal) return '观望';
    
    const signalMap = {
        'buy': '买入',
        'sell': '卖出',
        'hold': '持有',
        'watch': '观望'
    };
    
    return signalMap[signal.toLowerCase()] || signal;
}

// 添加获取信号类型的函数
function getSignalType(signal) {
    if (!signal) return 'warning';
    
    const typeMap = {
        'buy': 'success',
        'sell': 'error',
        'hold': 'info',
        'watch': 'warning'
    };
    
    return typeMap[signal.toLowerCase()] || 'warning';
}

// 添加创建标题的函数
function createTitle(text, level = 1) {
    const title = document.createElement('div');
    title.className = `content-title content-title-h${level} animate-slide-down`;
    title.textContent = text;
    return title;
}

// 添加创建内容块的函数
function createContentBlock(content, tags = []) {
    const block = document.createElement('div');
    block.className = 'content-block animate-slide-down';
    
    // 添加标签
    if (tags.length > 0) {
        const tagsContainer = document.createElement('div');
        tagsContainer.className = 'mb-3';
        tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = `content-tag tag-${tag.type || 'info'}`;
            tagElement.textContent = tag.text;
            tagsContainer.appendChild(tagElement);
        });
        block.appendChild(tagsContainer);
    }
    
    // 添加内容
    const contentElement = document.createElement('div');
    contentElement.className = 'prose prose-indigo max-w-none';
    contentElement.innerHTML = marked.parse(content);
    block.appendChild(contentElement);
    
    return block;
}

// 保留这些辅助函数，因为它们仍然需要用来格式化显示
function getSignalColor(score) {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-blue-500';
    if (score >= 40) return 'bg-yellow-500';
    if (score >= 20) return 'bg-orange-500';
    return 'bg-red-500';
}

function getSignalDescription(score) {
    if (score >= 80) return '强烈';
    if (score >= 60) return '较强';
    if (score >= 40) return '中等';
    if (score >= 20) return '较弱';
    return '微弱';
}

// 添加辅助函数来格式化参数名称
function formatParamName(key) {
    // 只显示这些参数
    const nameMap = {
        'period': '周期',
        'mult': '倍数',
        'strength_threshold': '信号阈值'
    };
    
    // 如果参数不在映射表中，返回空字符串，这样这个参数就不会显示
    return nameMap[key] || '';
}

// 修改 formatParamValue 函数，添加 key 参数
function formatParamValue(value, key) {  // 添加 key 参数
    if (typeof value === 'number') {
        if (key === 'strength_threshold') {
            return Math.round(value); // 信号阈值显示整数
        }
        return Number.isInteger(value) ? value : value.toFixed(2);
    }
    return value;
}

// 添加获取参数单位的辅助函数
function getParamUnit(key) {
    const units = {
        'period': '<span class="ml-2 text-sm text-gray-500">天</span>',
        'mult': '<span class="ml-2 text-sm text-gray-500">倍</span>',
        'strength_threshold': '<span class="ml-2 text-sm text-gray-500">%</span>'
    };
    return units[key] || '';
}

// 添加获取参数图标的辅助函数
function getParamIcon(key) {
    const icons = {
        'period': `
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
        `,
        'mult': `
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
            </svg>
        `,
        'strength_threshold': `
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
            </svg>
        `
    };
    return icons[key] || '';
}
