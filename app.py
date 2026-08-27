"""
新概念英语第一册 - 单词练习工具 v3.0
Flask + MySQL + 用户系统 + 全屏PPT答题 + 多单词集
"""
import pymysql
import random
import hashlib
from flask import Flask, g, jsonify, request, render_template, session

app = Flask(__name__)
app.secret_key = 'nce1_study_secret_key_2024'

# ========== MySQL 连接配置 ==========
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'devuser',
    'password': 'Dev@2026',
    'database': 'words_test',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# ========== 数据库操作 ==========
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = pymysql.connect(**MYSQL_CONFIG)
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
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
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

def get_user_word_set(user):
    """获取用户当前单词集，优先 session，其次 default_word_set"""
    ws = session.get('word_set')
    if not ws:
        ws = user.get('default_word_set', '')
    return ws

# ========== 单词生成逻辑 ==========
def generate_options(correct_word, field, all_words, count=3):
    pool = [w for w in all_words if w[field] != correct_word[field]]
    selected = random.sample(pool, min(count, len(pool)))
    return [w[field] for w in selected]

def generate_cloze(word):
    """挖空连续字母块，返回 (hint_str, missing_letters)"""
    w = word['word']
    l = len(w)
    letters = [(i, c) for i, c in enumerate(w) if c.isalpha()]
    if len(letters) < 2:
        i, c = letters[0]
        return w[:i] + '_' + w[i+1:], c

    if l <= 3:
        size = 1
    elif l <= 5:
        size = random.randint(1, 2)
    elif l <= 7:
        size = random.randint(2, 3)
    else:
        size = random.randint(2, 4)

    size = min(size, len(letters))
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
            if ml in vowels:
                c = random.choice(vowels.replace(ml, ''))
            else:
                if random.random() > 0.5 and ml in consonants:
                    pool = consonants.replace(ml, '') if len(consonants.replace(ml, '')) > 1 else vowels
                else:
                    pool = vowels + consonants.replace(ml, '')
                c = random.choice(pool)
            d = c.upper() if missing_letters[0].isupper() else c
        else:
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

    while len(distractors) < count:
        d = ''.join(random.choice('aeioubcdfghjklmnpqrstvwxyz') for _ in range(n))
        if d.lower() != ml and d not in distractors:
            distractors.append(d)

    return distractors

# ========== 路由 ==========
@app.route('/')
def index():
    return render_template('index.html')

# ---- 单词集 ----
@app.route('/api/wordsets', methods=['GET'])
def get_wordsets():
    """获取所有单词集列表"""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT word_set, COUNT(*) as cnt FROM words GROUP BY word_set ORDER BY MIN(id)")
        sets = cursor.fetchall()
    return jsonify({'data': [dict(s) for s in sets]})

@app.route('/api/wordsets/default', methods=['POST'])
def set_default_wordset():
    """设置用户默认单词集"""
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    data = request.json or {}
    ws = data.get('word_set', '')
    session['word_set'] = ws
    with db.cursor() as cursor:
        cursor.execute("UPDATE users SET default_word_set = %s WHERE id = %s", (ws, user['id']))
    db = get_db()
    db.commit()
    return jsonify({'success': True})

@app.route('/api/wordsets/import', methods=['POST'])
def import_wordset():
    """导入新单词集（JSON格式，保存为文件并写入数据库）"""
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    data = request.json or {}
    word_set_name = data.get('word_set', '').strip()
    words_data = data.get('words', [])
    if not word_set_name:
        return jsonify({'error': '单词集名称不能为空'}), 400
    if not words_data or not isinstance(words_data, list):
        return jsonify({'error': '单词数据不能为空'}), 400

    # 验证单词格式
    for w in words_data:
        if not isinstance(w, dict) or 'word' not in w or 'chinese' not in w:
            return jsonify({'error': '单词格式错误，需包含 word 和 chinese 字段'}), 400

    # 保存为 JSON 文件
    import os, json
    filename = f'{word_set_name}.json'
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(words_data, f, ensure_ascii=False, indent=2)

    # 写入数据库
    db = get_db()
    with db.cursor() as cursor:
        # 检查是否已存在该单词集
        cursor.execute("SELECT COUNT(*) as cnt FROM words WHERE word_set = %s", (word_set_name,))
        if cursor.fetchone()['cnt'] > 0:
            # 已存在则先删除旧数据
            cursor.execute("DELETE FROM words WHERE word_set = %s", (word_set_name,))
        for w in words_data:
            cursor.execute(
                'INSERT INTO words (word, chinese, phonetic, lesson, category, word_set) VALUES (%s, %s, %s, %s, %s, %s)',
                (w['word'], w['chinese'], w.get('phonetic', ''), w.get('lesson', 1), w.get('category', ''), word_set_name)
            )
    db.commit()

    return jsonify({'success': True, 'word_set': word_set_name, 'count': len(words_data)})

@app.route('/api/wordsets/<word_set_name>', methods=['GET'])
def get_wordset_detail(word_set_name):
    """查看单词集详情：单词列表、课时数、分类数等"""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) as cnt FROM words WHERE word_set = %s", (word_set_name,))
        total = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(DISTINCT lesson) as cnt FROM words WHERE word_set = %s", (word_set_name,))
        lessons = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(DISTINCT category) as cnt FROM words WHERE word_set = %s AND category != ''", (word_set_name,))
        categories = cursor.fetchone()['cnt']

        # 分页查询单词列表
        page = int(request.args.get('page', 1))
        per_page = 50
        offset = (page - 1) * per_page
        cursor.execute("SELECT word, chinese, phonetic, lesson, category FROM words WHERE word_set = %s ORDER BY lesson, id LIMIT %s OFFSET %s",
                       (word_set_name, per_page, offset))
        word_list = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as cnt FROM words WHERE word_set = %s", (word_set_name,))
        total_count = cursor.fetchone()['cnt']
    return jsonify({
        'word_set': word_set_name,
        'total': total,
        'lessons': lessons,
        'categories': categories,
        'words': [dict(w) for w in word_list],
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    })

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
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'error': '用户名已存在'}), 400
        pw_hash = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)",
                       (username, pw_hash, nickname))
        cursor.execute("INSERT INTO user_progress (user_id, score) VALUES (LAST_INSERT_ID(), 0)")
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
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user or user['password_hash'] != hash_password(password):
            return jsonify({'error': '用户名或密码错误'}), 401
        session['user_id'] = user['id']
        session['word_set'] = user.get('default_word_set', '')
        cursor.execute("SELECT * FROM user_progress WHERE user_id = %s", (user['id'],))
        prog = cursor.fetchone()
        if not prog:
            cursor.execute("INSERT INTO user_progress (user_id, score) VALUES (%s, 0)", (user['id'],))
    db.commit()
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'] or user['username'],
            'default_word_set': user.get('default_word_set', '')
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
    ws = session.get('word_set') or user.get('default_word_set', '')
    return jsonify({
        'logged_in': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'] or user['username'],
            'default_word_set': ws
        }
    })

# ---- 单词练习 ----
@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    ws = get_user_word_set(user)
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT lesson, COUNT(*) as cnt FROM words WHERE word_set = %s GROUP BY lesson ORDER BY lesson",
            (ws,)
        )
        lessons = cursor.fetchall()
    return jsonify({'data': [dict(l) for l in lessons]})

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有思维导图分类"""
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    ws = get_user_word_set(user)
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT category, COUNT(*) as cnt FROM words WHERE word_set = %s AND category != '' GROUP BY category ORDER BY category",
            (ws,)
        )
        cats = cursor.fetchall()
    return jsonify({'data': [dict(c) for c in cats]})

@app.route('/api/mastered_count', methods=['GET'])
def get_mastered_count():
    """获取各课时/分类的已掌握单词数（跨单词集通用，按单词文本匹配）"""
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    ws = get_user_word_set(user)
    db = get_db()
    with db.cursor() as cursor:
        # 按课时统计已掌握数（mastered_words 按 word 文本匹配，跨单词集）
        cursor.execute("""
            SELECT w.lesson, COUNT(*) as mastered_cnt
            FROM mastered_words m
            JOIN words w ON m.word = w.word
            WHERE m.user_id = %s AND w.word_set = %s
            GROUP BY w.lesson
        """, (user['id'], ws))
        lesson_data = cursor.fetchall()

        # 按分类统计已掌握数
        cursor.execute("""
            SELECT w.category, COUNT(*) as mastered_cnt
            FROM mastered_words m
            JOIN words w ON m.word = w.word
            WHERE m.user_id = %s AND w.word_set = %s AND w.category != ''
            GROUP BY w.category
        """, (user['id'], ws))
        cat_data = cursor.fetchall()

    return jsonify({
        'lessons': {str(r['lesson']): r['mastered_cnt'] for r in lesson_data},
        'categories': {r['category']: r['mastered_cnt'] for r in cat_data}
    })

@app.route('/api/words/quiz', methods=['POST'])
def get_quiz():
    """获取指定课程和模式的练习题"""
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401

    data = request.json
    mode = data.get('mode', 'en2cn')
    lesson = data.get('lesson', '')
    category = data.get('category', '')
    ws = get_user_word_set(user)

    db = get_db()
    with db.cursor() as cursor:
        if lesson:
            cursor.execute("SELECT * FROM words WHERE word_set = %s AND lesson = %s", (ws, int(lesson)))
        elif category:
            cursor.execute("SELECT * FROM words WHERE word_set = %s AND category = %s", (ws, category))
        else:
            cursor.execute("SELECT * FROM words WHERE word_set = %s", (ws,))
        words = cursor.fetchall()

    words = [dict(w) for w in words]
    if not words:
        return jsonify({'error': '没有符合条件的单词'}), 404

    # 排除已掌握的单词（按单词文本匹配，跨单词集通用）
    word_texts = [w['word'] for w in words]
    with db.cursor() as cursor:
        fmt = ','.join(['%s'] * len(word_texts))
        cursor.execute(f"SELECT word FROM mastered_words WHERE user_id = %s AND word IN ({fmt})",
                       [user['id']] + word_texts)
        mastered_rows = cursor.fetchall()
    mastered_words_set = {m['word'] for m in mastered_rows}
    words = [w for w in words if w['word'] not in mastered_words_set]

    if not words:
        return jsonify({'error': '该范围内所有单词已掌握'}), 404

    # 获取该用户在该范围内的错题（用于优先出题）
    if lesson or category:
        with db.cursor() as cursor:
            word_ids = [w['id'] for w in words]
            fmt = ','.join(['%s'] * len(word_ids))
            cursor.execute(f"""
                SELECT DISTINCT word_id FROM error_log
                WHERE user_id = %s AND word_id IN ({fmt})
            """, [user['id']] + word_ids)
            error_ids = cursor.fetchall()
        error_id_set = {e['word_id'] for e in error_ids}
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
        elif mode == 'spell':
            result.append({
                'word_id': word['id'],
                'question': word['chinese'],
                'full_word': word['word'],
                'chinese': word['chinese'],
                'phonetic': word.get('phonetic', ''),
                'lesson': word.get('lesson', ''),
                'answer': word['word'],
                'word_length': len(word['word'])
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

    # 获取单词文本（用于 mastered_words 跨单词集匹配）
    with db.cursor() as cursor:
        cursor.execute("SELECT word FROM words WHERE id = %s", (int(word_id),))
        word_row = cursor.fetchone()
    word_text = word_row['word'] if word_row else ''

    with db.cursor() as cursor:
        if not correct and word_id:
            cursor.execute("INSERT INTO error_log (user_id, word_id, error_type) VALUES (%s, %s, %s)",
                           (uid, int(word_id), mode))
            # 答错时清除该单词的已掌握记录
            if word_text:
                cursor.execute("DELETE FROM mastered_words WHERE user_id = %s AND word = %s",
                               (uid, word_text))
        elif correct and word_id:
            # 答对时记录为已掌握（按单词文本，跨单词集通用）
            if word_text:
                cursor.execute("""
                    INSERT IGNORE INTO mastered_words (user_id, word)
                    VALUES (%s, %s)
                """, (uid, word_text))

        # 更新统计
        cursor.execute("""
            SELECT * FROM stats WHERE user_id = %s AND mode = %s
            AND DATE(created_at) = CURDATE()
            ORDER BY id DESC LIMIT 1
        """, (uid, mode))
        stat = cursor.fetchone()

        if stat:
            cursor.execute("UPDATE stats SET total_questions = total_questions + 1, correct_count = correct_count + %s, wrong_count = wrong_count + %s WHERE id = %s",
                           (1 if correct else 0, 0 if correct else 1, stat['id']))
        else:
            cursor.execute("INSERT INTO stats (user_id, total_questions, correct_count, wrong_count, mode) VALUES (%s, 1, %s, %s, %s)",
                           (uid, 1 if correct else 0, 0 if correct else 1, mode))

        # 更新进度
        score_add = 10 if correct else 0
        cursor.execute("SELECT CURDATE() as d")
        today = cursor.fetchone()['d']

        cursor.execute("SELECT * FROM user_progress WHERE user_id = %s", (uid,))
        prog = cursor.fetchone()
        if prog:
            new_streak = prog['study_streak']
            if prog['last_study_date'] != str(today):
                cursor.execute("SELECT DATE_SUB(CURDATE(), INTERVAL 1 DAY) as d")
                yesterday = cursor.fetchone()['d']
                if prog['last_study_date'] == str(yesterday):
                    new_streak = prog['study_streak'] + 1
                else:
                    new_streak = 1
            cursor.execute("""
                UPDATE user_progress SET
                    score = score + %s,
                    total_practice_count = total_practice_count + 1,
                    study_streak = %s,
                    last_study_date = %s
                WHERE user_id = %s
            """, (score_add, new_streak, str(today), uid))

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
    with db.cursor() as cursor:
        cursor.execute("SELECT max_combo FROM user_progress WHERE user_id = %s", (user['id'],))
        prog = cursor.fetchone()
        if prog and combo > prog['max_combo']:
            cursor.execute("UPDATE user_progress SET max_combo = %s WHERE user_id = %s", (combo, user['id']))
    db.commit()
    return jsonify({'success': True})

# ---- 统计 ----
@app.route('/api/stats', methods=['GET'])
def get_stats():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    uid = user['id']
    ws = get_user_word_set(user)
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) as cnt FROM words WHERE word_set = %s", (ws,))
        total = cursor.fetchone()['cnt']

        # 错题统计（限定当前单词集）
        cursor.execute("""
            SELECT w.id, w.word, w.chinese, w.phonetic, w.lesson, COUNT(e.id) as error_count
            FROM words w
            JOIN error_log e ON w.id = e.word_id
            WHERE e.user_id = %s AND w.word_set = %s
            GROUP BY w.id
            ORDER BY error_count DESC
        """, (uid, ws))
        error_words = cursor.fetchall()

        cursor.execute("SELECT * FROM user_progress WHERE user_id = %s", (uid,))
        progress = cursor.fetchone()

        cursor.execute("""
            SELECT mode, total_questions, correct_count, wrong_count, created_at
            FROM stats WHERE user_id = %s
            ORDER BY created_at DESC LIMIT 20
        """, (uid,))
        recent = cursor.fetchall()

        cursor.execute("""
            SELECT mode, SUM(total_questions) as total_q,
                   SUM(correct_count) as total_c, SUM(wrong_count) as total_w
            FROM stats WHERE user_id = %s
            GROUP BY mode
        """, (uid,))
        mode_stats = cursor.fetchall()

        # 每课掌握度
        cursor.execute("""
            SELECT w.lesson, COUNT(DISTINCT e.word_id) as err_word_count
            FROM error_log e JOIN words w ON e.word_id = w.id
            WHERE e.user_id = %s AND w.word_set = %s
            GROUP BY w.lesson
        """, (uid, ws))
        lesson_mastery = cursor.fetchall()

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
    ws = get_user_word_set(user)
    try:
        db = get_db()
        mode_filter = request.args.get('mode', '')

        with db.cursor() as cursor:
            if mode_filter:
                cursor.execute("""
                    SELECT w.id, w.word, w.chinese, w.phonetic, w.lesson, COUNT(e.id) as error_count,
                           e.error_type,
                           MIN(e.created_at) as first_error, MAX(e.created_at) as last_error
                    FROM words w
                    JOIN error_log e ON w.id = e.word_id
                    WHERE e.user_id = %s AND e.error_type = %s AND w.word_set = %s
                    GROUP BY w.id
                    ORDER BY error_count DESC
                """, (user['id'], mode_filter, ws))
            else:
                cursor.execute("""
                    SELECT w.id, w.word, w.chinese, w.phonetic, w.lesson, COUNT(e.id) as error_count,
                           e.error_type,
                           MIN(e.created_at) as first_error, MAX(e.created_at) as last_error
                    FROM words w
                    JOIN error_log e ON w.id = e.word_id
                    WHERE e.user_id = %s AND w.word_set = %s
                    GROUP BY w.id, e.error_type
                    ORDER BY error_count DESC
                """, (user['id'], ws))
            words = cursor.fetchall()

            cursor.execute("""
                SELECT error_type as mode, COUNT(*) as error_count, COUNT(DISTINCT word_id) as word_count
                FROM error_log
                WHERE user_id = %s
                GROUP BY error_type
            """, (user['id'],))
            mode_stats = cursor.fetchall()

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
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM error_log WHERE user_id = %s AND word_id = %s", (user['id'], word_id))
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
    with db.cursor() as cursor:
        if mode:
            cursor.execute("DELETE FROM error_log WHERE user_id = %s AND error_type = %s", (user['id'], mode))
        else:
            cursor.execute("DELETE FROM error_log WHERE user_id = %s", (user['id'],))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/reset_progress', methods=['POST'])
def reset_progress():
    user = login_required()
    if not user:
        return jsonify({'error': '请先登录'}), 401
    data = request.json or {}
    admin_pass = data.get('admin_pass', '')
    if admin_pass != 'cz':
        return jsonify({'error': '管理员密码错误'}), 403
    uid = user['id']
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM stats WHERE user_id = %s", (uid,))
        cursor.execute("DELETE FROM error_log WHERE user_id = %s", (uid,))
        cursor.execute("DELETE FROM mastered_words WHERE user_id = %s", (uid,))
        cursor.execute("UPDATE user_progress SET score=0, max_combo=0, study_streak=0, total_practice_count=0, last_study_date='' WHERE user_id = %s", (uid,))
    db.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    # 检查MySQL连接
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        conn.close()
    except Exception as e:
        print(f'[ERROR] MySQL连接失败，请先运行: python init_db.py')
        print(f'  错误详情: {e}')
        exit(1)
    app.run(debug=True, host='0.0.0.0', port=5001)
