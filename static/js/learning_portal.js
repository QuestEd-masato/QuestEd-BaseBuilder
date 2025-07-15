/**
 * 自由進度学習ポータル JavaScript
 * QuestEd 新機能実装
 */

class LearningPortal {
    constructor() {
        this.units = [];
        this.recommendations = [];
        this.currentPage = 1;
        this.itemsPerPage = 12;
        this.filters = {
            search: '',
            difficulty: '',
            status: '',
            time: ''
        };
        this.selectedUnit = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadRecommendations();
        this.loadUnits();
    }
    
    bindEvents() {
        // フィルターイベント
        document.getElementById('search-input').addEventListener('input', 
            this.debounce((e) => this.updateFilter('search', e.target.value), 300));
        
        document.getElementById('difficulty-filter').addEventListener('change', 
            (e) => this.updateFilter('difficulty', e.target.value));
        
        document.getElementById('status-filter').addEventListener('change', 
            (e) => this.updateFilter('status', e.target.value));
        
        document.getElementById('time-filter').addEventListener('change', 
            (e) => this.updateFilter('time', e.target.value));
        
        // モーダルイベント
        document.getElementById('selectUnitBtn').addEventListener('click', 
            () => this.selectUnit());
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    async loadRecommendations() {
        try {
            // まずAIが利用可能かチェック
            const aiAvailable = await this.checkAIAvailability();
            
            if (!aiAvailable) {
                // AIが利用不可の場合は準備中メッセージを表示
                this.recommendations = [];
                this.renderRecommendations();
                return;
            }
            
            // AIが利用可能な場合は実際のAPI呼び出しを行う
            // 現在は実装されていないため、未完了レッスンを表示
            await this.loadIncompleteUnits();
            
        } catch (error) {
            console.error('推薦取得エラー:', error);
            this.showRecommendationError();
        }
    }
    
    async checkAIAvailability() {
        try {
            const response = await fetch('/api/ai/status', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.ai_available === true;
            }
            return false;
        } catch (error) {
            console.error('AI利用可能性チェックエラー:', error);
            return false;
        }
    }
    
    async loadIncompleteUnits() {
        try {
            // 未完了の単元を取得してレコメンデーションとして表示
            const response = await fetch('/api/units?status=incomplete&limit=3', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success' && data.data && data.data.units) {
                    // 未完了単元をレコメンデーション形式に変換
                    this.recommendations = data.data.units.map(unit => ({
                        unit_id: unit.id,
                        title: unit.title,
                        score: 0.8, // デフォルトスコア
                        reason: "まだ完了していない学習単元です",
                        difficulty: unit.difficulty_level || 2,
                        estimated_minutes: unit.estimated_minutes || 45
                    }));
                } else {
                    this.recommendations = [];
                }
            } else {
                this.recommendations = [];
            }
            
            this.renderRecommendations();
        } catch (error) {
            console.error('未完了レッスン取得エラー:', error);
            this.recommendations = [];
            this.renderRecommendations();
        }
    }
    
    async loadUnits() {
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                            document.querySelector('input[name="csrf_token"]')?.value || 
                            window.csrfToken || '';
            
            const response = await fetch('/api/units?include_progress=true', {
                method: 'GET',
                credentials: 'include',
                redirect: 'manual', // リダイレクトを手動で処理
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
            
            // レスポンスステータスチェック
            console.log('Response status:', response.status);
            console.log('Response URL:', response.url);
            console.log('Response redirected:', response.redirected);
            
            if (!response.ok) {
                console.error('Response not OK:', {
                    status: response.status,
                    statusText: response.statusText,
                    url: response.url,
                    redirected: response.redirected
                });
                
                // 302リダイレクトまたは認証エラー
                if (response.status === 302 || response.status === 401 || response.status === 403) {
                    this.showDebugInfo(`認証エラー (${response.status}): ${response.url}`);
                    throw new Error(`Authentication required (${response.status})`);
                } else if (response.status === 404) {
                    this.showDebugInfo(`エンドポイントが見つかりません (${response.status}): ${response.url}`);
                    throw new Error(`Endpoint not found (${response.status})`);
                } else {
                    this.showDebugInfo(`HTTPエラー (${response.status}): ${response.statusText}`);
                    throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
                }
            }
            
            const result = await response.json();
            console.log('Full API Response:', result);
            
            // データ検証強化
            console.log('API Response:', result);
            
            if (result && result.status === 'success' && result.data && Array.isArray(result.data.units)) {
                this.units = result.data.units;
                console.log('Units loaded:', this.units.length, 'units');
                
                if (this.units.length === 0) {
                    this.showEmptyUnits();
                } else {
                    this.renderUnits();
                }
            } else {
                console.error('Invalid data structure:', result);
                throw new Error(result.message || 'データの取得に失敗しました');
            }
        } catch (error) {
            console.error('単元取得エラー:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                response: error.response
            });
            
            // デバッグ情報を画面に表示
            this.showDebugInfo(`エラー: ${error.message}\nAPIエンドポイント: /api/units?include_progress=true`);
            
            // より詳細なエラーメッセージを表示
            if (error.message.includes('401') || error.message.includes('403')) {
                this.showAuthError();
            } else {
                this.showUnitsError();
            }
        }
    }
    
    renderRecommendations() {
        const container = document.getElementById('recommendations-grid');
        
        if (this.recommendations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-lightbulb"></i>
                    <h3>推薦を準備中です</h3>
                    <p>学習を進めると、AIがあなたに最適な単元を推薦します</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.recommendations.map(rec => `
            <div class="recommendation-card" onclick="learningPortal.selectRecommendation(${rec.unit_id})">
                <div class="difficulty-stars">
                    ${this.renderStars(rec.difficulty)}
                </div>
                <h4>${rec.title}</h4>
                <p class="text-sm mb-2">${rec.reason}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="badge bg-light text-dark">${rec.estimated_minutes}分</span>
                    <span class="text-sm">推薦度: ${Math.round(rec.score * 100)}%</span>
                </div>
            </div>
        `).join('');
    }
    
    renderUnits() {
        const container = document.getElementById('units-grid');
        const filteredUnits = this.filterUnits();
        
        if (filteredUnits.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h3>単元が見つかりません</h3>
                    <p>フィルター条件を変更してお試しください</p>
                </div>
            `;
            return;
        }
        
        // ページネーション計算
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pageUnits = filteredUnits.slice(startIndex, endIndex);
        
        container.innerHTML = pageUnits.map(unit => this.renderUnitCard(unit)).join('');
        this.renderPagination(filteredUnits.length);
    }
    
    renderUnitCard(unit) {
        const progress = unit.progress || { status: 'not_started', progress_percentage: 0 };
        const statusClass = progress.status === 'completed' ? 'completed' : 
                           progress.status === 'in_progress' ? 'in-progress' : '';
        
        const difficultyText = this.getDifficultyText(unit.difficulty_level);
        const difficultyClass = unit.difficulty_level === 1 ? 'easy' : 
                               unit.difficulty_level === 2 ? 'normal' : 'hard';
        
        const actionButton = this.getActionButton(progress.status, unit.id, unit);
        
        return `
            <div class="unit-card ${statusClass}" onclick="learningPortal.showUnitDetails(${unit.id})">
                <div class="unit-header">
                    <h3 class="unit-title">${unit.title}</h3>
                    <span class="unit-difficulty ${difficultyClass}">${difficultyText}</span>
                </div>
                
                <p class="unit-description">${unit.description || '説明がありません'}</p>
                
                <div class="unit-meta">
                    <span><i class="fas fa-clock"></i> ${unit.estimated_minutes}分</span>
                    <span><i class="fas fa-sort-numeric-up"></i> ${unit.order_index}</span>
                </div>
                
                ${this.renderProgressSection(progress)}
                
                <div class="unit-actions">
                    ${actionButton}
                </div>
            </div>
        `;
    }
    
    renderProgressSection(progress) {
        if (progress.status === 'not_started') {
            return '<div class="progress-section"><p class="text-muted">未開始</p></div>';
        }
        
        const percentage = progress.progress_percentage || 0;
        const completedItems = progress.completed_items || 0;
        const totalItems = progress.total_items || 0;
        
        return `
            <div class="progress-section">
                <div class="progress-bar">
                    <div class="progress-fill ${progress.status === 'completed' ? 'completed' : ''}" 
                         style="width: ${percentage}%"></div>
                </div>
                <div class="progress-text">
                    ${totalItems > 0 ? 
                        `<span>${completedItems}/${totalItems} 問完了</span>` : 
                        '<span>進捗記録中</span>'
                    }
                    <span>${Math.round(percentage)}%</span>
                </div>
            </div>
        `;
    }
    
    getDifficultyText(level) {
        switch(level) {
            case 1: return '基礎 ⭐';
            case 2: return '標準 ⭐⭐';
            case 3: return '応用 ⭐⭐⭐';
            default: return '不明';
        }
    }
    
    getActionButton(status, unitId, unit = null) {
        // 3状態レッスン管理システム: 未完了、却下（再申請）、完了
        const progress = unit?.progress;
        const approvalStatus = progress?.approval_status;
        const progressPercentage = progress?.progress_percentage || 0;
        
        // 完了状態（承認済み）
        if (approvalStatus === 'approved') {
            return `
                <div class="status-badge completed mb-2">
                    <i class="fas fa-check-circle"></i> 完了済み
                </div>
                <button class="btn-unit btn-review" onclick="event.stopPropagation(); learningPortal.reviewUnit(${unitId})" style="flex: 2;">
                    <i class="fas fa-redo"></i> 復習
                </button>
                <button class="btn-unit btn-outline-secondary" onclick="event.stopPropagation(); learningPortal.showCurriculum(${unitId})" style="flex: 1;">
                    <i class="fas fa-list-ul"></i> 内容
                </button>
            `;
        }
        
        // 却下（再申請）状態
        if (approvalStatus === 'rejected') {
            return `
                <div class="status-badge rejected mb-2">
                    <i class="fas fa-exclamation-triangle"></i> 再申請可能
                </div>
                ${progress?.rejection_reason ? `
                <div class="rejection-reason mb-2" style="font-size: 0.8rem; color: #dc3545; padding: 0.5rem; background: #f8d7da; border-radius: 4px;">
                    <strong>却下理由:</strong> ${progress.rejection_reason}
                </div>` : ''}
                <button class="btn-unit btn-warning" onclick="event.stopPropagation(); learningPortal.resubmitCompletion(${unitId})" style="flex: 2;">
                    <i class="fas fa-redo"></i> 再申請
                </button>
                <button class="btn-unit btn-outline-secondary" onclick="event.stopPropagation(); learningPortal.showCurriculum(${unitId})" style="flex: 1;">
                    <i class="fas fa-list-ul"></i> 内容
                </button>
            `;
        }
        
        // 承認待ち状態
        if (approvalStatus === 'pending') {
            return `
                <div class="status-badge pending mb-2">
                    <i class="fas fa-hourglass-half"></i> 承認待ち
                </div>
                <button class="btn-unit btn-review" onclick="event.stopPropagation(); learningPortal.reviewUnit(${unitId})" style="flex: 2;">
                    <i class="fas fa-eye"></i> 確認
                </button>
                <button class="btn-unit btn-outline-secondary" onclick="event.stopPropagation(); learningPortal.showCurriculum(${unitId})" style="flex: 1;">
                    <i class="fas fa-list-ul"></i> 内容
                </button>
            `;
        }
        
        // 未完了状態（従来のロジック）
        switch(status) {
            case 'not_started':
                return `
                    <button class="btn-unit btn-start" onclick="event.stopPropagation(); learningPortal.startUnit(${unitId})" style="flex: 2;">
                        <i class="fas fa-play"></i> 始める
                    </button>
                    <button class="btn-unit btn-outline-secondary" onclick="event.stopPropagation(); learningPortal.showCurriculum(${unitId})" style="flex: 1;">
                        <i class="fas fa-list-ul"></i> 内容
                    </button>
                    <button class="btn-unit btn-outline-danger" onclick="event.stopPropagation(); learningPortal.removeUnit(${unitId})" style="flex: 1;" title="この単元を削除">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            case 'in_progress':
                return `
                    <button class="btn-unit btn-continue" onclick="event.stopPropagation(); learningPortal.continueUnit(${unitId})" style="flex: 2;">
                        <i class="fas fa-arrow-right"></i> 続きから
                    </button>
                    <button class="btn-unit btn-outline-secondary" onclick="event.stopPropagation(); learningPortal.showCurriculum(${unitId})" style="flex: 1;">
                        <i class="fas fa-list-ul"></i> 内容
                    </button>
                    <button class="btn-unit btn-outline-danger" onclick="event.stopPropagation(); learningPortal.removeUnit(${unitId})" style="flex: 1;" title="この単元を削除（進捗が失われます）">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            case 'completed':
                // 完了申請可能な場合の表示
                if (progressPercentage >= 80) {
                    return `
                        <button class="btn-unit btn-success" onclick="event.stopPropagation(); learningPortal.requestCompletion(${unitId})" style="flex: 2;">
                            <i class="fas fa-check"></i> 完了申請
                        </button>
                        <button class="btn-unit btn-outline-secondary" onclick="event.stopPropagation(); learningPortal.showCurriculum(${unitId})" style="flex: 1;">
                            <i class="fas fa-list-ul"></i> 内容
                        </button>
                    `;
                } else {
                    return `
                        <button class="btn-unit btn-review" onclick="event.stopPropagation(); learningPortal.reviewUnit(${unitId})" style="flex: 2;">
                            <i class="fas fa-redo"></i> 復習
                        </button>
                        <button class="btn-unit btn-outline-secondary" onclick="event.stopPropagation(); learningPortal.showCurriculum(${unitId})" style="flex: 1;">
                            <i class="fas fa-list-ul"></i> 内容
                        </button>
                    `;
                }
            default:
                return `<button class="btn-unit btn-start" onclick="event.stopPropagation(); learningPortal.startUnit(${unitId})">
                    <i class="fas fa-play"></i> 始める
                </button>`;
        }
    }
    
    renderStars(level) {
        const maxStars = 3;
        let stars = '';
        for (let i = 1; i <= maxStars; i++) {
            stars += `<span class="star ${i <= level ? '' : 'empty'}">⭐</span>`;
        }
        return stars;
    }
    
    filterUnits() {
        return this.units.filter(unit => {
            // 検索フィルター
            if (this.filters.search && !unit.title.toLowerCase().includes(this.filters.search.toLowerCase())) {
                return false;
            }
            
            // 難易度フィルター
            if (this.filters.difficulty && unit.difficulty_level !== parseInt(this.filters.difficulty)) {
                return false;
            }
            
            // 進捗状況フィルター
            if (this.filters.status) {
                const progress = unit.progress || { status: 'not_started' };
                if (progress.status !== this.filters.status) {
                    return false;
                }
            }
            
            // 学習時間フィルター
            if (this.filters.time) {
                const minutes = unit.estimated_minutes;
                switch(this.filters.time) {
                    case 'short':
                        if (minutes > 30) return false;
                        break;
                    case 'medium':
                        if (minutes <= 30 || minutes > 60) return false;
                        break;
                    case 'long':
                        if (minutes <= 60) return false;
                        break;
                }
            }
            
            return true;
        });
    }
    
    updateFilter(filterType, value) {
        this.filters[filterType] = value;
        this.currentPage = 1; // ページをリセット
        this.renderUnits();
    }
    
    renderPagination(totalItems) {
        const totalPages = Math.ceil(totalItems / this.itemsPerPage);
        const container = document.getElementById('pagination');
        
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let pagination = '';
        
        // 前へボタン
        if (this.currentPage > 1) {
            pagination += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="learningPortal.goToPage(${this.currentPage - 1})">前へ</a>
                </li>
            `;
        }
        
        // ページ番号
        for (let i = 1; i <= totalPages; i++) {
            if (i === this.currentPage) {
                pagination += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else if (i === 1 || i === totalPages || Math.abs(i - this.currentPage) <= 2) {
                pagination += `
                    <li class="page-item">
                        <a class="page-link" href="#" onclick="learningPortal.goToPage(${i})">${i}</a>
                    </li>
                `;
            } else if (Math.abs(i - this.currentPage) === 3) {
                pagination += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }
        
        // 次へボタン
        if (this.currentPage < totalPages) {
            pagination += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="learningPortal.goToPage(${this.currentPage + 1})">次へ</a>
                </li>
            `;
        }
        
        container.innerHTML = pagination;
    }
    
    goToPage(page) {
        this.currentPage = page;
        this.renderUnits();
        
        // ページトップにスクロール
        document.querySelector('.units-section').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }
    
    showUnitDetails(unitId) {
        const unit = this.units.find(u => u.id === unitId);
        if (!unit) return;
        
        this.selectedUnit = unit;
        
        const modalBody = document.getElementById('unitModalBody');
        const progress = unit.progress || { status: 'not_started', progress_percentage: 0 };
        
        modalBody.innerHTML = `
            <h4>${unit.title}</h4>
            <p><strong>説明:</strong> ${unit.description || '説明がありません'}</p>
            <p><strong>難易度:</strong> ${this.getDifficultyText(unit.difficulty_level)}</p>
            <p><strong>推定学習時間:</strong> ${unit.estimated_minutes}分</p>
            
            ${progress.status !== 'not_started' ? `
                <h5>学習進捗</h5>
                <div class="progress mb-2">
                    <div class="progress-bar ${progress.status === 'completed' ? 'bg-success' : ''}" 
                         style="width: ${progress.progress_percentage || 0}%"></div>
                </div>
                ${progress.completed_items && progress.total_items ? 
                    `<p>完了問題数: ${progress.completed_items}/${progress.total_items}</p>` : ''
                }
                ${progress.study_time_minutes ? 
                    `<p>学習時間: ${progress.study_time_minutes}分</p>` : ''
                }
            ` : ''}
            
            ${unit.prerequisites && unit.prerequisites.length > 0 ? `
                <h5>前提知識</h5>
                <p>この単元を学習する前に、以下の単元を完了することをお勧めします。</p>
                <ul>
                    ${unit.prerequisites.map(prereq => `<li>単元ID: ${prereq}</li>`).join('')}
                </ul>
            ` : ''}
        `;
        
        // モーダルボタンのテキストを更新
        const selectBtn = document.getElementById('selectUnitBtn');
        if (progress.status === 'completed') {
            selectBtn.textContent = 'この単元を復習';
            selectBtn.className = 'btn btn-warning';
        } else if (progress.status === 'in_progress') {
            selectBtn.textContent = '学習を続ける';
            selectBtn.className = 'btn btn-success';
        } else {
            selectBtn.textContent = 'この単元を始める';
            selectBtn.className = 'btn btn-primary';
        }
        
        // モーダル表示
        const modal = new bootstrap.Modal(document.getElementById('unitModal'));
        modal.show();
    }
    
    async selectUnit() {
        if (!this.selectedUnit) return;
        
        console.log('CSRF Token available:', window.csrfToken ? 'Yes' : 'No');
        
        try {
            const response = await fetch('/api/units/select', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken || ''
                },
                body: JSON.stringify({
                    unit_id: this.selectedUnit.id,
                    selection_reason: 'self_selected'
                })
            });
            
            console.log('Unit select response:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('HTTP Error Response:', {
                    status: response.status,
                    statusText: response.statusText,
                    responseText: errorText
                });
                
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
            }
            
            const result = await response.json();
            console.log('Unit select result:', result);
            
            if (result.status === 'success') {
                // 成功時の処理
                this.showToast('success', result.message || '単元を選択しました');
                
                // モーダルを閉じる
                const modal = bootstrap.Modal.getInstance(document.getElementById('unitModal'));
                if (modal) modal.hide();
                
                // 単元一覧を再読み込み
                await this.loadUnits();
                
                // 実際の学習画面に遷移する場合は以下のコメントを外す
                // window.location.href = `/learning/unit/${this.selectedUnit.id}`;
                
            } else {
                this.showToast('error', result.message || 'エラーが発生しました');
            }
        } catch (error) {
            console.error('単元選択エラー:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                response: error.response
            });
            this.showToast('error', `単元の選択に失敗しました: ${error.message}`);
        }
    }
    
    selectRecommendation(unitId) {
        this.showUnitDetails(unitId);
    }
    
    async startUnit(unitId) {
        // ダッシュボードと同じ動作：直接学習画面に遷移
        const curriculum = this.units.find(u => u.id === unitId);
        if (curriculum && curriculum.system_type === 'lessons') {
            // レッスンシステムのカリキュラムの場合
            window.location.href = `/student/curriculum/${unitId}/lessons`;
        } else {
            // 従来のタスクシステムの場合または単元学習
            window.location.href = `/student/learning/unit/${unitId}`;
        }
    }
    
    async continueUnit(unitId) {
        // カリキュラムIDとして扱い、システムタイプに応じて適切なURLに遷移
        const curriculum = this.units.find(u => u.id === unitId);
        if (curriculum && curriculum.system_type === 'lessons') {
            // レッスンシステムのカリキュラムの場合
            window.location.href = `/student/curriculum/${unitId}/lessons`;
        } else {
            // 従来のタスクシステムの場合
            window.location.href = `/student/curriculum/${unitId}/tasks`;
        }
    }
    
    async reviewUnit(unitId) {
        // 復習モードで学習画面に遷移
        window.location.href = `/learning/unit/${unitId}?mode=review`;
    }
    
    async showCurriculum(unitId) {
        // 単元のカリキュラム詳細を表示
        const unit = this.units.find(u => u.id === unitId);
        if (!unit) {
            this.showToast('error', '単元が見つかりませんでした');
            return;
        }
        
        try {
            // 単元詳細情報を取得
            const response = await fetch(`/api/units/${unitId}/curriculum`, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-CSRFToken': window.csrfToken || ''
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const curriculumData = await response.json();
            
            // カリキュラム詳細モーダルを表示
            this.displayCurriculumModal(unit, curriculumData);
            
        } catch (error) {
            console.error('カリキュラム取得エラー:', error);
            // エラー時は基本情報のみでモーダルを表示
            this.displayCurriculumModal(unit, { problems: [] });
        }
    }
    
    displayCurriculumModal(unit, curriculumData) {
        const modalHtml = `
            <div class="modal fade" id="curriculumDetailModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-list-ul"></i> ${unit.title} - カリキュラム詳細
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="curriculum-overview mb-4">
                                <h6 class="text-primary">${unit.title}</h6>
                                <p class="text-muted">${unit.description || '単元の詳細学習内容をご確認ください'}</p>
                                <div class="row">
                                    <div class="col-md-4">
                                        <small class="text-muted">難易度:</small><br>
                                        <span class="badge bg-primary">${this.getDifficultyText(unit.difficulty_level)}</span>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">推定時間:</small><br>
                                        <span><i class="fas fa-clock"></i> ${unit.estimated_minutes}分</span>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">問題数:</small><br>
                                        <span><i class="fas fa-tasks"></i> ${curriculumData.problems ? curriculumData.problems.length : 0}問</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="curriculum-structure">
                                <h6><i class="fas fa-tasks"></i> 学習内容構成</h6>
                                
                                <div class="learning-items">
                                    <h7 class="text-secondary">📚 学習問題一覧</h7>
                                    <div class="problems-list mt-2">
                                        ${this.renderProblemsList(curriculumData.problems || [])}
                                    </div>
                                </div>
                                
                                <div class="learning-objectives mt-4">
                                    <h7 class="text-secondary">🎯 学習目標と評価基準</h7>
                                    <div class="mt-2">
                                        <div class="alert alert-light">
                                            <ul class="mb-0">
                                                <li><strong>完了基準:</strong> 80%以上の問題を完了すること</li>
                                                <li><strong>理解度目標:</strong> 各問題で3段階以上の自己評価</li>
                                                <li><strong>学習時間目安:</strong> ${unit.estimated_minutes}分程度</li>
                                                <li><strong>申請手順:</strong> 問題完了 → 進捗確認 → 教師承認申請</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
                            <button type="button" class="btn btn-primary" onclick="learningPortal.startUnitFromCurriculum(${unit.id})" data-bs-dismiss="modal">
                                <i class="fas fa-play"></i> 学習を始める
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 既存のモーダルがあれば削除
        const existingModal = document.getElementById('curriculumDetailModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 新しいモーダルを追加
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // モーダルを表示
        const modal = new bootstrap.Modal(document.getElementById('curriculumDetailModal'));
        modal.show();
    }
    
    renderProblemsList(problems) {
        if (!problems || problems.length === 0) {
            return `
                <div class="text-center py-3">
                    <i class="fas fa-exclamation-triangle text-warning"></i>
                    <p class="text-muted">学習問題が登録されていません</p>
                </div>
            `;
        }
        
        return `
            <div class="list-group">
                ${problems.map((problem, index) => `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div class="problem-info">
                            <h8 class="mb-1">${index + 1}. ${problem.title || 'タイトルなし'}</h8>
                            <p class="mb-1 text-muted small">${problem.question ? (problem.question.length > 80 ? problem.question.substring(0, 80) + '...' : problem.question) : '内容なし'}</p>
                        </div>
                        <div class="status-badge">
                            ${problem.status ? 
                                (problem.status === 'completed' ? '<span class="badge bg-success">完了</span>' :
                                 problem.status === 'in_progress' ? '<span class="badge bg-primary">学習中</span>' :
                                 '<span class="badge bg-secondary">未開始</span>') :
                                '<span class="badge bg-secondary">未開始</span>'
                            }
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    async startUnitFromCurriculum(unitId) {
        // カリキュラム確認後に学習を開始
        await this.startUnit(unitId);
    }
    
    async selectUnitById(unitId) {
        console.log('Looking for unit ID:', unitId, 'in units:', this.units);
        const unit = this.units.find(u => u.id === unitId);
        if (unit) {
            console.log('Found unit:', unit);
            this.selectedUnit = unit;
            await this.selectUnit();
        } else {
            console.error('Unit not found with ID:', unitId);
            this.showToast('error', '単元が見つかりませんでした');
        }
    }
    
    showRecommendationError() {
        const container = document.getElementById('recommendations-grid');
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>推薦の取得に失敗しました</h3>
                <p>しばらく時間をおいてから再度お試しください</p>
            </div>
        `;
    }
    
    showEmptyUnits() {
        const container = document.getElementById('units-grid');
        if (!container) {
            console.warn('units-grid container not found');
            return;
        }
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-book fa-3x mb-3"></i>
                <h3>学習単元がまだありません</h3>
                <p>先生が単元を登録するまでお待ちください。</p>
            </div>
        `;
    }
    
    showUnitsError() {
        const container = document.getElementById('units-grid');
        if (!container) {
            console.warn('units-grid container not found');
            return;
        }
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>単元の読み込みに失敗しました</h3>
                <p>ページを再読み込みしてお試しください</p>
                <button class="btn btn-outline-primary btn-sm mt-2" onclick="location.reload()">
                    <i class="fas fa-redo"></i> 再読み込み
                </button>
            </div>
        `;
    }
    
    showAuthError() {
        const container = document.getElementById('units-grid');
        if (!container) {
            console.warn('units-grid container not found');
            return;
        }
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-lock"></i>
                <h3>認証エラー</h3>
                <p>ログインが必要です。再度ログインしてください。</p>
                <button class="btn btn-primary btn-sm mt-2" onclick="window.location.href='/login'">
                    <i class="fas fa-sign-in-alt"></i> ログインページへ
                </button>
            </div>
        `;
    }
    
    showDebugInfo(message) {
        const debugInfo = document.getElementById('debug-info');
        const debugText = document.getElementById('debug-text');
        
        if (debugInfo && debugText) {
            debugText.textContent = message;
            debugInfo.style.display = 'block';
        }
    }
    
    showToast(type, message) {
        // Bootstrap Toast を使用してメッセージ表示
        // 実装は既存のtoast機能に合わせる
        console.log(`${type}: ${message}`);
        
        // 簡易的なアラート表示（実際の実装時はtoastに置き換える）
        if (type === 'success') {
            alert(`✅ ${message}`);
        } else {
            alert(`❌ ${message}`);
        }
    }
}

// フィルタークリア関数
function clearFilters() {
    document.getElementById('search-input').value = '';
    document.getElementById('difficulty-filter').value = '';
    document.getElementById('status-filter').value = '';
    document.getElementById('time-filter').value = '';
    
    learningPortal.filters = {
        search: '',
        difficulty: '',
        status: '',
        time: ''
    };
    learningPortal.currentPage = 1;
    learningPortal.renderUnits();
}

// 単元削除機能拡張
LearningPortal.prototype.removeUnit = async function(unitId) {
    // 削除対象の単元情報を取得
    const unit = this.units.find(u => u.id === unitId);
    if (!unit) {
        this.showToast('error', '単元が見つかりませんでした');
        return;
    }

    // 進捗状況に基づく確認メッセージ
    let confirmMessage = `「${unit.title}」を削除しますか？`;
    let progressWarning = '';
    
    if (unit.progress && unit.progress.status === 'in_progress' && unit.progress.progress_percentage > 0) {
        progressWarning = `\n\n⚠️ 警告: この単元は学習中です（進捗${unit.progress.progress_percentage}%）。削除すると進捗が失われます。`;
        confirmMessage += progressWarning;
    } else if (unit.progress && unit.progress.status === 'completed') {
        this.showToast('error', '完了済みの単元は削除できません');
        return;
    }

    // 確認ダイアログ
    if (!confirm(confirmMessage)) {
        return;
    }

    try {
        // APIで削除実行
        const response = await fetch(`/api/units/${unitId}/remove`, {
            method: 'DELETE',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.csrfToken || '',
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            this.showToast('success', result.message || '単元を削除しました');
            
            // ローカルデータから削除
            this.units = this.units.filter(u => u.id !== unitId);
            
            // UIを再描画
            this.renderUnits();
            
        } else if (result.status === 'warning') {
            // 警告の場合は再確認
            const confirmAgain = confirm(`${result.message}\n\n本当に削除しますか？`);
            if (confirmAgain) {
                // 強制削除フラグを付けて再実行
                await this.forceRemoveUnit(unitId);
            }
        } else {
            this.showToast('error', result.message || '削除に失敗しました');
        }

    } catch (error) {
        console.error('Unit removal error:', error);
        this.showToast('error', '削除中にエラーが発生しました');
    }
};

LearningPortal.prototype.forceRemoveUnit = async function(unitId) {
    try {
        const response = await fetch(`/api/units/${unitId}/remove?force=true`, {
            method: 'DELETE',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.csrfToken || '',
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            this.showToast('success', result.message || '単元を削除しました');
            
            // ローカルデータから削除
            this.units = this.units.filter(u => u.id !== unitId);
            
            // UIを再描画
            this.renderUnits();
        } else {
            this.showToast('error', result.message || '削除に失敗しました');
        }

    } catch (error) {
        console.error('Force unit removal error:', error);
        this.showToast('error', '削除中にエラーが発生しました');
    }
};

// 完了申請機能
LearningPortal.prototype.requestCompletion = async function(unitId) {
    if (!confirm('この単元の完了申請を行いますか？\n条件を満たしていることを確認してください。')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/units/${unitId}/request-completion`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.csrfToken || '',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                completion_comment: '完了申請',
                check_basebuilder: true
            })
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            this.showToast('success', result.message || '完了申請を送信しました');
            
            // データを再読み込み
            await this.loadUnits();
        } else {
            this.showToast('error', result.message || '完了申請に失敗しました');
        }

    } catch (error) {
        console.error('Completion request error:', error);
        this.showToast('error', '完了申請中にエラーが発生しました');
    }
};

// 再申請機能
LearningPortal.prototype.resubmitCompletion = async function(unitId) {
    if (!confirm('この単元を再申請しますか？\n前回の却下理由を確認して改善してから申請してください。')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/unit/${unitId}/resubmit-completion`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.csrfToken || '',
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            this.showToast('success', result.message || '再申請を送信しました');
            
            // データを再読み込み
            await this.loadUnits();
        } else {
            this.showToast('error', result.message || '再申請に失敗しました');
        }

    } catch (error) {
        console.error('Resubmit completion error:', error);
        this.showToast('error', '再申請中にエラーが発生しました');
    }
};

// インスタンス作成
let learningPortal;

// DOM読み込み完了時に初期化
document.addEventListener('DOMContentLoaded', function() {
    learningPortal = new LearningPortal();
});