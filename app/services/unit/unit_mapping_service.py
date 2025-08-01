# -*- coding: utf-8 -*-
"""
UnitMappingService

単元-アイテムマッピング専門サービス
ProgressManagerの重複メソッドcreate_unit_mappings_data を統合・修正
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import (
    CurriculumUnit, UnitItemMapping, db
)

logger = logging.getLogger(__name__)


class UnitMappingService:
    """単元マッピング専門サービス"""

    def create_unit_mappings(self, mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        単元-アイテムマッピングを作成
        
        Args:
            mapping_data: マッピングデータ
            
        Returns:
            Dict: 作成結果
        """
        try:
            logger.info(f"Creating unit mappings by user {current_user.id}")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "マッピング作成権限がありません"
                }

            # 入力データの検証
            validation_result = self._validate_mapping_data(mapping_data)
            if not validation_result['valid']:
                return {
                    "success": False,
                    "message": validation_result['message']
                }

            # マッピングの作成
            created_mappings = self._create_mappings(mapping_data)
            
            db.session.commit()
            
            return {
                "success": True,
                "message": "マッピングが正常に作成されました",
                "mappings": created_mappings,
                "total_created": len(created_mappings)
            }

        except Exception as e:
            logger.error(f"Error creating unit mappings: {str(e)}")
            db.session.rollback()
            return {
                "success": False,
                "message": f"マッピング作成中にエラーが発生しました: {str(e)}"
            }

    def get_unit_mappings(self, unit_id: Optional[int] = None) -> Dict[str, Any]:
        """
        単元マッピング一覧を取得
        
        Args:
            unit_id: 単元ID（指定時は該当単元のマッピングのみ）
            
        Returns:
            Dict: マッピング一覧
        """
        try:
            logger.info(f"Getting unit mappings for unit {unit_id}")
            
            query = UnitItemMapping.query
            
            if unit_id:
                # 単元の存在確認
                unit = CurriculumUnit.query.get(unit_id)
                if not unit:
                    return {
                        "success": False,
                        "message": "指定された単元が見つかりません"
                    }
                
                query = query.filter_by(unit_id=unit_id)
            
            mappings = query.order_by(UnitItemMapping.created_at.desc()).all()
            
            mappings_data = []
            for mapping in mappings:
                mapping_item = {
                    "id": mapping.id,
                    "unit_id": mapping.unit_id,
                    "item_id": mapping.item_id,
                    "item_type": mapping.item_type,
                    "order_index": mapping.order_index,
                    "is_required": mapping.is_required,
                    "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
                    "created_by": mapping.created_by
                }
                
                # 単元情報の追加
                unit = CurriculumUnit.query.get(mapping.unit_id)
                if unit:
                    mapping_item["unit_title"] = unit.title
                
                mappings_data.append(mapping_item)
            
            return {
                "success": True,
                "mappings": mappings_data,
                "total_count": len(mappings_data)
            }

        except Exception as e:
            logger.error(f"Error getting unit mappings: {str(e)}")
            return {
                "success": False,
                "message": f"マッピング取得中にエラーが発生しました: {str(e)}"
            }

    def update_unit_mapping(self, mapping_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        単元マッピングを更新
        
        Args:
            mapping_id: マッピングID
            update_data: 更新データ
            
        Returns:
            Dict: 更新結果
        """
        try:
            logger.info(f"Updating unit mapping {mapping_id}")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "マッピング更新権限がありません"
                }

            # マッピングの存在確認
            mapping = UnitItemMapping.query.get(mapping_id)
            if not mapping:
                return {
                    "success": False,
                    "message": "指定されたマッピングが見つかりません"
                }

            # 更新データの適用
            updated_mapping = self._apply_mapping_updates(mapping, update_data)
            
            db.session.commit()
            
            return {
                "success": True,
                "message": "マッピングが正常に更新されました",
                "mapping": {
                    "id": updated_mapping.id,
                    "unit_id": updated_mapping.unit_id,
                    "item_id": updated_mapping.item_id,
                    "item_type": updated_mapping.item_type,
                    "order_index": updated_mapping.order_index,
                    "is_required": updated_mapping.is_required,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error updating unit mapping: {str(e)}")
            db.session.rollback()
            return {
                "success": False,
                "message": f"マッピング更新中にエラーが発生しました: {str(e)}"
            }

    def delete_unit_mapping(self, mapping_id: int) -> Dict[str, Any]:
        """
        単元マッピングを削除
        
        Args:
            mapping_id: マッピングID
            
        Returns:
            Dict: 削除結果
        """
        try:
            logger.info(f"Deleting unit mapping {mapping_id}")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "マッピング削除権限がありません"
                }

            # マッピングの存在確認
            mapping = UnitItemMapping.query.get(mapping_id)
            if not mapping:
                return {
                    "success": False,
                    "message": "指定されたマッピングが見つかりません"
                }

            # 削除実行
            db.session.delete(mapping)
            db.session.commit()
            
            return {
                "success": True,
                "message": "マッピングが正常に削除されました",
                "deleted_mapping_id": mapping_id
            }

        except Exception as e:
            logger.error(f"Error deleting unit mapping: {str(e)}")
            db.session.rollback()
            return {
                "success": False,
                "message": f"マッピング削除中にエラーが発生しました: {str(e)}"
            }

    def batch_create_mappings(self, batch_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        マッピング一括作成
        
        Args:
            batch_data: 一括作成データ
            
        Returns:
            Dict: 一括作成結果
        """
        try:
            logger.info(f"Batch creating {len(batch_data)} mappings")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "マッピング作成権限がありません"
                }

            successful_creates = []
            failed_creates = []
            
            for mapping_data in batch_data:
                try:
                    result = self.create_unit_mappings(mapping_data)
                    if result['success']:
                        successful_creates.extend(result['mappings'])
                    else:
                        failed_creates.append({
                            "data": mapping_data,
                            "error": result['message']
                        })
                        
                except Exception as e:
                    failed_creates.append({
                        "data": mapping_data,
                        "error": str(e)
                    })
            
            return {
                "success": len(failed_creates) == 0,
                "successful_creates": successful_creates,
                "failed_creates": failed_creates,
                "total_processed": len(batch_data),
                "success_count": len(successful_creates),
                "failure_count": len(failed_creates)
            }

        except Exception as e:
            logger.error(f"Error in batch mapping creation: {str(e)}")
            return {
                "success": False,
                "message": f"一括マッピング作成中にエラーが発生しました: {str(e)}"
            }

    def _validate_mapping_data(self, mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """マッピングデータの検証"""
        required_fields = ['unit_id', 'item_id', 'item_type']
        
        for field in required_fields:
            if field not in mapping_data:
                return {
                    "valid": False,
                    "message": f"必須フィールド '{field}' が不足しています"
                }
        
        # 単元の存在確認
        unit = CurriculumUnit.query.get(mapping_data['unit_id'])
        if not unit:
            return {
                "valid": False,
                "message": "指定された単元が見つかりません"
            }
        
        # アイテムタイプの検証
        valid_item_types = ['quiz', 'material', 'assignment', 'video', 'document']
        if mapping_data['item_type'] not in valid_item_types:
            return {
                "valid": False,
                "message": f"無効なアイテムタイプです。有効な値: {', '.join(valid_item_types)}"
            }
        
        # 重複チェック
        existing_mapping = UnitItemMapping.query.filter_by(
            unit_id=mapping_data['unit_id'],
            item_id=mapping_data['item_id'],
            item_type=mapping_data['item_type']
        ).first()
        
        if existing_mapping:
            return {
                "valid": False,
                "message": "このマッピングは既に存在します"
            }
        
        return {"valid": True}

    def _create_mappings(self, mapping_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """マッピングの実際の作成処理"""
        created_mappings = []
        
        # 単一マッピングの場合
        if 'item_id' in mapping_data:
            mapping = UnitItemMapping(
                unit_id=mapping_data['unit_id'],
                item_id=mapping_data['item_id'],
                item_type=mapping_data['item_type'],
                order_index=mapping_data.get('order_index', 0),
                is_required=mapping_data.get('is_required', False),
                created_by=current_user.id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(mapping)
            db.session.flush()  # IDを取得するため
            
            created_mappings.append({
                "id": mapping.id,
                "unit_id": mapping.unit_id,
                "item_id": mapping.item_id,
                "item_type": mapping.item_type,
                "order_index": mapping.order_index,
                "is_required": mapping.is_required
            })
        
        # 複数アイテムの場合
        elif 'items' in mapping_data:
            for i, item_data in enumerate(mapping_data['items']):
                mapping = UnitItemMapping(
                    unit_id=mapping_data['unit_id'],
                    item_id=item_data['item_id'],
                    item_type=item_data['item_type'],
                    order_index=item_data.get('order_index', i),
                    is_required=item_data.get('is_required', False),
                    created_by=current_user.id,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(mapping)
                db.session.flush()  # IDを取得するため
                
                created_mappings.append({
                    "id": mapping.id,
                    "unit_id": mapping.unit_id,
                    "item_id": mapping.item_id,
                    "item_type": mapping.item_type,
                    "order_index": mapping.order_index,
                    "is_required": mapping.is_required
                })
        
        return created_mappings

    def _apply_mapping_updates(self, mapping: UnitItemMapping, 
                             update_data: Dict[str, Any]) -> UnitItemMapping:
        """マッピング更新の適用"""
        updatable_fields = ['order_index', 'is_required']
        
        for field in updatable_fields:
            if field in update_data:
                setattr(mapping, field, update_data[field])
        
        # 更新時刻の記録
        mapping.updated_at = datetime.utcnow()
        
        return mapping