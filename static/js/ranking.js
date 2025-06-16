/**
 * QuestEd ランキング機能 JavaScript
 * 
 * ランキング表示、フィルタリング、リアルタイム更新などの
 * フロントエンド機能を提供します。
 * 
 * Author: QuestEd Development Team
 * Created: 2025-01-15
 * Version: 1.0.0
 */

class QuestEdRanking {
    constructor() {
        this.currentRankingType = 'total_points';
        this.currentScope = 'school';
        this.currentClassId = null;
        this.updateInterval = null;
        this.isLoading = false;
        
        this.init();
    }
    
    // XSS対策: HTMLエスケープ
    escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return unsafe;
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    init() {
        this.bindEvents();
        this.setupAutoRefresh();
        this.loadInitialRanking();
    }
    
    bindEvents() {
        // ランキング種類ボタンのイベント
        document.addEventListener('click', (e) => {
            if (e.target.matches('.ranking-type-btn')) {
                this.handleRankingTypeChange(e.target);
            }
        });
        
        // スコープ選択のイベント
        const scopeSelect = document.getElementById('scope-select');
        if (scopeSelect) {
            scopeSelect.addEventListener('change', (e) => {
                this.handleScopeChange(e.target.value);
            });
        }
        
        // クラス選択のイベント
        const classSelect = document.getElementById('class-select');
        if (classSelect) {
            classSelect.addEventListener('change', (e) => {
                this.currentClassId = e.target.value;
                this.refreshRanking();
            });
        }
        
        // 更新ボタンのイベント
        document.addEventListener('click', (e) => {
            if (e.target.matches('.refresh-btn') || e.target.closest('.refresh-btn')) {
                e.preventDefault();
                this.refreshRanking();
            }
        });
        
        // エクスポートボタンのイベント
        document.addEventListener('click', (e) => {
            if (e.target.matches('.export-btn') || e.target.closest('.export-btn')) {
                const action = e.target.dataset.action;
                if (action === 'export') {
                    this.exportRanking();
                }
            }
        });
    }
    
    handleRankingTypeChange(button) {
        // アクティブボタンの変更
        document.querySelectorAll('.ranking-type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');
        
        this.currentRankingType = button.dataset.type;
        this.refreshRanking();
    }
    
    handleScopeChange(value) {
        if (value.startsWith('class_')) {
            this.currentScope = 'class';
            this.currentClassId = value.split('_')[1];
        } else {
            this.currentScope = value;
            this.currentClassId = null;
        }
        
        this.refreshRanking();
    }
    
    async loadInitialRanking() {
        // 初期値の設定
        const rankingTypeButtons = document.querySelector('.ranking-type-buttons');
        if (rankingTypeButtons) {
            this.currentRankingType = rankingTypeButtons.dataset.current || 'total_points';
        }
        
        const scopeSelect = document.getElementById('scope-select');
        if (scopeSelect) {
            const selectedOption = scopeSelect.options[scopeSelect.selectedIndex];
            if (selectedOption.value.startsWith('class_')) {
                this.currentScope = 'class';
                this.currentClassId = selectedOption.value.split('_')[1];
            } else {
                this.currentScope = selectedOption.value;
            }
        }
        
        // 初期ランキングデータの読み込み
        await this.loadRankingData();
    }
    
    async refreshRanking() {
        if (this.isLoading) return;
        
        this.showLoading();
        await this.loadRankingData();
        this.hideLoading();
    }
    
    async loadRankingData() {
        try {
            this.isLoading = true;
            
            const params = new URLSearchParams({
                scope: this.currentScope,
                limit: 50
            });
            
            if (this.currentClassId) {
                params.append('scope_id', this.currentClassId);
            }
            
            const response = await fetch(`/api/ranking/${this.currentRankingType}?${params.toString()}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                this.updateRankingDisplay(data.data);
                this.updateMyRankDisplay(data.data.my_rank);
            } else {
                this.showError(data.message || 'データの取得に失敗しました');
            }
            
        } catch (error) {
            console.error('ランキングデータ取得エラー:', error);
            this.showError('通信エラーが発生しました');
        } finally {
            this.isLoading = false;
        }
    }
    
    updateRankingDisplay(rankingData) {
        const contentElement = document.getElementById('ranking-content');
        if (!contentElement) return;
        
        if (!rankingData.rankings || rankingData.rankings.length === 0) {
            contentElement.innerHTML = this.getNoDataHTML();
            return;
        }
        
        const tableHTML = this.generateRankingTableHTML(rankingData);
        contentElement.innerHTML = tableHTML;
    }
    
    updateMyRankDisplay(myRank) {
        const myRankCard = document.querySelector('.my-rank-card');
        if (!myRankCard || !myRank || !myRank.rank) return;
        
        const rankNumber = myRankCard.querySelector('.my-rank-number');
        const rankScore = myRankCard.querySelector('.my-rank-score');
        const participantsInfo = myRankCard.querySelector('p');
        
        if (rankNumber) {
            let medalEmoji = '';
            if (myRank.rank <= 3) {
                medalEmoji = myRank.rank === 1 ? '🥇' : myRank.rank === 2 ? '🥈' : '🥉';
            }
            rankNumber.textContent = `${medalEmoji}${myRank.rank}位`;
        }
        
        if (rankScore) {
            let unit = '';
            if (this.currentRankingType === 'accuracy_rate') unit = '%';
            else if (this.currentRankingType === 'study_time') unit = '分';
            
            rankScore.textContent = `スコア: ${myRank.score}${unit}`;
        }
        
        if (participantsInfo) {
            participantsInfo.textContent = `全${myRank.total_participants}人中 (上位${myRank.percentile}%)`;
        }
    }
    
    generateRankingTableHTML(rankingData) {
        const rankings = rankingData.rankings;
        const currentUserId = this.getCurrentUserId();
        
        let tableHTML = `
            <table class="ranking-table">
                <thead>
                    <tr>
                        <th style="width: 80px; text-align: center;">順位</th>
                        <th>学習者</th>
                        <th style="width: 150px; text-align: center;">${this.getRankingTypeLabel()}</th>
                        ${this.getExtraColumnHeaders()}
                        ${this.currentScope === 'school' ? '<th style="width: 150px;">クラス</th>' : ''}
                    </tr>
                </thead>
                <tbody>
        `;
        
        rankings.forEach(student => {
            const isCurrentUser = currentUserId && student.student_id === currentUserId;
            tableHTML += `
                <tr ${isCurrentUser ? 'style="background-color: #fef3c7; font-weight: bold;"' : ''}>
                    <td class="rank-number rank-${student.rank <= 3 ? student.rank : ''}">
                        ${this.getRankDisplayHTML(student.rank)}
                    </td>
                    <td>
                        <div class="student-info">
                            <div class="student-avatar">
                                ${student.student_name ? this.escapeHtml(student.student_name)[0].toUpperCase() : '?'}
                            </div>
                            <div>
                                <div style="font-weight: 600;">${this.escapeHtml(student.student_name || '不明')}</div>
                                ${student.school_name && this.currentScope !== 'class' ? 
                                    `<div style="font-size: 0.8rem; color: #6b7280;">${this.escapeHtml(student.school_name)}</div>` : ''
                                }
                            </div>
                        </div>
                    </td>
                    <td style="text-align: center;">
                        <div class="score-display">
                            ${this.formatScore(student.score)}
                        </div>
                    </td>
                    ${this.getExtraColumnData(student)}
                    ${this.currentScope === 'school' ? 
                        `<td style="font-size: 0.9rem; color: #6b7280;">${this.escapeHtml(student.class_name || '-')}</td>` : ''
                    }
                </tr>
            `;
        });
        
        tableHTML += `
                </tbody>
            </table>
            <div class="last-updated">
                最終更新: ${new Date(rankingData.last_updated).toLocaleString('ja-JP')}
                (参加者数: ${rankingData.total_participants}人)
            </div>
        `;
        
        return tableHTML;
    }
    
    getRankingTypeLabel() {
        const labels = {
            'total_points': '総合ポイント',
            'weekly_points': '週間ポイント',
            'monthly_points': '月間ポイント',
            'accuracy_rate': '正答率',
            'study_time': '学習時間',
            'consistency': '継続性'
        };
        return labels[this.currentRankingType] || 'スコア';
    }
    
    getExtraColumnHeaders() {
        if (this.currentRankingType === 'accuracy_rate') {
            return '<th style="width: 120px; text-align: center;">回答数</th>';
        } else if (this.currentRankingType === 'study_time') {
            return '<th style="width: 120px; text-align: center;">時間</th>';
        } else if (this.currentRankingType === 'consistency') {
            return '<th style="width: 120px; text-align: center;">継続率</th>';
        }
        return '';
    }
    
    getExtraColumnData(student) {
        if (this.currentRankingType === 'accuracy_rate') {
            return `<td style="text-align: center; color: #6b7280;">${student.total_answers || 0}問</td>`;
        } else if (this.currentRankingType === 'study_time') {
            return `<td style="text-align: center; color: #6b7280;">${(student.hours || 0).toFixed(1)}h</td>`;
        } else if (this.currentRankingType === 'consistency') {
            return `<td style="text-align: center; color: #6b7280;">${(student.consistency_rate || 0).toFixed(1)}%</td>`;
        }
        return '';
    }
    
    getRankDisplayHTML(rank) {
        if (rank === 1) return '<span class="medal">🥇</span>1';
        if (rank === 2) return '<span class="medal">🥈</span>2';
        if (rank === 3) return '<span class="medal">🥉</span>3';
        return rank.toString();
    }
    
    formatScore(score) {
        if (this.currentRankingType === 'accuracy_rate') {
            return `${parseFloat(score).toFixed(1)}%`;
        } else if (this.currentRankingType === 'study_time') {
            return `${parseInt(score)}分`;
        } else if (this.currentRankingType === 'consistency') {
            return `${score}日`;
        } else {
            return `${parseInt(score)}pt`;
        }
    }
    
    getCurrentUserId() {
        // グローバル変数または要素のdata属性から取得
        return window.currentUserId || 
               document.querySelector('[data-current-user-id]')?.dataset.currentUserId ||
               null;
    }
    
    showLoading() {
        const contentElement = document.getElementById('ranking-content');
        if (contentElement) {
            contentElement.innerHTML = `
                <div class="loading">
                    <i class="fas fa-spinner fa-spin fa-2x"></i>
                    <p>更新中...</p>
                </div>
            `;
        }
    }
    
    hideLoading() {
        // loadRankingDataで自動的に更新されるため、特別な処理は不要
    }
    
    showError(message) {
        const contentElement = document.getElementById('ranking-content');
        if (contentElement) {
            contentElement.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-exclamation-triangle fa-3x" style="color: #dc2626; margin-bottom: 1rem;"></i>
                    <p>${message}</p>
                    <button class="refresh-btn" onclick="rankingManager.refreshRanking()">
                        <i class="fas fa-sync-alt"></i> 再試行
                    </button>
                </div>
            `;
        }
    }
    
    getNoDataHTML() {
        return `
            <div class="no-data">
                <i class="fas fa-chart-line fa-3x" style="color: #d1d5db; margin-bottom: 1rem;"></i>
                <p>ランキングデータがありません</p>
            </div>
        `;
    }
    
    setupAutoRefresh() {
        // 5分ごとに自動更新
        this.updateInterval = setInterval(() => {
            if (!this.isLoading) {
                this.loadRankingData();
            }
        }, 300000);
    }
    
    stopAutoRefresh() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    async exportRanking() {
        try {
            const params = new URLSearchParams({
                type: this.currentRankingType,
                scope: this.currentScope,
                format: 'csv'
            });
            
            if (this.currentClassId) {
                params.append('class_id', this.currentClassId);
            }
            
            const response = await fetch(`/api/ranking/export?${params.toString()}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `ranking_${this.currentRankingType}_${Date.now()}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                throw new Error('エクスポートに失敗しました');
            }
        } catch (error) {
            console.error('エクスポートエラー:', error);
            alert('エクスポートに失敗しました');
        }
    }
    
    destroy() {
        this.stopAutoRefresh();
    }
}

// ランキングマネージャーのインスタンス化
let rankingManager = null;

// DOM読み込み完了時に初期化
document.addEventListener('DOMContentLoaded', function() {
    // ランキングページでのみ初期化
    if (document.querySelector('.ranking-container') || document.querySelector('.analysis-container')) {
        rankingManager = new QuestEdRanking();
    }
});

// ページ離脱時にリソースクリーンアップ
window.addEventListener('beforeunload', function() {
    if (rankingManager) {
        rankingManager.destroy();
    }
});

// グローバル関数（テンプレートから呼び出し用）
function refreshRanking() {
    if (rankingManager) {
        rankingManager.refreshRanking();
    }
}

function updateAnalysis() {
    // 教師ランキング分析ページ用
    if (typeof rankingManager !== 'undefined' && rankingManager) {
        const classSelect = document.getElementById('class-select');
        const rankingTypeSelect = document.getElementById('ranking-type-select');
        
        if (classSelect && rankingTypeSelect) {
            const params = new URLSearchParams({
                class_id: classSelect.value,
                type: rankingTypeSelect.value
            });
            
            window.location.href = `/teacher/ranking_analysis?${params.toString()}`;
        }
    }
}

function exportAnalysis() {
    // 教師用エクスポート機能
    if (rankingManager) {
        rankingManager.exportRanking();
    } else {
        alert('エクスポート機能は準備中です');
    }
}

function viewStudentDetail(studentId) {
    // 学生詳細ページへの遷移
    window.open(`/teacher/student_detail/${studentId}`, '_blank');
}