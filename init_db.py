"""一键初始化数据库：建表 + 导入单词数据 (MySQL版)

支持多个单词集（word_set）：扫描目录下所有 *.json 文件，
文件名（不含扩展名）即为单词集名称。
第一个找到的单词集为默认。
"""
import json
import os
import glob
import sys
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

# ===== MySQL 连接配置 =====
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'devuser',
    'password': 'Dev@2026',
    'charset': 'utf8mb4',
}

DB_NAME = 'words_test'


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

    # ---- 扫描所有单词集 JSON 文件 ----
    json_files = sorted(glob.glob('*.json'))
    # 排除 package.json 等
    json_files = [f for f in json_files if not f.startswith('package')]
    if not json_files:
        print('[ERROR] 未找到任何 *.json 单词集文件')
        return

    print(f'[INFO] 发现 {len(json_files)} 个单词集: {", ".join(json_files)}')

    # 先连接MySQL服务器（不指定数据库），创建数据库
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
    cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()
    conn.close()
    print(f'[INFO] 已重建数据库 {DB_NAME}')

    # 连接到新数据库
    db = get_mysql_connection(DB_NAME)
    cursor = db.cursor()

    # ---- 用户表 ----
    cursor.execute('''CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(64) NOT NULL,
        nickname VARCHAR(50) DEFAULT '',
        default_word_set VARCHAR(50) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ---- 单词表 ----
    cursor.execute('''CREATE TABLE words (
        id INT AUTO_INCREMENT PRIMARY KEY,
        word VARCHAR(100) NOT NULL,
        chinese VARCHAR(200) NOT NULL,
        phonetic VARCHAR(200) DEFAULT '',
        lesson INT DEFAULT 1,
        category VARCHAR(50) DEFAULT '',
        word_set VARCHAR(50) NOT NULL DEFAULT 'default'
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

    # ---- 已掌握单词表（按单词文本去重，跨单词集通用）----
    cursor.execute('''CREATE TABLE mastered_words (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        word VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_user_word (user_id, word),
        FOREIGN KEY (user_id) REFERENCES users(id)
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

    # ---- 导入单词集 ----
    default_word_set = ''
    total_words = 0
    for jf in json_files:
        word_set_name = os.path.splitext(jf)[0]  # 文件名（不含扩展名）
        if not default_word_set:
            default_word_set = word_set_name

        with open(jf, 'r', encoding='utf-8') as f:
            words = json.load(f)
        print(f'[INFO] 从 {jf} 读取到 {len(words)} 个单词 (单词集: {word_set_name})')

        for w in words:
            cursor.execute(
                'INSERT INTO words (word, chinese, phonetic, lesson, category, word_set) VALUES (%s, %s, %s, %s, %s, %s)',
                (w['word'], w['chinese'], w.get('phonetic', ''), w.get('lesson', 1), w.get('category', ''), word_set_name)
            )
        total_words += len(words)

    # ---- 创建默认用户 ----
    default_user = 'xby'
    default_nick = '小白杨'
    default_pass = hashlib.sha256('1234'.encode()).hexdigest()
    cursor.execute(
        'INSERT INTO users (username, password_hash, nickname, default_word_set) VALUES (%s, %s, %s, %s)',
        (default_user, default_pass, default_nick, default_word_set)
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
        'INSERT INTO users (username, password_hash, nickname, default_word_set) VALUES (%s, %s, %s, %s)',
        (test_user, test_pass, test_nick, default_word_set)
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
    cursor.execute('SELECT word_set, COUNT(*) FROM words GROUP BY word_set')
    set_stats = cursor.fetchall()

    cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{DB_NAME}' ORDER BY table_name")
    tables = cursor.fetchall()

    print(f'\n[DONE] 建表完成，共 {word_count} 个单词, {lesson_count} 个课时')
    for s in set_stats:
        print(f'  单词集 {s[0]}: {s[1]} 个单词')
    print(f'  默认单词集: {default_word_set}')

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
