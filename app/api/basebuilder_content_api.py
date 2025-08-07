"""
BaseBuilderコンテンツAPI

カリキュラム編集で使用するBaseBuilderコンテンツ取得API
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import logging

logger = logging.getLogger(__name__)

basebuilder_content_api_bp = Blueprint('basebuilder_content_api', __name__, url_prefix='/api/basebuilder')

@basebuilder_content_api_bp.route('/content')
@login_required
def get_basebuilder_content():
    """
    教科IDに基づいてBaseBuilderコンテンツを取得
    
    Query Parameters:
        subject_id: 教科ID
        
    Returns:
        JSON: TextSetとBasicKnowledgeItemのリスト
    """
    try:
        # 教師のみアクセス可能
        if current_user.role != 'teacher':
            return jsonify({"error": "Unauthorized"}), 403
            
        subject_id = request.args.get('subject_id', type=int)
        if not subject_id:
            return jsonify({"error": "subject_id is required"}), 400
            
        # サービスを使用してデータ取得
        from app.services.curriculum.basebuilder_content_service import BaseBuilderContentService
        
        textsets = BaseBuilderContentService.get_textsets_for_subject(subject_id)
        items = BaseBuilderContentService.get_basic_items_for_subject(subject_id, limit=50)
        
        return jsonify({
            "textsets": textsets,
            "items": items,
            "count": {
                "textsets": len(textsets),
                "items": len(items)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_basebuilder_content: {e}")
        return jsonify({"error": "Internal server error"}), 500