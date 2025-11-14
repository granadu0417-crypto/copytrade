// API 기본 URL
const API_BASE = '';

// 자동 새로고침 간격 (밀리초)
const REFRESH_INTERVAL = 5000; // 5초

// 새로고침 타이머
let refreshTimer = null;

// 페이지 로드시 초기화
document.addEventListener('DOMContentLoaded', () => {
    console.log('카피트레이딩 대시보드 초기화');

    // 버튼 이벤트 리스너
    document.getElementById('btn-start').addEventListener('click', startTrading);
    document.getElementById('btn-stop').addEventListener('click', stopTrading);
    document.getElementById('btn-emergency').addEventListener('click', emergencyStop);
    document.getElementById('btn-refresh').addEventListener('click', refreshAll);

    // 초기 데이터 로드
    refreshAll();

    // 자동 새로고침 시작
    startAutoRefresh();
});

// ===== API 호출 함수 =====

async function apiGet(endpoint) {
    try {
        const response = await fetch(`${API_BASE}/api${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API GET 오류 (${endpoint}):`, error);
        showError(`데이터 로드 실패: ${endpoint}`);
        return null;
    }
}

async function apiPost(endpoint, data = null) {
    try {
        const options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`${API_BASE}/api${endpoint}`, options);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API POST 오류 (${endpoint}):`, error);
        showError(error.message);
        return null;
    }
}

// ===== 데이터 로드 함수 =====

async function loadSystemStatus() {
    const data = await apiGet('/status');
    if (!data) return;

    // 시스템 상태 뱃지 업데이트
    const statusBadge = document.getElementById('status-badge');
    const isRunning = data.system?.is_running;

    if (isRunning) {
        statusBadge.textContent = '실행 중';
        statusBadge.className = 'badge badge-active';
    } else {
        statusBadge.textContent = '중지됨';
        statusBadge.className = 'badge badge-inactive';
    }

    // 통계 업데이트
    updateStat('balance', formatMoney(data.account?.balance || 0));
    updateStat('available-balance', formatMoney(data.account?.available_balance || 0));
    updateStat('unrealized-pnl', formatMoney(data.account?.unrealized_pnl || 0), data.account?.unrealized_pnl);

    const openCount = data.positions?.open_count || 0;
    const maxPositions = data.positions?.max_positions || 5;
    updateStat('active-positions', `${openCount}/${maxPositions}`);

    // 리스크 정보
    if (data.risk) {
        const todayPnl = data.risk.today_pnl || 0;
        updateStat('today-pnl', formatMoney(todayPnl), todayPnl);
    }
}

async function loadPositions() {
    const data = await apiGet('/positions');
    if (!data) return;

    const tbody = document.getElementById('positions-tbody');

    if (!data.positions || data.positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="empty-state">포지션이 없습니다</td></tr>';
        return;
    }

    tbody.innerHTML = data.positions.map(pos => `
        <tr>
            <td><strong>${pos.symbol || '-'}</strong></td>
            <td class="position-${(pos.side || '').toLowerCase()}">${pos.side || '-'}</td>
            <td>${formatPrice(pos.entry_price)}</td>
            <td>${formatPrice(pos.current_price)}</td>
            <td>${formatNumber(pos.quantity)}</td>
            <td>${pos.leverage || '-'}x</td>
            <td class="${getPnlClass(pos.pnl_pct)}">${formatPercent(pos.pnl_pct)}</td>
            <td class="${getPnlClass(pos.pnl_usdt)}">${formatMoney(pos.pnl_usdt)}</td>
            <td>${pos.status || '-'}</td>
            <td>
                <button class="btn btn-close btn-small" onclick="closePosition(${pos.id})">청산</button>
            </td>
        </tr>
    `).join('');
}

async function loadTraders() {
    const data = await apiGet('/traders');
    if (!data) return;

    const tbody = document.getElementById('traders-tbody');

    if (!data.traders || data.traders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">트레이더 데이터가 없습니다</td></tr>';
        updateStat('tracked-traders', '0');
        return;
    }

    updateStat('tracked-traders', data.count);

    tbody.innerHTML = data.traders.map(trader => `
        <tr>
            <td><strong>${trader.nickname || '-'}</strong></td>
            <td>${trader.binance_uid || '-'}</td>
            <td class="${getPnlClass(trader.roi_7d)}">${formatPercent(trader.roi_7d)}</td>
            <td class="${getPnlClass(trader.roi_30d)}">${formatPercent(trader.roi_30d)}</td>
            <td>${formatPercent(trader.win_rate)}</td>
            <td>${formatNumber(trader.followers)}</td>
            <td>${trader.is_active ? '✅ 활성' : '❌ 비활성'}</td>
        </tr>
    `).join('');
}

async function loadAlerts() {
    const data = await apiGet('/alerts');
    if (!data) return;

    const container = document.getElementById('alerts-container');

    if (!data.alerts || data.alerts.length === 0) {
        container.innerHTML = '<p class="empty-state">알림이 없습니다</p>';
        return;
    }

    container.innerHTML = data.alerts.map(alert => `
        <div class="alert-item alert-${alert.severity.toLowerCase()}">
            <strong>${alert.alert_type || '알림'}</strong>
            <p>${alert.message || '-'}</p>
            <div class="alert-time">${formatDateTime(alert.created_at)}</div>
        </div>
    `).join('');
}

// ===== 시스템 제어 함수 =====

async function startTrading() {
    if (!confirm('자동 거래를 시작하시겠습니까?')) return;

    const result = await apiPost('/control/start');
    if (result) {
        showSuccess('자동 거래가 시작되었습니다');
        refreshAll();
    }
}

async function stopTrading() {
    if (!confirm('자동 거래를 중지하시겠습니까?')) return;

    const result = await apiPost('/control/stop');
    if (result) {
        showSuccess('자동 거래가 중지되었습니다');
        refreshAll();
    }
}

async function emergencyStop() {
    if (!confirm('⚠️ 긴급 정지하시겠습니까?\n모든 포지션이 즉시 청산됩니다!')) return;
    if (!confirm('정말로 긴급 정지하시겠습니까?')) return;

    const result = await apiPost('/control/emergency');
    if (result) {
        showSuccess('긴급 정지 완료 - 모든 포지션이 청산되었습니다');
        refreshAll();
    }
}

async function closePosition(tradeId) {
    if (!confirm(`포지션 #${tradeId}를 청산하시겠습니까?`)) return;

    const result = await apiPost(`/positions/${tradeId}/close`, { reason: 'MANUAL' });
    if (result) {
        showSuccess(`포지션 #${tradeId} 청산 완료`);
        refreshAll();
    }
}

// ===== UI 업데이트 함수 =====

function updateStat(elementId, value, numericValue = null) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = value;

    // PnL 색상 적용
    if (numericValue !== null) {
        element.className = 'stat-value';
        if (numericValue > 0) {
            element.classList.add('positive');
        } else if (numericValue < 0) {
            element.classList.add('negative');
        }
    }
}

function refreshAll() {
    loadSystemStatus();
    loadPositions();
    loadTraders();
    loadAlerts();

    // 마지막 업데이트 시간
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString('ko-KR');
}

function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    refreshTimer = setInterval(refreshAll, REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

// ===== 유틸리티 함수 =====

function formatMoney(value) {
    if (value === null || value === undefined) return '-';
    const num = parseFloat(value);
    if (isNaN(num)) return '-';
    return `$${num.toFixed(2)}`;
}

function formatPrice(value) {
    if (value === null || value === undefined) return '-';
    const num = parseFloat(value);
    if (isNaN(num)) return '-';
    return num.toFixed(2);
}

function formatPercent(value) {
    if (value === null || value === undefined) return '-';
    const num = parseFloat(value);
    if (isNaN(num)) return '-';
    return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`;
}

function formatNumber(value) {
    if (value === null || value === undefined) return '-';
    const num = parseFloat(value);
    if (isNaN(num)) return '-';
    return num.toLocaleString('ko-KR');
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleString('ko-KR');
    } catch (e) {
        return dateString;
    }
}

function getPnlClass(value) {
    if (value === null || value === undefined) return '';
    const num = parseFloat(value);
    if (isNaN(num)) return '';
    return num > 0 ? 'positive' : num < 0 ? 'negative' : '';
}

function showSuccess(message) {
    alert(`✅ ${message}`);
}

function showError(message) {
    alert(`❌ 오류: ${message}`);
}

// 페이지 언로드시 타이머 정리
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});
