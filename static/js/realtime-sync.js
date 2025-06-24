/**
 * リアルタイム同期システム - フロントエンド WebSocket 接続
 * 
 * カリキュラム・単元の同期状況をリアルタイムで表示
 */

class RealtimeSyncClient {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.connectionRetries = 0;
        this.maxRetries = 5;
        this.retryDelay = 3000; // 3秒
        this.currentCurriculumId = null;
        this.notificationQueue = [];
        this.syncStatusCallbacks = new Map();
        
        // UI要素の初期化
        this.initializeUI();
        
        // 接続開始
        this.connect();
    }
    
    /**
     * UI要素の初期化
     */
    initializeUI() {
        // 同期ステータス表示エリア
        if (!document.getElementById('sync-status-container')) {
            const statusContainer = document.createElement('div');
            statusContainer.id = 'sync-status-container';
            statusContainer.className = 'realtime-sync-status';
            statusContainer.innerHTML = `
                <div id="sync-connection-status" class="sync-connection-status disconnected">
                    <i class="fas fa-circle"></i>
                    <span>接続中...</span>
                </div>
                <div id="sync-notifications" class="sync-notifications"></div>
            `;
            document.body.appendChild(statusContainer);
        }
        
        // CSS スタイルの追加
        this.addStyles();
    }
    
    /**
     * CSS スタイルの追加
     */
    addStyles() {
        if (document.getElementById('realtime-sync-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'realtime-sync-styles';
        styles.textContent = `
            .realtime-sync-status {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            }
            
            .sync-connection-status {
                background: #fff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 12px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9rem;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
            }
            
            .sync-connection-status.connected {
                border-color: #28a745;
                background-color: #d4edda;
                color: #155724;
            }
            
            .sync-connection-status.disconnected {
                border-color: #dc3545;
                background-color: #f8d7da;
                color: #721c24;
            }
            
            .sync-connection-status.connecting {
                border-color: #ffc107;
                background-color: #fff3cd;
                color: #856404;
            }
            
            .sync-connection-status .fas {
                font-size: 0.8rem;
            }
            
            .sync-connection-status.connected .fas {
                color: #28a745;
                animation: pulse 2s infinite;
            }
            
            .sync-connection-status.disconnected .fas {
                color: #dc3545;
            }
            
            .sync-connection-status.connecting .fas {
                color: #ffc107;
                animation: spin 1s linear infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            
            .sync-notifications {
                max-height: 300px;
                overflow-y: auto;
            }
            
            .sync-notification {
                background: #fff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                animation: slideInRight 0.3s ease;
                position: relative;
            }
            
            .sync-notification.success {
                border-left: 4px solid #28a745;
                background-color: #f8fff9;
            }
            
            .sync-notification.info {
                border-left: 4px solid #17a2b8;
                background-color: #f7fdff;
            }
            
            .sync-notification.warning {
                border-left: 4px solid #ffc107;
                background-color: #fffdf7;
            }
            
            .sync-notification.error {
                border-left: 4px solid #dc3545;
                background-color: #fff7f7;
            }
            
            .sync-notification-header {
                display: flex;
                justify-content: between;
                align-items: flex-start;
                margin-bottom: 8px;
            }
            
            .sync-notification-title {
                font-weight: 600;
                font-size: 0.9rem;
                margin: 0;
                flex-grow: 1;
            }
            
            .sync-notification-time {
                font-size: 0.8rem;
                color: #6c757d;
                margin-left: 10px;
            }
            
            .sync-notification-close {
                background: none;
                border: none;
                font-size: 1.2rem;
                color: #6c757d;
                cursor: pointer;
                padding: 0;
                margin-left: 10px;
                line-height: 1;
            }
            
            .sync-notification-close:hover {
                color: #495057;
            }
            
            .sync-notification-message {
                font-size: 0.85rem;
                color: #495057;
                margin-bottom: 8px;
            }
            
            .sync-notification-progress {
                background-color: #e9ecef;
                border-radius: 4px;
                height: 6px;
                margin-top: 8px;
                overflow: hidden;
            }
            
            .sync-notification-progress-bar {
                background-color: #007bff;
                height: 100%;
                transition: width 0.3s ease;
            }
            
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            .sync-notification-fade-out {
                animation: fadeOut 0.3s ease forwards;
            }
            
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; transform: translateX(100%); }
            }
            
            /* レスポンシブ対応 */
            @media (max-width: 768px) {
                .realtime-sync-status {
                    top: 10px;
                    right: 10px;
                    left: 10px;
                    max-width: none;
                }
                
                .sync-notification {
                    padding: 10px;
                }
            }
        `;
        
        document.head.appendChild(styles);
    }
    
    /**
     * WebSocket接続
     */
    connect() {
        if (this.socket && this.isConnected) {
            return;
        }
        
        this.updateConnectionStatus('connecting', '接続中...');
        
        try {
            // Socket.IOクライアントの初期化
            this.socket = io({
                transports: ['websocket', 'polling'],
                autoConnect: true,
                reconnection: true,
                reconnectionAttempts: this.maxRetries,
                reconnectionDelay: this.retryDelay
            });
            
            // イベントリスナーの設定
            this.setupEventListeners();
            
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.updateConnectionStatus('disconnected', '接続エラー');
            this.scheduleReconnect();
        }
    }
    
    /**
     * イベントリスナーの設定
     */
    setupEventListeners() {
        // 接続確立
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.connectionRetries = 0;
            this.updateConnectionStatus('connected', 'リアルタイム同期接続中');
            
            // 現在のページでカリキュラム同期が必要な場合は参加
            this.joinCurrentCurriculumSync();
        });
        
        // 切断
        this.socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason);
            this.isConnected = false;
            this.updateConnectionStatus('disconnected', '接続が切断されました');
        });
        
        // 再接続試行
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.connectionRetries++;
            
            if (this.connectionRetries >= this.maxRetries) {
                this.updateConnectionStatus('disconnected', '接続に失敗しました');
            } else {
                this.updateConnectionStatus('connecting', `再接続中... (${this.connectionRetries}/${this.maxRetries})`);
            }
        });
        
        // 同期ステータス通知
        this.socket.on('sync_status', (data) => {
            this.handleSyncStatus(data);
        });
        
        // 同期通知
        this.socket.on('sync_notification', (data) => {
            this.handleSyncNotification(data);
        });
        
        // 単元更新通知
        this.socket.on('unit_update_notification', (data) => {
            this.handleUnitUpdateNotification(data);
        });
    }
    
    /**
     * 現在のカリキュラム同期ルームに参加
     */
    joinCurrentCurriculumSync() {
        // ページURLからカリキュラムIDを取得
        const curriculumId = this.extractCurriculumIdFromURL();
        if (curriculumId) {
            this.joinCurriculumSync(curriculumId);
        }
    }
    
    /**
     * カリキュラム同期ルームに参加
     */
    joinCurriculumSync(curriculumId) {
        if (!this.isConnected || !curriculumId) return;
        
        this.currentCurriculumId = curriculumId;
        this.socket.emit('join_curriculum_sync', { curriculum_id: curriculumId });
        console.log(`Joined curriculum sync room: ${curriculumId}`);
    }
    
    /**
     * カリキュラム同期ルームから退出
     */
    leaveCurriculumSync(curriculumId) {
        if (!this.isConnected || !curriculumId) return;
        
        this.socket.emit('leave_curriculum_sync', { curriculum_id: curriculumId });
        
        if (this.currentCurriculumId === curriculumId) {
            this.currentCurriculumId = null;
        }
        
        console.log(`Left curriculum sync room: ${curriculumId}`);
    }
    
    /**
     * URLからカリキュラムIDを抽出
     */
    extractCurriculumIdFromURL() {
        const path = window.location.pathname;
        
        // パターン: /teacher/curriculum/{id}/...
        const curriculumMatch = path.match(/\/teacher\/curriculum\/(\d+)/);
        if (curriculumMatch) {
            return parseInt(curriculumMatch[1]);
        }
        
        // パターン: curriculum_id=... in query params
        const urlParams = new URLSearchParams(window.location.search);
        const curriculumIdParam = urlParams.get('curriculum_id');
        if (curriculumIdParam) {
            return parseInt(curriculumIdParam);
        }
        
        return null;
    }
    
    /**
     * 同期ステータス処理
     */
    handleSyncStatus(data) {
        console.log('Sync status received:', data);
        
        // コールバック実行
        if (this.syncStatusCallbacks.has(data.type)) {
            this.syncStatusCallbacks.get(data.type)(data);
        }
    }
    
    /**
     * 同期通知処理
     */
    handleSyncNotification(data) {
        console.log('Sync notification received:', data);
        
        let notificationType = 'info';
        let title = '同期通知';
        
        switch (data.type) {
            case 'sync_started':
                notificationType = 'info';
                title = '同期開始';
                break;
            case 'sync_progress':
                notificationType = 'info';
                title = '同期進行中';
                break;
            case 'sync_completed':
                notificationType = data.result?.success ? 'success' : 'error';
                title = data.result?.success ? '同期完了' : '同期エラー';
                break;
            case 'sync_conflict':
                notificationType = 'warning';
                title = '同期競合';
                break;
        }
        
        this.showNotification({
            type: notificationType,
            title: title,
            message: data.message,
            data: data,
            autoHide: notificationType !== 'warning' && notificationType !== 'error'
        });
        
        // ページの同期ステータス表示を更新
        this.updatePageSyncStatus(data);
    }
    
    /**
     * 単元更新通知処理
     */
    handleUnitUpdateNotification(data) {
        console.log('Unit update notification received:', data);
        
        this.showNotification({
            type: 'success',
            title: '学習単元更新',
            message: data.message,
            data: data,
            autoHide: true
        });
        
        // 学習ポータル画面なら自動更新
        if (window.location.pathname.includes('/student/learning_portal')) {
            this.refreshLearningPortal();
        }
    }
    
    /**
     * 通知表示
     */
    showNotification(options) {
        const {
            type = 'info',
            title = '通知',
            message = '',
            data = {},
            autoHide = true,
            duration = 5000
        } = options;
        
        const notificationId = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const notification = document.createElement('div');
        notification.id = notificationId;
        notification.className = `sync-notification ${type}`;
        
        notification.innerHTML = `
            <div class="sync-notification-header">
                <h5 class="sync-notification-title">${this.escapeHtml(title)}</h5>
                <span class="sync-notification-time">${new Date().toLocaleTimeString()}</span>
                <button class="sync-notification-close" onclick="realtimeSync.hideNotification('${notificationId}')">&times;</button>
            </div>
            <div class="sync-notification-message">${this.escapeHtml(message)}</div>
            ${data.progress ? `
                <div class="sync-notification-progress">
                    <div class="sync-notification-progress-bar" style="width: ${data.progress.percentage || 0}%"></div>
                </div>
            ` : ''}
        `;
        
        const container = document.getElementById('sync-notifications');
        container.appendChild(notification);
        
        // 自動非表示
        if (autoHide) {
            setTimeout(() => {
                this.hideNotification(notificationId);
            }, duration);
        }
        
        // 最大表示数制限
        this.limitNotifications();
    }
    
    /**
     * 通知を非表示
     */
    hideNotification(notificationId) {
        const notification = document.getElementById(notificationId);
        if (notification) {
            notification.classList.add('sync-notification-fade-out');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }
    
    /**
     * 通知数制限
     */
    limitNotifications(maxCount = 5) {
        const container = document.getElementById('sync-notifications');
        const notifications = container.children;
        
        while (notifications.length > maxCount) {
            const oldest = notifications[0];
            this.hideNotification(oldest.id);
        }
    }
    
    /**
     * 接続ステータス更新
     */
    updateConnectionStatus(status, message) {
        const statusElement = document.getElementById('sync-connection-status');
        if (statusElement) {
            statusElement.className = `sync-connection-status ${status}`;
            statusElement.querySelector('span').textContent = message;
        }
    }
    
    /**
     * ページの同期ステータス更新
     */
    updatePageSyncStatus(data) {
        // カリキュラム編集ページの同期ステータス表示を更新
        const syncStatusElements = document.querySelectorAll('.curriculum-sync-status');
        syncStatusElements.forEach(element => {
            if (element.dataset.curriculumId == data.curriculum_id) {
                this.updateCurriculumSyncStatusElement(element, data);
            }
        });
        
        // 統合管理画面の同期ステータス更新
        if (window.location.pathname.includes('/teacher/integrated_management')) {
            this.updateIntegratedManagementStatus(data);
        }
    }
    
    /**
     * カリキュラム同期ステータス要素の更新
     */
    updateCurriculumSyncStatusElement(element, data) {
        switch (data.type) {
            case 'sync_started':
                element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 同期中...';
                element.className = 'curriculum-sync-status syncing';
                break;
            case 'sync_completed':
                if (data.result?.success) {
                    element.innerHTML = '<i class="fas fa-check-circle"></i> 同期完了';
                    element.className = 'curriculum-sync-status success';
                } else {
                    element.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 同期エラー';
                    element.className = 'curriculum-sync-status error';
                }
                break;
            case 'sync_conflict':
                element.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 競合要解決';
                element.className = 'curriculum-sync-status warning';
                break;
        }
    }
    
    /**
     * 学習ポータルを更新
     */
    refreshLearningPortal() {
        // 学習ポータルの単元一覧を更新
        if (typeof refreshLearningUnits === 'function') {
            refreshLearningUnits();
        } else {
            // フォールバック: ページリロード
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
    }
    
    /**
     * HTMLエスケープ
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 再接続スケジュール
     */
    scheduleReconnect() {
        if (this.connectionRetries < this.maxRetries) {
            setTimeout(() => {
                this.connect();
            }, this.retryDelay);
        }
    }
    
    /**
     * 同期ステータスコールバック登録
     */
    onSyncStatus(type, callback) {
        this.syncStatusCallbacks.set(type, callback);
    }
    
    /**
     * 切断
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.isConnected = false;
            this.updateConnectionStatus('disconnected', '切断されました');
        }
    }
    
    /**
     * 接続状態確認
     */
    isSocketConnected() {
        return this.isConnected && this.socket && this.socket.connected;
    }
}

// グローバルインスタンス作成
let realtimeSync;

// DOMContentLoaded後に初期化
document.addEventListener('DOMContentLoaded', function() {
    // Socket.IOライブラリが読み込まれている場合のみ初期化
    if (typeof io !== 'undefined') {
        realtimeSync = new RealtimeSyncClient();
        
        // グローバル関数として公開
        window.realtimeSync = realtimeSync;
        
        console.log('Realtime sync client initialized');
    } else {
        console.warn('Socket.IO library not found. Realtime sync disabled.');
    }
});

// ページ遷移時のクリーンアップ
window.addEventListener('beforeunload', function() {
    if (realtimeSync) {
        realtimeSync.disconnect();
    }
});