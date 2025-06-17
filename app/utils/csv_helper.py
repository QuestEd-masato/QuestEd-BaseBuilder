"""
CSV エクスポートヘルパー - 文字化け対策版

日本語データのCSVエクスポートでExcelでの文字化けを防ぐための
UTF-8 BOM付きエクスポート機能を提供

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import csv
import io
from flask import make_response
from typing import List, Dict, Any, Union


def export_to_csv_utf8_bom(data: List[Dict[str, Any]], 
                          filename: str, 
                          headers: List[str] = None,
                          field_order: List[str] = None) -> Any:
    """
    UTF-8 BOM付きCSVエクスポート（Excel対応）
    
    Args:
        data: エクスポートするデータのリスト
        filename: ダウンロードファイル名
        headers: カスタムヘッダー（Noneの場合はデータから自動生成）
        field_order: フィールドの出力順序
        
    Returns:
        Flask Response オブジェクト
    """
    
    # BytesIOを使用してBOM付きUTF-8で出力
    output = io.BytesIO()
    
    # UTF-8 BOMを追加
    output.write(b'\xef\xbb\xbf')
    
    # TextIOWrapperを使用してUTF-8テキストとして書き込み
    text_output = io.TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.writer(text_output, quoting=csv.QUOTE_ALL)
    
    if data:
        # ヘッダー行の準備
        if headers:
            writer.writerow(headers)
        elif field_order:
            writer.writerow(field_order)
        else:
            # データの最初の行からキーを取得
            writer.writerow(data[0].keys())
        
        # データ行の書き込み
        for row in data:
            if field_order:
                # 指定された順序でフィールドを出力
                row_data = [str(row.get(field, '')) for field in field_order]
            else:
                # データの順序で出力
                row_data = [str(value) for value in row.values()]
            
            writer.writerow(row_data)
    
    # バッファをフラッシュして内容を確定
    text_output.flush()
    output.seek(0)
    
    # レスポンス作成
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


def export_to_csv_shift_jis(data: List[Dict[str, Any]], 
                           filename: str, 
                           headers: List[str] = None,
                           field_order: List[str] = None) -> Any:
    """
    Shift-JIS CSVエクスポート（古いExcel対応）
    
    Args:
        data: エクスポートするデータのリスト
        filename: ダウンロードファイル名
        headers: カスタムヘッダー
        field_order: フィールドの出力順序
        
    Returns:
        Flask Response オブジェクト
    """
    
    # StringIOでUTF-8として作成
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    if data:
        # ヘッダー行
        if headers:
            writer.writerow(headers)
        elif field_order:
            writer.writerow(field_order)
        else:
            writer.writerow(data[0].keys())
        
        # データ行
        for row in data:
            if field_order:
                row_data = [str(row.get(field, '')) for field in field_order]
            else:
                row_data = [str(value) for value in row.values()]
            
            writer.writerow(row_data)
    
    # Shift-JISに変換（エラー文字は無視）
    csv_content = output.getvalue()
    try:
        sjis_content = csv_content.encode('shift-jis', 'ignore')
    except UnicodeEncodeError:
        # Shift-JISで表現できない文字がある場合はUTF-8で出力
        sjis_content = csv_content.encode('utf-8-sig')
    
    # レスポンス作成
    response = make_response(sjis_content)
    response.headers['Content-Type'] = 'text/csv; charset=shift-jis'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    
    return response


def export_ranking_to_csv(ranking_data: Dict[str, Any], 
                         ranking_type: str, 
                         encoding: str = 'utf-8-bom') -> Any:
    """
    ランキングデータのCSVエクスポート専用関数
    
    Args:
        ranking_data: ランキングデータ
        ranking_type: ランキングタイプ
        encoding: エンコーディング ('utf-8-bom' または 'shift-jis')
        
    Returns:
        Flask Response オブジェクト
    """
    
    # ランキングデータを変換
    csv_data = []
    for student in ranking_data.get('rankings', []):
        csv_data.append({
            '順位': student.get('rank', ''),
            '学生名': student.get('student_name', ''),
            'スコア': student.get('score', ''),
            '学校名': student.get('school_name', ''),
            'クラス名': student.get('class_name', '')
        })
    
    filename = f'ranking_{ranking_type}_{ranking_data.get("last_updated", "").replace(":", "-").split(".")[0]}.csv'
    
    if encoding == 'shift-jis':
        return export_to_csv_shift_jis(
            csv_data, 
            filename,
            headers=['順位', '学生名', 'スコア', '学校名', 'クラス名']
        )
    else:
        return export_to_csv_utf8_bom(
            csv_data, 
            filename,
            headers=['順位', '学生名', 'スコア', '学校名', 'クラス名']
        )


def export_users_to_csv(users_data: List[Dict[str, Any]], 
                       encoding: str = 'utf-8-bom') -> Any:
    """
    ユーザーデータのCSVエクスポート
    
    Args:
        users_data: ユーザーデータのリスト
        encoding: エンコーディング
        
    Returns:
        Flask Response オブジェクト
    """
    
    filename = 'users_export.csv'
    headers = ['ユーザー名', '氏名', 'メールアドレス', '役割', '学校', '登録日']
    
    if encoding == 'shift-jis':
        return export_to_csv_shift_jis(users_data, filename, headers)
    else:
        return export_to_csv_utf8_bom(users_data, filename, headers)


def export_curriculum_to_csv(curriculum_data: Dict[str, Any], 
                            curriculum_title: str,
                            encoding: str = 'utf-8-bom') -> Any:
    """
    カリキュラムデータのCSVエクスポート
    
    Args:
        curriculum_data: カリキュラムデータ
        curriculum_title: カリキュラムタイトル
        encoding: エンコーディング
        
    Returns:
        Flask Response オブジェクト
    """
    
    csv_data = []
    
    # フェーズデータを展開
    for phase in curriculum_data.get('phases', []):
        for week in phase.get('weeks', []):
            csv_data.append({
                'フェーズ': phase.get('name', phase.get('phase', '')),
                '週': week.get('week', ''),
                '時間数': week.get('hours', ''),
                'テーマ': week.get('theme', ''),
                '活動内容': week.get('activities', ''),
                '教師のサポート': week.get('teacher_support', ''),
                '評価方法': week.get('evaluation', '')
            })
    
    filename = f'curriculum_{curriculum_title.replace(" ", "_")}.csv'
    headers = ['フェーズ', '週', '時間数', 'テーマ', '活動内容', '教師のサポート', '評価方法']
    
    if encoding == 'shift-jis':
        return export_to_csv_shift_jis(csv_data, filename, headers)
    else:
        return export_to_csv_utf8_bom(csv_data, filename, headers)