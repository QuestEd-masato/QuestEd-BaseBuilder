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
            // 将来的にはAI推薦APIを呼び出す
            // 現在はモックデータを使用
            const mockRecommendations = [
                {
                    unit_id: 1,
                    title: "一次関数の基礎",
                    score: 0.92,
                    reason: "二次方程式の理解度が高く、次のステップとして最適です",
                    difficulty: 2,
                    estimated_minutes: 45
                },
                {
                    unit_id: 2,
                    title: "図形の性質",
                    score: 0.85,
                    reason: "空間認識能力を伸ばすのに適しています",
                    difficulty: 1,
                    estimated_minutes: 30
                },
                {
                    unit_id: 3,
                    title: "確率の基礎",
                    score: 0.78,
                    reason: "論理的思考力の向上につながります",
                    difficulty: 3,
                    estimated_minutes: 60
                }
            ];
            
            this.recommendations = mockRecommendations;
            this.renderRecommendations();
        } catch (error) {
            console.error('推薦取得エラー:', error);
            this.showRecommendationError();
        }
    }
    
    async loadUnits() {
        try {
            const response = await fetch('/api/units?include_progress=true');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.units = result.data.units;
                this.renderUnits();
            } else {
                throw new Error(result.message || 'データの取得に失敗しました');
            }
        } catch (error) {
            console.error('単元取得エラー:', error);
            this.showUnitsError();
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
        const progress = unit.progress || { status: 'not_started', percentage: 0 };
        const statusClass = progress.status === 'completed' ? 'completed' : 
                           progress.status === 'in_progress' ? 'in-progress' : '';
        
        const difficultyText = this.getDifficultyText(unit.difficulty);
        const difficultyClass = unit.difficulty === 1 ? 'easy' : 
                               unit.difficulty === 2 ? 'normal' : 'hard';
        
        const actionButton = this.getActionButton(progress.status, unit.id);
        
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
        
        return `
            <div class="progress-section">
                <div class="progress-bar">
                    <div class="progress-fill ${progress.status === 'completed' ? 'completed' : ''}" 
                         style="width: ${progress.percentage}%"></div>
                </div>
                <div class="progress-text">
                    <span>${progress.completed_items}/${progress.total_items} 問完了</span>
                    <span>${Math.round(progress.percentage)}%</span>
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
    
    getActionButton(status, unitId) {
        switch(status) {
            case 'not_started':
                return `<button class="btn-unit btn-start" onclick="event.stopPropagation(); learningPortal.startUnit(${unitId})">
                    <i class="fas fa-play"></i> 始める
                </button>`;
            case 'in_progress':
                return `<button class="btn-unit btn-continue" onclick="event.stopPropagation(); learningPortal.continueUnit(${unitId})">
                    <i class="fas fa-arrow-right"></i> 続きから
                </button>`;
            case 'completed':
                return `<button class="btn-unit btn-review" onclick="event.stopPropagation(); learningPortal.reviewUnit(${unitId})">
                    <i class="fas fa-redo"></i> 復習
                </button>`;
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
            if (this.filters.difficulty && unit.difficulty !== parseInt(this.filters.difficulty)) {
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
        const progress = unit.progress || { status: 'not_started', percentage: 0 };
        
        modalBody.innerHTML = `
            <h4>${unit.title}</h4>
            <p><strong>説明:</strong> ${unit.description || '説明がありません'}</p>
            <p><strong>難易度:</strong> ${this.getDifficultyText(unit.difficulty)}</p>
            <p><strong>推定学習時間:</strong> ${unit.estimated_minutes}分</p>
            
            ${progress.status !== 'not_started' ? `
                <h5>学習進捗</h5>
                <div class="progress mb-2">
                    <div class="progress-bar ${progress.status === 'completed' ? 'bg-success' : ''}" 
                         style="width: ${progress.percentage}%"></div>
                </div>
                <p>完了問題数: ${progress.completed_items}/${progress.total_items}</p>
                <p>学習時間: ${progress.study_time_minutes}分</p>
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
        
        try {
            const response = await fetch('/api/units/select', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    unit_id: this.selectedUnit.id,
                    selection_reason: 'self_selected'
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                // 成功時の処理
                this.showToast('success', result.message);
                
                // モーダルを閉じる
                const modal = bootstrap.Modal.getInstance(document.getElementById('unitModal'));
                modal.hide();
                
                // 単元一覧を再読み込み
                await this.loadUnits();
                
                // 実際の学習画面に遷移する場合は以下のコメントを外す
                // window.location.href = `/learning/unit/${this.selectedUnit.id}`;
                
            } else {
                this.showToast('error', result.message);
            }
        } catch (error) {
            console.error('単元選択エラー:', error);
            this.showToast('error', '単元の選択に失敗しました');
        }
    }
    
    selectRecommendation(unitId) {
        this.showUnitDetails(unitId);
    }
    
    async startUnit(unitId) {
        await this.selectUnitById(unitId);
    }
    
    async continueUnit(unitId) {
        // 実際の学習画面に遷移
        window.location.href = `/learning/unit/${unitId}`;
    }
    
    async reviewUnit(unitId) {
        // 復習モードで学習画面に遷移
        window.location.href = `/learning/unit/${unitId}?mode=review`;
    }
    
    async selectUnitById(unitId) {
        const unit = this.units.find(u => u.id === unitId);
        if (unit) {
            this.selectedUnit = unit;
            await this.selectUnit();
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
    
    showUnitsError() {
        const container = document.getElementById('units-grid');
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>単元の読み込みに失敗しました</h3>
                <p>ページを再読み込みしてお試しください</p>
            </div>
        `;
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

// インスタンス作成
let learningPortal;

// DOM読み込み完了時に初期化
document.addEventListener('DOMContentLoaded', function() {
    learningPortal = new LearningPortal();
});