-- MFA (Multi-Factor Authentication) テーブル作成スクリプト
-- QuestEd セキュリティ強化 Phase 1
-- 実行日: 2025-01-20

-- 1. Users テーブルにMFA関連カラムを追加
ALTER TABLE users 
ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE COMMENT 'MFA有効フラグ',
ADD COLUMN mfa_enforced BOOLEAN DEFAULT FALSE COMMENT 'MFA強制フラグ（管理者設定）',
ADD COLUMN last_mfa_verification TIMESTAMP NULL COMMENT '最終MFA認証日時',
ADD COLUMN mfa_setup_completed_at TIMESTAMP NULL COMMENT 'MFA設定完了日時';

-- 2. MFA秘密鍵管理テーブル
CREATE TABLE user_mfa_secrets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    secret_key_encrypted TEXT NOT NULL COMMENT '暗号化されたTOTP秘密鍵',
    backup_codes_encrypted TEXT NOT NULL COMMENT '暗号化されたバックアップコード（JSON）',
    is_enabled BOOLEAN DEFAULT FALSE NOT NULL COMMENT 'MFA有効フラグ',
    failed_attempts INT DEFAULT 0 COMMENT '認証失敗回数',
    locked_until TIMESTAMP NULL COMMENT 'ロック解除日時',
    last_used_at TIMESTAMP NULL COMMENT '最終使用日時',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_mfa (user_id),
    INDEX idx_user_mfa_user_id (user_id),
    INDEX idx_user_mfa_enabled (is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MFA秘密鍵管理';

-- 3. バックアップコード管理テーブル
CREATE TABLE mfa_backup_codes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    code_hash VARCHAR(255) NOT NULL COMMENT 'ハッシュ化されたバックアップコード',
    is_used BOOLEAN DEFAULT FALSE NOT NULL COMMENT '使用済みフラグ',
    used_at TIMESTAMP NULL COMMENT '使用日時',
    used_ip VARCHAR(45) NULL COMMENT '使用時IPアドレス',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_mfa_backup_user_id (user_id),
    INDEX idx_mfa_backup_used (is_used)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MFAバックアップコード管理';

-- 4. MFA認証試行ログテーブル
CREATE TABLE mfa_login_attempts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    attempt_type ENUM('TOTP', 'BACKUP_CODE') NOT NULL COMMENT '認証方法',
    success BOOLEAN NOT NULL COMMENT '認証成功フラグ',
    ip_address VARCHAR(45) NOT NULL COMMENT 'クライアントIPアドレス',
    user_agent TEXT NULL COMMENT 'ユーザーエージェント',
    failure_reason ENUM(
        'INVALID_CODE', 'EXPIRED_CODE', 'ACCOUNT_LOCKED', 
        'CODE_ALREADY_USED', 'RATE_LIMITED', 'SYSTEM_ERROR'
    ) NULL COMMENT '失敗理由',
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_mfa_attempts_user_time (user_id, attempted_at),
    INDEX idx_mfa_attempts_ip_time (ip_address, attempted_at),
    INDEX idx_mfa_attempts_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MFA認証試行ログ';

-- 5. 信頼済みデバイス管理テーブル
CREATE TABLE mfa_device_trust (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    device_fingerprint VARCHAR(255) NOT NULL COMMENT 'デバイスフィンガープリント',
    device_name VARCHAR(100) NULL COMMENT 'ユーザー指定デバイス名',
    is_trusted BOOLEAN DEFAULT TRUE NOT NULL COMMENT '信頼フラグ',
    trust_expires_at TIMESTAMP NOT NULL COMMENT '信頼有効期限',
    last_ip VARCHAR(45) NOT NULL COMMENT '最終使用IPアドレス',
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最終使用日時',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_device_trust_user_fingerprint (user_id, device_fingerprint),
    INDEX idx_device_trust_expires (trust_expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='信頼済みデバイス管理';

-- 6. 管理者アカウントのMFA強制設定
UPDATE users 
SET mfa_enforced = TRUE 
WHERE role = 'admin';

-- 7. インデックス最適化
-- 既存のusersテーブルにMFA関連インデックスを追加
ALTER TABLE users 
ADD INDEX idx_users_mfa_enabled (mfa_enabled),
ADD INDEX idx_users_mfa_enforced (mfa_enforced);

-- 8. セキュリティログ用のテーブル作成準備
-- （次のフェーズで使用）

-- 実行確認用のクエリ
-- SELECT 
--     'MFA Tables Created' as status,
--     COUNT(*) as admin_users_with_mfa_enforced
-- FROM users 
-- WHERE role = 'admin' AND mfa_enforced = TRUE;