"""
学習パターン分析サービスの使用例
このファイルは削除してください - 実装例として提供
"""

from app.services.pattern_analyzer import PatternAnalyzerService
from app.models import User


def example_usage():
    """パターン分析サービスの使用例"""
    
    # サービスのインスタンス化
    analyzer = PatternAnalyzerService()
    
    # 特定の学生のパターンを分析
    student_id = 1
    requester = User.query.filter_by(role='teacher').first()  # 教師権限で実行
    
    try:
        # 全パターンの分析を実行
        analysis_result = analyzer.analyze_student_patterns(student_id, requester)
        
        print("=== 学習パターン分析結果 ===")
        print(f"学生ID: {analysis_result['student_id']}")
        print(f"分析時刻: {analysis_result['analysis_timestamp']}")
        print(f"全体信頼度: {analysis_result['overall_confidence']}")
        
        # 各パターンの結果を表示
        patterns = analysis_result['patterns']
        
        # 時間帯別傾向
        if 'time_preference' in patterns:
            time_data = patterns['time_preference']
            print(f"\n-- 時間帯別傾向 (信頼度: {time_data['confidence']}) --")
            print(f"好む時間帯: {time_data['data'].get('preferred_period', 'データなし')}")
            print(f"サンプル数: {time_data['sample_size']}")
        
        # 難易度別傾向
        if 'difficulty_preference' in patterns:
            diff_data = patterns['difficulty_preference']
            print(f"\n-- 難易度別傾向 (信頼度: {diff_data['confidence']}) --")
            print(f"適性難易度: {diff_data['data'].get('preferred_difficulty', 'データなし')}")
            print(f"推薦: {diff_data['data'].get('recommendation', 'データなし')}")
        
        # 科目別強み
        if 'subject_strength' in patterns:
            subj_data = patterns['subject_strength']
            print(f"\n-- 科目別強み (信頼度: {subj_data['confidence']}) --")
            print(f"最強科目: {subj_data['data'].get('strongest_subject', 'データなし')}")
            recommendations = subj_data['data'].get('recommendations', [])
            for rec in recommendations:
                print(f"  - {rec}")
        
        # 学習スタイル
        if 'learning_style' in patterns:
            style_data = patterns['learning_style']
            print(f"\n-- 学習スタイル (信頼度: {style_data['confidence']}) --")
            print(f"主要スタイル: {style_data['data'].get('primary_style', 'データなし')}")
            session_stats = style_data['data'].get('session_stats', {})
            if session_stats:
                print(f"平均学習時間: {session_stats.get('avg_session_minutes', 0)}分")
                print(f"総セッション数: {session_stats.get('total_sessions', 0)}")
        
        # 保存されたパターンの取得例
        saved_patterns = analyzer.get_student_patterns(student_id, requester)
        print(f"\n-- 保存されたパターン --")
        print(f"最終更新: {saved_patterns['last_updated']}")
        print(f"保存パターン数: {len(saved_patterns['patterns'])}")
        
    except Exception as e:
        print(f"エラー: {e}")


def individual_analyzer_usage():
    """個別分析器の使用例"""
    
    from app.services.pattern_analyzer import (
        TimePreferenceAnalyzer,
        DifficultyPreferenceAnalyzer,
        SubjectStrengthAnalyzer,
        LearningStyleAnalyzer
    )
    
    student_id = 1
    
    # 個別の分析器を直接使用
    time_analyzer = TimePreferenceAnalyzer()
    time_result = time_analyzer.analyze(student_id)
    print("時間帯分析結果:", time_result)
    
    difficulty_analyzer = DifficultyPreferenceAnalyzer()
    diff_result = difficulty_analyzer.analyze(student_id)
    print("難易度分析結果:", diff_result)
    
    subject_analyzer = SubjectStrengthAnalyzer()
    subj_result = subject_analyzer.analyze(student_id)
    print("科目強み分析結果:", subj_result)
    
    style_analyzer = LearningStyleAnalyzer()
    style_result = style_analyzer.analyze(student_id)
    print("学習スタイル分析結果:", style_result)


# 使用方法のコメント
"""
# Flaskアプリケーション内での使用例:

from app.services import PatternAnalyzerService
from flask_login import current_user

@app.route('/api/student/<int:student_id>/patterns')
@login_required
def get_student_patterns(student_id):
    analyzer = PatternAnalyzerService() 
    
    try:
        # 分析を実行
        result = analyzer.analyze_student_patterns(student_id, current_user)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/student/<int:student_id>/saved-patterns')
@login_required
def get_saved_patterns(student_id):
    analyzer = PatternAnalyzerService()
    
    try:
        # 保存されたパターンを取得
        result = analyzer.get_student_patterns(student_id, current_user)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# AI推薦エンジンでの使用例:

def generate_ai_recommendations(student_id):
    analyzer = PatternAnalyzerService()
    
    # パターンデータを取得
    patterns = analyzer.get_student_patterns(student_id)
    
    # パターンデータを基に推薦を生成
    recommendations = []
    
    if patterns['patterns'].get('time_preference'):
        time_data = patterns['patterns']['time_preference']
        preferred_time = time_data['data'].get('preferred_period')
        
        if preferred_time == 'morning':
            recommendations.append({
                'type': 'timing',
                'message': '午前中の学習が効果的です',
                'suggested_time': '9:00-11:00'
            })
    
    if patterns['patterns'].get('difficulty_preference'):
        diff_data = patterns['patterns']['difficulty_preference']
        preferred_diff = diff_data['data'].get('preferred_difficulty')
        
        if preferred_diff:
            recommendations.append({
                'type': 'difficulty',
                'message': f'難易度レベル{preferred_diff}の問題をお勧めします',
                'target_difficulty': preferred_diff
            })
    
    return recommendations
"""

if __name__ == "__main__":
    # 実際の使用時はFlaskアプリケーションコンテキスト内で実行
    print("パターン分析サービスの使用例:")
    print("この例を実行するには、Flaskアプリケーションコンテキストが必要です")