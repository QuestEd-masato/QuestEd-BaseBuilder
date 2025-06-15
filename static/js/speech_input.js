/**
 * 音声入力管理クラス - 一時無効化中
 * Web Speech APIを使用した音声認識機能
 * QuestEd 新機能実装
 * 
 * 注意: この機能は現在無効化されています
 * 理由: ブラウザ互換性とプライバシー/セキュリティ懸念のため
 */

class SpeechInputManager {
    constructor(options = {}) {
        this.recognition = null;
        this.isRecording = false;
        this.isSupported = false;
        this.targetElement = null;
        this.onResultCallback = null;
        this.onErrorCallback = null;
        this.onStatusChangeCallback = null;
        
        // 設定オプション
        this.options = {
            language: options.language || 'ja-JP',
            continuous: options.continuous || false,
            interimResults: options.interimResults || true,
            maxAlternatives: options.maxAlternatives || 1,
            autoSave: options.autoSave !== false, // デフォルトでtrue
            context: options.context || 'chat'
        };
        
        this.startTime = null;
        this.finalTranscript = '';
        this.interimTranscript = '';
        
        this.init();
    }
    
    init() {
        // 一時的に音声機能を無効化
        console.warn('音声入力機能は一時的に無効化されています');
        this.isSupported = false;
        return;
        
        // Web Speech APIの可用性チェック（無効化中）
        /*
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            console.warn('Web Speech API is not supported in this browser');
            this.isSupported = false;
            return;
        }
        
        this.isSupported = true;
        this.setupRecognition();
        */
    }
    
    setupRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // 認識設定
        this.recognition.lang = this.options.language;
        this.recognition.continuous = this.options.continuous;
        this.recognition.interimResults = this.options.interimResults;
        this.recognition.maxAlternatives = this.options.maxAlternatives;
        
        // イベントハンドラの設定
        this.recognition.onstart = () => this.handleStart();
        this.recognition.onresult = (event) => this.handleResult(event);
        this.recognition.onerror = (event) => this.handleError(event);
        this.recognition.onend = () => this.handleEnd();
        this.recognition.onnomatch = () => this.handleNoMatch();
        this.recognition.onsoundstart = () => this.handleSoundStart();
        this.recognition.onsoundend = () => this.handleSoundEnd();
        this.recognition.onspeechstart = () => this.handleSpeechStart();
        this.recognition.onspeechend = () => this.handleSpeechEnd();
    }
    
    // 公開メソッド
    
    /**
     * 音声認識を開始
     * @param {HTMLElement} targetElement - 結果を挿入する要素
     * @param {Object} callbacks - コールバック関数
     */
    startRecognition(targetElement, callbacks = {}) {
        if (!this.isSupported) {
            this.showError('お使いのブラウザは音声入力に対応していません。Chrome、Edge、Safariをお試しください。');
            return false;
        }
        
        if (this.isRecording) {
            this.stopRecognition();
            return false;
        }
        
        this.targetElement = targetElement;
        this.onResultCallback = callbacks.onResult;
        this.onErrorCallback = callbacks.onError;
        this.onStatusChangeCallback = callbacks.onStatusChange;
        
        try {
            this.finalTranscript = '';
            this.interimTranscript = '';
            this.startTime = new Date();
            this.recognition.start();
            return true;
        } catch (error) {
            console.error('Recognition start error:', error);
            this.handleError({ error: 'not-allowed' });
            return false;
        }
    }
    
    /**
     * 音声認識を停止
     */
    stopRecognition() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
        }
    }
    
    /**
     * 対応ブラウザかチェック
     */
    checkSupport() {
        return this.isSupported;
    }
    
    // イベントハンドラ
    
    handleStart() {
        this.isRecording = true;
        console.log('Speech recognition started');
        this.updateStatus('recording', '録音中...');
    }
    
    handleResult(event) {
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        this.finalTranscript += finalTranscript;
        this.interimTranscript = interimTranscript;
        
        // 結果をターゲット要素に表示
        if (this.targetElement) {
            const displayText = this.finalTranscript + 
                (this.interimTranscript ? `<span class="interim">${this.interimTranscript}</span>` : '');
            
            if (this.targetElement.tagName === 'INPUT' || this.targetElement.tagName === 'TEXTAREA') {
                this.targetElement.value = this.finalTranscript + this.interimTranscript;
            } else {
                this.targetElement.innerHTML = displayText;
            }
        }
        
        // コールバック実行
        if (this.onResultCallback) {
            this.onResultCallback({
                final: this.finalTranscript,
                interim: this.interimTranscript,
                complete: this.finalTranscript + this.interimTranscript
            });
        }
        
        // 最終結果が得られた場合の処理
        if (finalTranscript) {
            console.log('Final transcript:', finalTranscript);
            
            // 自動保存が有効な場合
            if (this.options.autoSave && finalTranscript.trim()) {
                this.saveTranscription(finalTranscript.trim());
            }
        }
    }
    
    handleError(event) {
        this.isRecording = false;
        console.error('Speech recognition error:', event.error);
        
        let errorMessage = 'エラーが発生しました。';
        
        switch (event.error) {
            case 'no-speech':
                errorMessage = '音声が検出されませんでした。もう一度お試しください。';
                break;
            case 'audio-capture':
                errorMessage = 'マイクにアクセスできません。マイクの設定を確認してください。';
                break;
            case 'not-allowed':
                errorMessage = 'マイクへのアクセスが拒否されました。ブラウザの設定でマイクの使用を許可してください。';
                break;
            case 'network':
                errorMessage = 'ネットワークエラーが発生しました。';
                break;
            case 'language-not-supported':
                errorMessage = '選択された言語はサポートされていません。';
                break;
            case 'service-not-allowed':
                errorMessage = '音声認識サービスが無効になっています。';
                break;
        }
        
        this.updateStatus('error', errorMessage);
        
        if (this.onErrorCallback) {
            this.onErrorCallback(errorMessage);
        } else {
            this.showError(errorMessage);
        }
    }
    
    handleEnd() {
        this.isRecording = false;
        console.log('Speech recognition ended');
        this.updateStatus('stopped', '録音終了');
        
        // 最終的なテキストをターゲット要素に設定
        if (this.targetElement && this.finalTranscript) {
            if (this.targetElement.tagName === 'INPUT' || this.targetElement.tagName === 'TEXTAREA') {
                this.targetElement.value = this.finalTranscript;
                // Inputイベントを発火（他のJavaScriptが反応できるように）
                this.targetElement.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
    }
    
    handleNoMatch() {
        console.warn('No speech match found');
        this.updateStatus('no-match', '音声を認識できませんでした');
    }
    
    handleSoundStart() {
        console.log('Sound detected');
    }
    
    handleSoundEnd() {
        console.log('Sound ended');
    }
    
    handleSpeechStart() {
        console.log('Speech detected');
        this.updateStatus('detecting', '音声を検出中...');
    }
    
    handleSpeechEnd() {
        console.log('Speech ended');
        this.updateStatus('processing', '処理中...');
    }
    
    // ユーティリティメソッド
    
    updateStatus(status, message) {
        if (this.onStatusChangeCallback) {
            this.onStatusChangeCallback(status, message);
        }
    }
    
    showError(message) {
        // 簡易的なエラー表示（実際の実装ではtoastやモーダルを使用）
        console.error('Speech Input Error:', message);
        alert(message);
    }
    
    /**
     * 音声認識結果をサーバーに保存
     */
    async saveTranscription(transcription) {
        try {
            const duration = this.startTime ? (new Date() - this.startTime) / 1000 : 0;
            
            const response = await fetch('/api/speech/transcribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    transcription: transcription,
                    usage_context: this.options.context,
                    duration: duration
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                console.log('Transcription saved:', result.data);
            } else {
                console.error('Save transcription error:', result.message);
            }
        } catch (error) {
            console.error('Save transcription network error:', error);
        }
    }
}

/**
 * 音声入力ボタンコンポーネント
 */
class SpeechInputButton {
    constructor(buttonElement, targetElement, options = {}) {
        this.button = buttonElement;
        this.targetElement = targetElement;
        this.speechManager = new SpeechInputManager(options);
        this.isRecording = false;
        
        this.originalButtonHTML = this.button.innerHTML;
        this.recordingButtonHTML = '<i class="fas fa-stop text-danger"></i>';
        
        this.init();
    }
    
    init() {
        if (!this.speechManager.checkSupport()) {
            this.button.style.display = 'none';
            return;
        }
        
        this.button.addEventListener('click', () => this.toggleRecording());
        this.button.disabled = false;
        
        // ツールチップの更新
        this.button.setAttribute('title', 'クリックして音声入力を開始');
    }
    
    toggleRecording() {
        if (!this.isRecording) {
            this.startRecording();
        } else {
            this.stopRecording();
        }
    }
    
    startRecording() {
        const success = this.speechManager.startRecognition(this.targetElement, {
            onResult: (result) => this.handleResult(result),
            onError: (error) => this.handleError(error),
            onStatusChange: (status, message) => this.handleStatusChange(status, message)
        });
        
        if (success) {
            this.isRecording = true;
            this.updateButtonAppearance(true);
        }
    }
    
    stopRecording() {
        this.speechManager.stopRecognition();
        this.isRecording = false;
        this.updateButtonAppearance(false);
    }
    
    updateButtonAppearance(recording) {
        if (recording) {
            this.button.innerHTML = this.recordingButtonHTML;
            this.button.classList.add('recording');
            this.button.setAttribute('title', 'クリックして録音を停止');
        } else {
            this.button.innerHTML = this.originalButtonHTML;
            this.button.classList.remove('recording');
            this.button.setAttribute('title', 'クリックして音声入力を開始');
        }
    }
    
    handleResult(result) {
        // 結果は既にSpeechInputManagerで処理済み
        console.log('Speech result:', result);
    }
    
    handleError(error) {
        this.isRecording = false;
        this.updateButtonAppearance(false);
    }
    
    handleStatusChange(status, message) {
        // ステータスに応じてUIを更新
        switch (status) {
            case 'recording':
                this.button.classList.add('pulse');
                break;
            case 'stopped':
            case 'error':
                this.button.classList.remove('pulse');
                break;
        }
    }
}

// グローバル関数（既存コードとの互換性のため）
function initSpeechInput(buttonSelector, targetSelector, options = {}) {
    const button = document.querySelector(buttonSelector);
    const target = document.querySelector(targetSelector);
    
    if (button && target) {
        return new SpeechInputButton(button, target, options);
    }
    
    console.warn('Speech input elements not found:', { buttonSelector, targetSelector });
    return null;
}

// エクスポート（モジュール使用時）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SpeechInputManager, SpeechInputButton, initSpeechInput };
}