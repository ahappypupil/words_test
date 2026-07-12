"""一键初始化数据库：建表 + 导入单词数据"""
import json
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_FILE = 'nce_words.db'
WORDS_FILE = 'words.json'


def init_database():
    """删除旧库，重新建表并导入数据"""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f'[INFO] 已删除旧数据库 {DB_FILE}')

    if not os.path.exists(WORDS_FILE):
        print(f'[ERROR] 未找到 {WORDS_FILE}')
        return

    with open(WORDS_FILE, 'r', encoding='utf-8') as f:
        words = json.load(f)
    print(f'[INFO] 从 {WORDS_FILE} 读取到 {len(words)} 个单词')

    db = sqlite3.connect(DB_FILE)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')

    # ---- 用户表 ----
    db.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # ---- 单词表 ----
    db.execute('''CREATE TABLE words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        chinese TEXT NOT NULL,
        phonetic TEXT DEFAULT '',
        lesson INTEGER DEFAULT 1
    )''')

    # ---- 错误记录表 ----
    db.execute('''CREATE TABLE error_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        word_id INTEGER NOT NULL,
        error_type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (word_id) REFERENCES words(id)
    )''')

    # ---- 练习统计表 ----
    db.execute('''CREATE TABLE stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total_questions INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        wrong_count INTEGER DEFAULT 0,
        mode TEXT DEFAULT '',
        lesson TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ---- 用户进度表 ----
    db.execute('''CREATE TABLE user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        score INTEGER DEFAULT 0,
        max_combo INTEGER DEFAULT 0,
        study_streak INTEGER DEFAULT 0,
        last_study_date TEXT DEFAULT '',
        total_practice_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ---- 导入单词 ----
    for w in words:
        db.execute(
            'INSERT INTO words (word, chinese, phonetic, lesson) VALUES (?, ?, ?, ?)',
            (w['word'], w['chinese'], w.get('phonetic', ''), w.get('lesson', 1))
        )

    db.commit()

    # ---- 汇总 ----
    word_count = db.execute('SELECT COUNT(*) as cnt FROM words').fetchone()[0]
    lesson_count = db.execute(
        'SELECT COUNT(DISTINCT lesson) as cnt FROM words'
    ).fetchone()[0]

    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    print(f'\n[DONE] 建表完成，{word_count} 个单词, {lesson_count} 个课时')
    print('\n[INFO] 表结构:')
    for t in tables:
        cnt = db.execute(f'SELECT COUNT(*) as cnt FROM {t[0]}').fetchone()[0]
        cols = [c[1] for c in db.execute(f'PRAGMA table_info({t[0]})').fetchall()]
        print(f'  {t[0]:<16} ({cnt:>4} 行) 列: {", ".join(cols)}')

    db.close()
    print('\n[OK] 初始化完成！可以启动 app.py 了')


if __name__ == '__main__':
    init_database()
