"""
BaseBuilderコンテンツサービス

カリキュラム編集でBaseBuilderコンテンツを利用するための最小限のサービス
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BaseBuilderContentService:
    """BaseBuilderコンテンツ取得サービス"""
    
    @staticmethod
    def get_textsets_for_subject(subject_id: int) -> List[Dict[str, Any]]:
        """
        教科IDに基づいてTextSetを取得
        
        Args:
            subject_id: 教科ID
            
        Returns:
            TextSet情報のリスト
        """
        try:
            from basebuilder.models import TextSet, ProblemCategory
            
            textsets = (
                TextSet.query
                .join(ProblemCategory, TextSet.category_id == ProblemCategory.id)
                .filter(ProblemCategory.subject_id == subject_id)
                .order_by(TextSet.title)
                .all()
            )
            
            return [
                {
                    "id": ts.id,
                    "title": ts.title,
                    "description": ts.description,
                    "category_name": ts.category.name if ts.category else "",
                    "problems_count": len(ts.problems) if ts.problems else 0
                }
                for ts in textsets
            ]
            
        except ImportError:
            logger.warning("BaseBuilder models not available")
            return []
        except Exception as e:
            logger.error(f"Error getting textsets: {e}")
            return []
    
    @staticmethod
    def get_basic_items_for_subject(subject_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        教科IDに基づいてBasicKnowledgeItemを取得
        
        Args:
            subject_id: 教科ID
            limit: 取得上限
            
        Returns:
            BasicKnowledgeItem情報のリスト
        """
        try:
            from basebuilder.models import BasicKnowledgeItem, ProblemCategory
            
            items = (
                BasicKnowledgeItem.query
                .join(ProblemCategory, BasicKnowledgeItem.category_id == ProblemCategory.id)
                .filter(ProblemCategory.subject_id == subject_id)
                .filter(BasicKnowledgeItem.is_active == True)
                .order_by(BasicKnowledgeItem.title)
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "id": item.id,
                    "title": item.title,
                    "question": item.question,
                    "category_name": item.category.name if item.category else "",
                    "difficulty": item.difficulty
                }
                for item in items
            ]
            
        except ImportError:
            logger.warning("BaseBuilder models not available")
            return []
        except Exception as e:
            logger.error(f"Error getting basic items: {e}")
            return []