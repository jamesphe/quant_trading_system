import { formatDate, formatDisplayDate } from '../utils/dateUtils.js';

export class DatePicker {
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
        this.displayInput = document.getElementById(this.options.inputId);
        if (!this.displayInput) {
            console.error(`未找到ID为 ${this.options.inputId} 的输入元素`);
            return;
        }

        // 初始化日期选择器
        this.setDate(this.options.defaultDate);
        this.attachEventListeners();
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
        const formattedDate = formatDate(date);
        this.displayInput.value = formattedDate;
        
        if (this.options.onChange) {
            this.options.onChange(date, formattedDate);
        }
    }

    getDate() {
        return this.displayInput.value ? new Date(this.displayInput.value) : null;
    }

    attachEventListeners() {
        this.displayInput.addEventListener('change', (e) => {
            const date = new Date(e.target.value);
            if (this.validateDateRange(date)) {
                this.setDate(date);
            }
        });
    }
} 