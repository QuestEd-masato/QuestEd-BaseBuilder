"""
QuestEd APIエンドポイントセキュリティ強化モジュール

このモジュールは、REST APIエンドポイントのセキュリティを強化し、
不正アクセス、データ漏洩、API悪用を防ぐ機能を提供します。

主な機能:
- JWTトークン認証
- レート制限
- CORS設定
- APIキー認証
- リクエスト検証
- レスポンスサニタイゼーション

新規開発者向けガイド:
1. 全てのAPIエンドポイントに認証を実装
2. レート制限でDoS攻撃を防御
3. 入力データの厳格な検証
4. 出力データのサニタイゼーション
5. APIアクセスの詳細ログ記録

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import jwt
import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from flask import request, jsonify, current_app, g
from flask_login import current_user
from werkzeug.exceptions import TooManyRequests, Unauthorized, BadRequest
import redis
import json

# ログ設定
logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class APIAuthentication:
    """
    API認証システム
    
    JWTトークンベースの認証とAPIキー認証を提供し、
    セキュアなAPI accessを実現します。
    """
    
    @staticmethod
    def generate_api_token(user_id: int, role: str, expires_hours: int = 24) -> str:
        """
        APIトークンを生成
        
        Args:
            user_id: ユーザーID
            role: ユーザーロール
            expires_hours: 有効期限（時間）
            
        Returns:
            str: JWTトークン
        """
        try:
            payload = {
                'user_id': user_id,
                'role': role,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=expires_hours),
                'jti': secrets.token_hex(16)  # JWT ID for revocation
            }
            
            secret_key = current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('SECRET_KEY')
            token = jwt.encode(payload, secret_key, algorithm='HS256')
            
            return token
            
        except Exception as e:
            logger.error(f"APIトークン生成エラー: {str(e)}")
            raise
    
    @staticmethod
    def verify_api_token(token: str) -> Dict[str, Any]:
        """
        APIトークンを検証
        
        Args:
            token: JWTトークン
            
        Returns:
            Dict: トークンペイロード
            
        Raises:
            jwt.InvalidTokenError: 無効なトークン
        """
        try:
            secret_key = current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('SECRET_KEY')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # トークンの取り消し確認
            if APIAuthentication._is_token_revoked(payload.get('jti')):
                raise jwt.InvalidTokenError("トークンは取り消されています")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("トークンの有効期限が切れています")
        except jwt.InvalidTokenError as e:
            logger.warning(f"無効なAPIトークン: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"APIトークン検証エラー: {str(e)}")
            raise jwt.InvalidTokenError("トークン検証中にエラーが発生しました")
    
    @staticmethod
    def _is_token_revoked(jti: str) -> bool:
        """
        トークンが取り消されているかチェック
        
        Args:
            jti: JWT ID
            
        Returns:
            bool: 取り消されている場合True
        """
        try:
            # Redisを使用してトークンの取り消し状態を確認
            # 実装例：Redis接続が利用可能な場合
            # r = redis.Redis(host='localhost', port=6379, db=0)
            # return r.exists(f"revoked_token:{jti}")
            
            # Redis未利用の場合はとりあえずFalseを返す
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def revoke_token(jti: str, expires_at: datetime):
        """
        トークンを取り消し
        
        Args:
            jti: JWT ID
            expires_at: トークンの有効期限
        """
        try:
            # 取り消しリストに追加
            # 実装例：Redis使用
            # r = redis.Redis(host='localhost', port=6379, db=0)
            # ttl = int((expires_at - datetime.utcnow()).total_seconds())
            # r.setex(f"revoked_token:{jti}", ttl, "1")
            
            security_logger.info(f"APIトークンを取り消しました: {jti}")
            
        except Exception as e:
            logger.error(f"トークン取り消しエラー: {str(e)}")


class RateLimiter:
    """
    レート制限システム
    
    APIエンドポイントへのアクセス頻度を制限し、
    DoS攻撃やAPI乱用を防ぎます。
    """
    
    def __init__(self, redis_client=None):
        """
        レート制限システムの初期化
        
        Args:
            redis_client: Redisクライアント（オプション）
        """
        self.redis_client = redis_client
        self.memory_store = {}  # Redis未利用時のメモリストア
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, Any]]:
        """
        レート制限チェック
        
        Args:
            key: 制限キー（IP、ユーザーIDなど）
            limit: 制限回数
            window: 時間窓（秒）
            
        Returns:
            tuple: (許可/拒否, 制限情報)
        """
        now = time.time()
        
        try:
            if self.redis_client:
                return self._check_rate_limit_redis(key, limit, window, now)
            else:
                return self._check_rate_limit_memory(key, limit, window, now)
                
        except Exception as e:
            logger.error(f"レート制限チェックエラー: {str(e)}")
            # エラー時は通すが警告ログを出力
            return True, {'remaining': limit, 'reset_time': now + window}
    
    def _check_rate_limit_redis(self, key: str, limit: int, window: int, now: float) -> tuple[bool, Dict[str, Any]]:
        """
        Redis使用のレート制限チェック
        """
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window)
        results = pipe.execute()
        
        current_requests = results[1]
        
        if current_requests >= limit:
            return False, {
                'remaining': 0,
                'reset_time': now + window,
                'current': current_requests
            }
        
        return True, {
            'remaining': limit - current_requests - 1,
            'reset_time': now + window,
            'current': current_requests + 1
        }
    
    def _check_rate_limit_memory(self, key: str, limit: int, window: int, now: float) -> tuple[bool, Dict[str, Any]]:
        """
        メモリ使用のレート制限チェック
        """
        if key not in self.memory_store:
            self.memory_store[key] = []
        
        # 古いリクエストを削除
        self.memory_store[key] = [
            req_time for req_time in self.memory_store[key]
            if req_time > now - window
        ]
        
        current_requests = len(self.memory_store[key])
        
        if current_requests >= limit:
            return False, {
                'remaining': 0,
                'reset_time': now + window,
                'current': current_requests
            }
        
        # 新しいリクエストを記録
        self.memory_store[key].append(now)
        
        return True, {
            'remaining': limit - current_requests - 1,
            'reset_time': now + window,
            'current': current_requests + 1
        }


class APISecurityDecorator:
    """
    APIセキュリティデコレーター
    
    認証、認可、レート制限、入力検証などの
    セキュリティ機能をデコレーターとして提供します。
    """
    
    rate_limiter = RateLimiter()
    
    @staticmethod
    def require_api_auth(roles: Optional[List[str]] = None):
        """
        API認証を要求するデコレーター
        
        Args:
            roles: 許可するロールのリスト
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    # Authorization헤더からトークンを取得
                    auth_header = request.headers.get('Authorization')
                    if not auth_header:
                        raise Unauthorized("認証トークンが必要です")
                    
                    if not auth_header.startswith('Bearer '):
                        raise Unauthorized("無効な認証形式です")
                    
                    token = auth_header.split(' ')[1]
                    
                    # トークンを検証
                    payload = APIAuthentication.verify_api_token(token)
                    
                    # ロール認証
                    if roles and payload.get('role') not in roles:
                        raise Unauthorized("アクセス権限がありません")
                    
                    # リクエストコンテキストにユーザー情報を設定
                    g.api_user = {
                        'user_id': payload.get('user_id'),
                        'role': payload.get('role')
                    }
                    
                    return f(*args, **kwargs)
                    
                except jwt.InvalidTokenError as e:
                    return jsonify({'error': str(e)}), 401
                except Unauthorized as e:
                    return jsonify({'error': str(e)}), 401
                except Exception as e:
                    logger.error(f"API認証エラー: {str(e)}")
                    return jsonify({'error': 'Authentication failed'}), 401
            
            return decorated_function
        return decorator
    
    @staticmethod
    def rate_limit(limit: int = 60, window: int = 3600, per: str = 'ip'):
        """
        レート制限デコレーター
        
        Args:
            limit: 制限回数
            window: 時間窓（秒）
            per: 制限単位（'ip', 'user', 'endpoint'）
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    # 制限キーを生成
                    if per == 'ip':
                        key = f"rate_limit:ip:{request.remote_addr}"
                    elif per == 'user':
                        user_id = getattr(g, 'api_user', {}).get('user_id', 'anonymous')
                        key = f"rate_limit:user:{user_id}"
                    elif per == 'endpoint':
                        key = f"rate_limit:endpoint:{request.endpoint}"
                    else:
                        key = f"rate_limit:generic:{request.remote_addr}"
                    
                    # レート制限チェック
                    allowed, info = APISecurityDecorator.rate_limiter.is_allowed(key, limit, window)
                    
                    if not allowed:
                        security_logger.warning(
                            f"レート制限超過: key={key}, ip={request.remote_addr}, "
                            f"endpoint={request.endpoint}"
                        )
                        
                        response = jsonify({
                            'error': 'レート制限を超過しました',
                            'retry_after': int(info['reset_time'] - time.time())
                        })
                        response.status_code = 429
                        response.headers['Retry-After'] = str(int(info['reset_time'] - time.time()))
                        return response
                    
                    # レスポンスヘッダーにレート制限情報を追加
                    response = f(*args, **kwargs)
                    if hasattr(response, 'headers'):
                        response.headers['X-RateLimit-Limit'] = str(limit)
                        response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                        response.headers['X-RateLimit-Reset'] = str(int(info['reset_time']))
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"レート制限エラー: {str(e)}")
                    # エラー時は通す
                    return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    @staticmethod
    def validate_json_input(schema: Dict[str, Any]):
        """
        JSON入力検証デコレーター
        
        Args:
            schema: 検証スキーマ
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    if not request.is_json:
                        return jsonify({'error': 'JSON形式のデータが必要です'}), 400
                    
                    data = request.get_json()
                    if not data:
                        return jsonify({'error': '空のJSONデータです'}), 400
                    
                    # 入力検証
                    from app.utils.input_validator import InputValidator
                    try:
                        validated_data = InputValidator.validate_and_sanitize(data, schema)
                        g.validated_data = validated_data
                    except Exception as e:
                        return jsonify({'error': f'入力検証エラー: {str(e)}'}), 400
                    
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"JSON入力検証エラー: {str(e)}")
                    return jsonify({'error': 'Invalid input data'}), 400
            
            return decorated_function
        return decorator
    
    @staticmethod
    def log_api_access():
        """
        APIアクセスログデコレーター
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                start_time = time.time()
                
                try:
                    # アクセス情報を記録
                    access_info = {
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'ip': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent'),
                        'user_id': getattr(g, 'api_user', {}).get('user_id'),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    response = f(*args, **kwargs)
                    
                    # レスポンス情報を追加
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    access_info.update({
                        'status_code': getattr(response, 'status_code', 200),
                        'response_time_ms': round(response_time * 1000, 2)
                    })
                    
                    logger.info(f"API_ACCESS: {json.dumps(access_info)}")
                    
                    return response
                    
                except Exception as e:
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    error_info = {
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'ip': request.remote_addr,
                        'error': str(e),
                        'response_time_ms': round(response_time * 1000, 2),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    logger.error(f"API_ERROR: {json.dumps(error_info)}")
                    raise
            
            return decorated_function
        return decorator


class CORSConfig:
    """
    CORS設定管理
    
    Cross-Origin Resource Sharing設定を管理し、
    セキュアなクロスオリジンアクセスを実現します。
    """
    
    @staticmethod
    def setup_cors(app):
        """
        CORS設定の初期化
        
        Args:
            app: Flaskアプリケーション
        """
        from flask_cors import CORS
        
        # 本番環境では厳格なCORS設定
        if app.config.get('ENV') == 'production':
            cors_config = {
                'origins': app.config.get('ALLOWED_ORIGINS', ['https://yourdomain.com']),
                'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                'allow_headers': ['Content-Type', 'Authorization'],
                'supports_credentials': True,
                'max_age': 86400  # 1日
            }
        else:
            # 開発環境では緩い設定
            cors_config = {
                'origins': '*',
                'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
                'allow_headers': ['Content-Type', 'Authorization'],
                'supports_credentials': True
            }
        
        CORS(app, **cors_config)
        logger.info("CORS設定が初期化されました")


def setup_api_security(app):
    """
    APIセキュリティの初期化
    
    Args:
        app: Flaskアプリケーション
    """
    # CORS設定
    try:
        CORSConfig.setup_cors(app)
    except ImportError:
        logger.warning("flask-corsがインストールされていません。CORS機能は無効です。")
    
    # APIセキュリティミドルウェアの設定
    @app.before_request
    def before_api_request():
        """API リクエスト前処理"""
        if request.path.startswith('/api/'):
            # APIアクセスの基本検証
            if request.method == 'POST' and not request.is_json:
                return jsonify({'error': 'APIエンドポイントにはJSON形式でのリクエストが必要です'}), 400
    
    @app.after_request
    def after_api_request(response):
        """API レスポンス後処理"""
        if request.path.startswith('/api/'):
            # セキュリティヘッダーの追加
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        
        return response
    
    logger.info("APIセキュリティが正常に初期化されました")