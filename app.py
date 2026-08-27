"""
新概念英语第一册 - 单词练习工具 v2.0
Flask + SQLite + 用户系统 + 全屏PPT答题
"""
import sqlite3
import random
import hashlib
from flask import Flask, g, jsonify, request, render_template, session

app = Flask(__name__)
app.secret_key = 'nce1_study_secret_key_2024'
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'nce_words.db')

# ========== 数据库操作 ==========
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ========== 工具函数 ==========
def get_current_user():
    """获取当前登录用户"""
    user_id = session.get('user_id')
    if user_id:
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(user) if user else None
    return None

def login_required():
    """检查是否登录，未登录则返回错误"""
    user = get_current_user()
    if not user:
        return None
    return user

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ========== 单词生成逻辑 ==========
def generate_options(correct_word, field, all_words, count=3):
    pool = [w for w in all_words if w[field] != correct_word[field]]
    selected = random.sample(pool, min(count, len(pool)))
    return [w[field] for w in selected]

def generate_cloze(word):
    """挖空连续字母块，返回 (hint_str, missing_letters)"""
    w = word['word']
    l = len(w)
    # 只处理纯字母部分
    letters = [(i, c) for i, c in enumerate(w) if c.isalpha()]
    if len(letters) < 2:
        i, c = letters[0]
        return w[:i] + '_' + w[i+1:], c

    # 根据单词长度决定挖空块大小
    if l <= 3:
        size = 1
    elif l <= 5:
        size = random.randint(1, 2)
    elif l <= 7:
        size = random.randint(2, 3)
    else:
        size = random.randint(2, 4)

    size = min(size, len(letters))
    # 随机选择一个连续块
    max_start = len(letters) - size
    start_idx = random.randint(0, max_start)
    start_pos = letters[start_idx][0]
    end_pos = letters[start_idx + size - 1][0] + 1

    missing = w[start_pos:end_pos]
    hint = w[:start_pos] + '_' * len(missing) + w[end_pos:]
    return hint, missing


def generate_cloze_options(missing_letters, count=3):
    """生成干扰字母组合作为选项"""
    vowels = 'aeiou'
    consonants = 'bcdfghjklmnpqrstvwxyz'
    ml = missing_letters.lower()
    n = len(missing_letters)

    distractors = []
    attempts = 0
    max_attempts = count * 20

    while len(distractors) < count and attempts < max_attempts:
        attempts += 1
        if n == 1:
            # 单字母：替换成相似字母
            if ml in vowels:
                c = random.choice(vowels.replace(ml, ''))
            else:
                # 50%换成其他辅音，50%换成元音
                if random.random() > 0.5 and ml in consonants:
                    pool = consonants.replace(ml, '') if len(consonants.replace(ml, '')) > 1 else vowels
                else:
                    pool = vowels + consonants.replace(ml, '')
                c = random.choice(pool)
            d = c.upper() if missing_letters[0].isupper() else c
        else:
            # 多字母：保持元音/辅音模式，生成相似组合
            result_chars = []
            for ch in missing_letters:
                is_upper = ch.isupper()
                ch_low = ch.lower()
                if ch_low in vowels:
                    pool = vowels.replace(ch_low, '')
                else:
                    pool = consonants.replace(ch_low, '') if ch_low in consonants else consonants
                if not pool:
                    pool = vowels + consonants
                c = random.choice(pool)
                result_chars.append(c.upper() if is_upper else c)
            d = ''.join(result_chars)

        if d.lower() != ml and d not in distractors:
            distractors.append(d)

    # 如果没生成足够的干扰项，用随机字母补全
    while len(distractors) < count:
        d = ''.join(random.choice('aeioubcdfghjklmnpqrstvwxyz') for _ in range(n))
        if d.lower() != ml and d not in distractors:
            distractors.append(d)

    return distractors

# ========== 路由 ==========
@app.route('/')
def index():
    return render_template('index.html')

# ---- 用户认证 ----
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', username)
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if len(username) < 2 or len(username) > 20:
        return jsonify({'error': '用户名需2-20个字符'}), 400
    if len(password) < 4:
        return jsonify({'error': '密码至少4个字符'}), 400
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({'error': '用户名已存在'}), 400
    pw_hash = hash_password(password)
    db.execute("INSERT INTO users (username, password_hash, nickname) VALUES (?, ?, ?)",
               (username, pw_hash, nickname))
    db.execute("INSERT INTO user_progress (user_id, score) VALUES (last_insert_rowid(), 0)")
    db.commit()
    return jsonify({'success': True, 'message': '注册成功，请登录'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'error': '请输入用户名和密码'}), 400
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user or user['password_hash'] != hash_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401
    session['user_id'] = user['id']
    # 确保有进度记录
    prog = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user['id'],)).fetchone()
    if not prog:
        db.execute("INSERT INTO user_progress (user_id, score) VALUES (?, 0)", (user['id'],))
        db.commit()
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'] or user['username']
        }
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/user', methods=['GET'])
def get_user():
    user = get_current_user()
    if not user:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'] or user['username']
        }
    })

# ---- 单词练习 ----
@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    db = get_db()
    lessons = db.execute(
        "SELECT lesson, COUNT(*) as cnt FROM words GROUP BY lesson ORDER BY lesson"
    ).fetchall()
    return jsonify({'data': [dict(l) for l in lessons]})

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有思维导图分类"""
    db = get_db()
    cats = db.execute(
        "SELECT category, COUNT(*) as cnt FROM words WHERE category != '' GROUP BY category ORDER BY category"
    ).fetchall()
    return jsonify({'data': [dict(c) for c in cats]})

@app.route('/api/words/quiz', methods=['POST'])
def get_quiz():
    """获取指定课程和模式的练习题"""
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401

    data = request.json
    mode = data.get('mode', 'en2cn')
    lesson = data.get('lesson', '')  # 单个课程号
    category = data.get('category', '')  # 思维导图分类

    db = get_db()
    if lesson:
        words = db.execute("SELECT * FROM words WHERE lesson = ?", (int(lesson),)).fetchall()
    elif category:
        words = db.execute("SELECT * FROM words WHERE category = ?", (category,)).fetchall()
    else:
        words = db.execute("SELECT * FROM words").fetchall()

    words = [dict(w) for w in words]
    if not words:
        return jsonify({'error': '没有符合条件的单词'}), 404

    # 获取该用户在该范围内的错题（用于优先出题）
    if lesson or category:
        error_ids = db.execute("""
            SELECT DISTINCT word_id FROM error_log
            WHERE user_id = ? AND word_id IN (
                SELECT id FROM words WHERE """ + ("lesson = ?" if lesson else "category = ?") + """
            )
        """, (user['id'], int(lesson) if lesson else category)).fetchall()
        error_id_set = {e['word_id'] for e in error_ids}
        # 错题优先排在前面
        error_words = [w for w in words if w['id'] in error_id_set]
        normal_words = [w for w in words if w['id'] not in error_id_set]
        random.shuffle(error_words)
        random.shuffle(normal_words)
        selected = error_words + normal_words
    else:
        random.shuffle(words)
        selected = words

    result = []
    for word in selected:
        if mode == 'en2cn':
            options = generate_options(word, 'chinese', words)
            opts = options + [word['chinese']]
            random.shuffle(opts)
            result.append({
                'word_id': word['id'],
                'question': word['word'],
                'phonetic': word.get('phonetic', ''),
                'lesson': word.get('lesson', ''),
                'answer': word['chinese'],
                'options': opts
            })
        elif mode == 'cn2en':
            options = generate_options(word, 'word', words)
            opts = options + [word['word']]
            random.shuffle(opts)
            result.append({
                'word_id': word['id'],
                'question': word['chinese'],
                'phonetic': word.get('phonetic', ''),
                'lesson': word.get('lesson', ''),
                'answer': word['word'],
                'options': opts
            })
        elif mode == 'cloze':
            hint, missing = generate_cloze(word)
            options = generate_cloze_options(missing)
            opts = options + [missing]
            random.shuffle(opts)
            result.append({
                'word_id': word['id'],
                'question': hint,
                'full_word': word['word'],
                'chinese': word['chinese'],
                'phonetic': word.get('phonetic', ''),
                'lesson': word.get('lesson', ''),
                'answer': missing,
                'options': opts
            })

    # 确定标题
    if lesson:
        title = f'Lesson {lesson}'
    elif category:
        title = category
    else:
        title = '全部课程'

    return jsonify({
        'data': result,
        'lesson_name': title,
        'total': len(result)
    })

# ---- 答题记录 ----
@app.route('/api/log_answer', methods=['POST'])
def log_answer():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401

    data = request.json
    word_id = data.get('word_id')
    correct = data.get('correct', False)
    mode = data.get('mode', '')
    user_answer = data.get('user_answer', '')

    db = get_db()
    uid = user['id']

    if not correct and word_id:
        db.execute("INSERT INTO error_log (user_id, word_id, error_type) VALUES (?, ?, ?)",
                   (uid, int(word_id), mode))

    # 更新统计
    stat = db.execute("""
        SELECT * FROM stats WHERE user_id = ? AND mode = ?
        AND date(created_at) = date('now', 'localtime')
        ORDER BY id DESC LIMIT 1
    """, (uid, mode)).fetchone()

    if stat:
        db.execute("UPDATE stats SET total_questions = total_questions + 1, correct_count = correct_count + ?, wrong_count = wrong_count + ? WHERE id = ?",
                   (1 if correct else 0, 0 if correct else 1, stat['id']))
    else:
        db.execute("INSERT INTO stats (user_id, total_questions, correct_count, wrong_count, mode) VALUES (?, 1, ?, ?, ?)",
                   (uid, 1 if correct else 0, 0 if correct else 1, mode))

    # 更新进度
    score_add = 10 if correct else 0
    today = db.execute("SELECT date('now', 'localtime') as d").fetchone()['d']

    prog = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (uid,)).fetchone()
    if prog:
        new_streak = prog['study_streak']
        if prog['last_study_date'] != today:
            yesterday = db.execute("SELECT date('now', '-1 day', 'localtime') as d").fetchone()['d']
            if prog['last_study_date'] == yesterday:
                new_streak = prog['study_streak'] + 1
            else:
                new_streak = 1
        db.execute("""
            UPDATE user_progress SET
                score = score + ?,
                total_practice_count = total_practice_count + 1,
                study_streak = ?,
                last_study_date = ?
            WHERE user_id = ?
        """, (score_add, new_streak, today, uid))

    db.commit()
    return jsonify({'success': True, 'score_add': score_add})

@app.route('/api/combo_update', methods=['POST'])
def combo_update():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    data = request.json
    combo = data.get('combo', 0)
    db = get_db()
    prog = db.execute("SELECT max_combo FROM user_progress WHERE user_id = ?", (user['id'],)).fetchone()
    if prog and combo > prog['max_combo']:
        db.execute("UPDATE user_progress SET max_combo = ? WHERE user_id = ?", (combo, user['id']))
        db.commit()
    return jsonify({'success': True})

# ---- 统计 ----
@app.route('/api/stats', methods=['GET'])
def get_stats():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    uid = user['id']
    db = get_db()
    total = db.execute("SELECT COUNT(*) as cnt FROM words").fetchone()['cnt']

    # 错题统计
    error_words = db.execute("""
        SELECT w.id, w.word, w.chinese, w.phonetic, w.lesson, COUNT(e.id) as error_count
        FROM words w
        JOIN error_log e ON w.id = e.word_id
        WHERE e.user_id = ?
        GROUP BY w.id
        ORDER BY error_count DESC
    """, (uid,)).fetchall()

    progress = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (uid,)).fetchone()

    recent = db.execute("""
        SELECT mode, total_questions, correct_count, wrong_count, created_at
        FROM stats WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 20
    """, (uid,)).fetchall()

    mode_stats = db.execute("""
        SELECT mode, SUM(total_questions) as total_q,
               SUM(correct_count) as total_c, SUM(wrong_count) as total_w
        FROM stats WHERE user_id = ?
        GROUP BY mode
    """, (uid,)).fetchall()

    # 每课掌握度
    lesson_mastery = db.execute("""
        SELECT w.lesson, COUNT(DISTINCT e.word_id) as err_word_count
        FROM error_log e JOIN words w ON e.word_id = w.id
        WHERE e.user_id = ?
        GROUP BY w.lesson
    """, (uid,)).fetchall()

    return jsonify({
        'total_words': total,
        'error_words': [dict(w) for w in error_words],
        'progress': dict(progress) if progress else {},
        'recent': [dict(r) for r in recent],
        'mode_stats': [dict(m) for m in mode_stats],
        'lesson_mastery': [dict(l) for l in lesson_mastery]
    })

# ---- 错题本 ----
@app.route('/api/error_words', methods=['GET'])
def get_error_words():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    try:
        db = get_db()

        # 按题型分组查询
        mode_filter = request.args.get('mode', '')  # 可选过滤

        if mode_filter:
            words = db.execute("""
                SELECT w.id, w.word, w.chinese, w.phonetic, w.lesson, COUNT(e.id) as error_count,
                       e.error_type,
                       MIN(e.created_at) as first_error, MAX(e.created_at) as last_error
                FROM words w
                JOIN error_log e ON w.id = e.word_id
                WHERE e.user_id = ? AND e.error_type = ?
                GROUP BY w.id
                ORDER BY error_count DESC
            """, (user['id'], mode_filter)).fetchall()
        else:
            words = db.execute("""
                SELECT w.id, w.word, w.chinese, w.phonetic, w.lesson, COUNT(e.id) as error_count,
                       e.error_type,
                       MIN(e.created_at) as first_error, MAX(e.created_at) as last_error
                FROM words w
                JOIN error_log e ON w.id = e.word_id
                WHERE e.user_id = ?
                GROUP BY w.id, e.error_type
                ORDER BY error_count DESC
            """, (user['id'],)).fetchall()

        # 各题型统计
        mode_stats = db.execute("""
            SELECT error_type as mode, COUNT(*) as error_count, COUNT(DISTINCT word_id) as word_count
            FROM error_log
            WHERE user_id = ?
            GROUP BY error_type
        """, (user['id'],)).fetchall()

        return jsonify({
            'data': [dict(w) for w in words],
            'mode_stats': [dict(m) for m in mode_stats]
        })
    except Exception as e:
        print(f'[ERROR] get_error_words: {e}')
        return jsonify({'error': '加载错题本失败', 'data': [], 'mode_stats': []}), 200

@app.route('/api/error_words/<int:word_id>/reset', methods=['POST'])
def reset_error_word(word_id):
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    db = get_db()
    db.execute("DELETE FROM error_log WHERE user_id = ? AND word_id = ?", (user['id'], word_id))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/error_words/clear', methods=['POST'])
def clear_error_words():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    db = get_db()
    data = request.json or {}
    mode = data.get('mode', '')
    if mode:
        db.execute("DELETE FROM error_log WHERE user_id = ? AND error_type = ?", (user['id'], mode))
    else:
        db.execute("DELETE FROM error_log WHERE user_id = ?", (user['id'],))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/reset_progress', methods=['POST'])
def reset_progress():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    uid = user['id']
    db = get_db()
    db.execute("DELETE FROM stats WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM error_log WHERE user_id = ?", (uid,))
    db.execute("UPDATE user_progress SET score=0, max_combo=0, study_streak=0, total_practice_count=0, last_study_date='' WHERE user_id = ?", (uid,))
    db.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    import os
    if not os.path.exists(DATABASE):
        print('[ERROR] 数据库未初始化，请先运行: python init_db.py')
        exit(1)
    app.run(debug=True, host='0.0.0.0', port=5001)
