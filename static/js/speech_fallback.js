/**
 * 音声入力機能のフォールバック処理
 * 非対応ブラウザでの代替機能
 */

class SpeechFallback {
    constructor() {
        this.isSupported = this.checkBrowserSupport();
        this.init();
    }
    
    checkBrowserSupport() {
        // Web Speech API対応チェック
        const hasWebSpeech = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        
        // ブラウザー種別チェック
        const userAgent = navigator.userAgent.toLowerCase();
        const isChrome = /chrome/.test(userAgent) && !/edge/.test(userAgent);
        const isEdge = /edge/.test(userAgent) || /edg/.test(userAgent);
        const isSafari = /safari/.test(userAgent) && !/chrome/.test(userAgent);
        const isFirefox = /firefox/.test(userAgent);
        
        // セキュアコンテキストチェック
        const isSecure = location.protocol === 'https:' || location.hostname === 'localhost';
        
        console.log('Browser support check:', {
            hasWebSpeech,
            isChrome,
            isEdge,
            isSafari,
            isFirefox,
            isSecure
        });
        
        return hasWebSpeech && isSecure && (isChrome || isEdge || isSafari);
    }
    
    init() {
        if (!this.isSupported) {
            this.setupFallback();
        }
    }
    
    setupFallback() {
        document.body.classList.add('speech-not-supported');
        
        // 非対応の警告を表示（初回のみ）
        if (!sessionStorage.getItem('speech-warning-shown')) {
            this.showBrowserWarning();
            sessionStorage.setItem('speech-warning-shown', 'true');
        }
        
        // 音声入力ボタンを代替ボタンに置き換え
        this.replaceWithFallbackButtons();
    }
    
    showBrowserWarning() {
        const message = this.getBrowserSpecificMessage();
        
        // 簡易的な通知（実際のプロジェクトではtoastやモーダルを使用）
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            max-width: 400px;
            font-size: 0.9rem;
        `;
        notification.innerHTML = `
            <div style="display: flex; align-items: start; gap: 0.5rem;">
                <i class="fas fa-exclamation-triangle" style="color: #856404; margin-top: 0.1rem;"></i>
                <div>
                    <strong>音声入力について</strong><br>
                    ${message}
                </div>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="background: none; border: none; color: #856404; font-size: 1.2rem; cursor: pointer; margin-left: auto;">
                    ×
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // 10秒後に自動で非表示
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 10000);
    }
    
    getBrowserSpecificMessage() {
        const userAgent = navigator.userAgent.toLowerCase();
        
        if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
            return '音声入力機能は HTTPS 接続でのみご利用いただけます。';
        }
        
        if (/firefox/.test(userAgent)) {
            return 'Firefox では音声入力がサポートされていません。Chrome、Edge、Safari をお試しください。';
        }
        
        if (/safari/.test(userAgent) && !/chrome/.test(userAgent)) {
            return 'Safari では音声入力の機能が制限される場合があります。Chrome または Edge の使用をお勧めします。';
        }
        
        return 'お使いのブラウザでは音声入力がサポートされていません。Chrome、Edge、Safari の最新版をお試しください。';
    }
    
    replaceWithFallbackButtons() {
        const speechButtons = document.querySelectorAll('.speech-btn');
        
        speechButtons.forEach(button => {
            // 音声入力ボタンを代替機能ボタンに置き換え
            const fallbackButton = this.createFallbackButton(button);
            button.parentNode.replaceChild(fallbackButton, button);
        });
    }
    
    createFallbackButton(originalButton) {
        const fallbackButton = document.createElement('button');
        fallbackButton.type = 'button';
        fallbackButton.className = 'btn btn-outline-secondary speech-fallback-btn';
        fallbackButton.title = '音声入力（このブラウザでは利用できません）';
        fallbackButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
        fallbackButton.disabled = true;
        
        // 元のボタンのスタイルを一部継承
        const originalClasses = originalButton.className.split(' ');
        const sizeClasses = originalClasses.filter(cls => 
            cls.includes('chat-speech-btn') || 
            cls.includes('search-speech-btn') || 
            cls.includes('activity-speech-btn')
        );
        
        if (sizeClasses.length > 0) {
            fallbackButton.className += ' ' + sizeClasses.join(' ');
        }
        
        // クリック時の説明表示
        fallbackButton.addEventListener('click', () => {
            this.showDetailedHelp();
        });
        
        return fallbackButton;
    }
    
    showDetailedHelp() {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        
        modal.innerHTML = `
            <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 500px; margin: 1rem;">
                <h3 style="margin-top: 0; color: #495057;">
                    <i class="fas fa-microphone-slash text-muted"></i> 音声入力について
                </h3>
                <p>音声入力機能をご利用いただくには、以下の条件が必要です：</p>
                <ul style="text-align: left; margin: 1rem 0;">
                    <li><strong>対応ブラウザ：</strong> Chrome、Edge、Safari の最新版</li>
                    <li><strong>セキュア接続：</strong> HTTPS でのアクセス</li>
                    <li><strong>マイク許可：</strong> ブラウザでマイクアクセスを許可</li>
                </ul>
                <p><strong>推奨ブラウザ：</strong> Google Chrome または Microsoft Edge</p>
                <div style="margin-top: 1.5rem; text-align: center;">
                    <button onclick="this.closest('[style*=fixed]').remove()" 
                            style="background: #007bff; color: white; border: none; padding: 0.5rem 1.5rem; border-radius: 6px; cursor: pointer;">
                        閉じる
                    </button>
                </div>
            </div>
        `;
        
        // モーダル外クリックで閉じる
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        document.body.appendChild(modal);
    }
    
    // 代替入力方法の提案
    static suggestAlternatives(targetElement) {
        if (!targetElement) return;
        
        // キーボードショートカットの案内
        const tooltip = document.createElement('div');
        tooltip.style.cssText = `
            position: absolute;
            background: #343a40;
            color: white;
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            z-index: 1000;
            white-space: nowrap;
        `;
        tooltip.textContent = 'Ctrl+; でIME音声入力（Windowsの場合）';
        
        targetElement.parentNode.appendChild(tooltip);
        
        setTimeout(() => {
            tooltip.remove();
        }, 3000);
    }
}

// ページ読み込み時にフォールバック機能を初期化
document.addEventListener('DOMContentLoaded', function() {
    new SpeechFallback();
});

// 音声入力の代替手段を提案する関数
function showSpeechAlternatives() {
    const message = `
音声入力の代替手段：

1. スマートフォンの音声入力
   - iOS: キーボードのマイクボタン
   - Android: Gboardの音声入力

2. Windows音声認識
   - Windows + H キーで音声入力開始

3. スマートフォンでアクセス
   - Chrome または Safari で同じページを開く
    `;
    
    alert(message);
}

// エクスポート
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SpeechFallback;
}