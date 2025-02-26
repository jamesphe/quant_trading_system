// 日期格式化和验证工具函数
export function formatDate(date) {
    return date.toISOString().split('T')[0];
}

export function formatDisplayDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}年${month}月${day}日`;
}

export function formatDateToYYYYMMDD(dateStr) {
    return dateStr.replace(/-/g, '');
}

export function getToday() {
    return new Date();
}

export function getYesterday() {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday;
}

export function getLastYear() {
    const today = new Date();
    return new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
} 