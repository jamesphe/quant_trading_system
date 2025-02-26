import { getToday, getYesterday, getLastYear } from '../utils/dateUtils.js';

export const datePickerConfigs = [
    {
        inputId: 'pickDate',
        defaultDate: getToday(),
        maxDate: getToday(),
        onChange: (date, dateString) => {
            console.log('每日选股日期已更改:', dateString);
            updateDailyPicks(dateString);
        }
    },
    {
        inputId: 'analysisDate',
        defaultDate: getToday(),
        maxDate: getToday(),
        onChange: (date, dateString) => {
            console.log('分析日期已更改:', dateString);
            updateAnalysis(dateString);
        }
    },
    {
        inputId: 'startDate',
        defaultDate: getLastYear(),
        maxDate: getToday(),
        onChange: (date, dateString) => {
            console.log('开始日期已更改:', dateString);
        }
    },
    {
        inputId: 'endDate',
        defaultDate: getToday(),
        maxDate: getToday(),
        onChange: (date, dateString) => {
            console.log('结束日期已更改:', dateString);
        }
    },
    {
        inputId: 'targetDate',
        defaultDate: getYesterday(),
        onChange: (date, dateString) => {
            console.log('目标股票日期已更改:', dateString);
            updateTargetStocks(dateString);
        }
    },
    {
        inputId: 'industryDate',
        defaultDate: getToday(),
        maxDate: getToday(),
        onChange: (date, dateString) => {
            console.log('行业分析日期已更改:', dateString);
            handleIndustryAnalysis(dateString);
        }
    }
]; 