"""一键初始化数据库：建表 + 导入单词数据 (MySQL版)"""
import json
import os
import sys
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

WORDS_FILE = 'words.json'

# ===== MySQL 连接配置 =====
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'devuser',
    'password': 'Dev@2026',
    'database': 'ncf1_words',
    'charset': 'utf8mb4',
}


def get_mysql_connection(db_name=None):
    """获取MySQL连接，db_name为None时不指定数据库"""
    import pymysql
    config = MYSQL_CONFIG.copy()
    if db_name:
        config['database'] = db_name
    else:
        config.pop('database', None)
    return pymysql.connect(**config)


def init_database():
    """删除旧库，重新建表并导入数据"""

    if not os.path.exists(WORDS_FILE):
        print(f'[ERROR] 未找到 {WORDS_FILE}')
        return

    with open(WORDS_FILE, 'r', encoding='utf-8') as f:
        words = json.load(f)
    print(f'[INFO] 从 {WORDS_FILE} 读取到 {len(words)} 个单词')

    # 先连接MySQL服务器（不指定数据库），创建数据库
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("DROP DATABASE IF EXISTS ncf1_words")
    cursor.execute("CREATE DATABASE ncf1_words CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()
    conn.close()
    print('[INFO] 已重建数据库 ncf1_words')

    # 连接到新数据库
    db = get_mysql_connection('ncf1_words')
    cursor = db.cursor()

    # ---- 用户表 ----
    cursor.execute('''CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(64) NOT NULL,
        nickname VARCHAR(50) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ---- 单词表 ----
    cursor.execute('''CREATE TABLE words (
        id INT AUTO_INCREMENT PRIMARY KEY,
        word VARCHAR(100) NOT NULL,
        chinese VARCHAR(200) NOT NULL,
        phonetic VARCHAR(200) DEFAULT '',
        lesson INT DEFAULT 1,
        category VARCHAR(50) DEFAULT ''
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ---- 错误记录表 ----
    cursor.execute('''CREATE TABLE error_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        word_id INT NOT NULL,
        error_type VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (word_id) REFERENCES words(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ---- 已掌握单词表（某单词某题型答对后记录，不再出现）----
    cursor.execute('''CREATE TABLE mastered_words (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        word_id INT NOT NULL,
        mode VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_user_word_mode (user_id, word_id, mode),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (word_id) REFERENCES words(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ---- 练习统计表 ----
    cursor.execute('''CREATE TABLE stats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        total_questions INT DEFAULT 0,
        correct_count INT DEFAULT 0,
        wrong_count INT DEFAULT 0,
        mode VARCHAR(20) DEFAULT '',
        lesson VARCHAR(20) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ---- 用户进度表 ----
    cursor.execute('''CREATE TABLE user_progress (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT UNIQUE NOT NULL,
        score INT DEFAULT 0,
        max_combo INT DEFAULT 0,
        study_streak INT DEFAULT 0,
        last_study_date VARCHAR(20) DEFAULT '',
        total_practice_count INT DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ---- 导入单词 ----
    for w in words:
        cursor.execute(
            'INSERT INTO words (word, chinese, phonetic, lesson, category) VALUES (%s, %s, %s, %s, %s)',
            (w['word'], w['chinese'], w.get('phonetic', ''), w.get('lesson', 1), w.get('category', ''))
        )

    # ---- 创建默认用户 ----
    default_user = 'xby'
    default_nick = '小白杨'
    default_pass = hashlib.sha256('1234'.encode()).hexdigest()
    cursor.execute(
        'INSERT INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)',
        (default_user, default_pass, default_nick)
    )
    cursor.execute(
        'INSERT INTO user_progress (user_id, score) VALUES (LAST_INSERT_ID(), 0)'
    )
    print(f'[INFO] 已创建默认用户: {default_user} (昵称: {default_nick})')

    # ---- 创建测试用户 ----
    test_user = 'test'
    test_nick = '测试'
    test_pass = hashlib.sha256('1234'.encode()).hexdigest()
    cursor.execute(
        'INSERT INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)',
        (test_user, test_pass, test_nick)
    )
    cursor.execute(
        'INSERT INTO user_progress (user_id, score) VALUES (LAST_INSERT_ID(), 0)'
    )
    print(f'[INFO] 已创建测试用户: {test_user} (昵称: {test_nick})')

    db.commit()

    # ---- 汇总 ----
    cursor.execute('SELECT COUNT(*) FROM words')
    word_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(DISTINCT lesson) FROM words')
    lesson_count = cursor.fetchone()[0]

    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='ncf1_words' ORDER BY table_name")
    tables = cursor.fetchall()

    print(f'\n[DONE] 建表完成，{word_count} 个单词, {lesson_count} 个课时')
    print('\n[INFO] 表结构:')
    for t in tables:
        tname = t[0]
        cursor.execute(f'SELECT COUNT(*) FROM `{tname}`')
        cnt = cursor.fetchone()[0]
        cursor.execute(f'DESCRIBE `{tname}`')
        cols = [c[0] for c in cursor.fetchall()]
        print(f'  {tname:<16} ({cnt:>4} 行) 列: {", ".join(cols)}')

    cursor.close()
    db.close()
    print('\n[OK] 初始化完成！可以启动 app.py 了')


if __name__ == '__main__':
    init_database()
