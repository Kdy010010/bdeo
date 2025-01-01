import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash

app = Flask(__name__)
app.secret_key = 'super_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

DB_NAME = 'bdeo.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                likes INTEGER DEFAULT 0
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                username TEXT,
                comment_text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(id)
            )
        ''')
        conn.commit()

@app.route('/')
def index():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('SELECT id, filename, likes FROM videos ORDER BY id DESC')
        videos = cur.fetchall()
    return render_template('index.html', videos=videos)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            filename = file.filename
            if not filename:
                flash('파일을 선택해주세요.')
                return redirect(url_for('upload_file'))

            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)

            with sqlite3.connect(DB_NAME) as conn:
                cur = conn.cursor()
                cur.execute('INSERT INTO videos (filename, likes) VALUES (?, ?)', (filename, 0))
                conn.commit()

            flash('동영상 업로드 완료!')
            return redirect(url_for('index'))
        else:
            flash('업로드할 파일이 없습니다.')
            return redirect(url_for('upload_file'))

    return render_template('upload.html')

@app.route('/watch/<int:video_id>')
def watch_video(video_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('SELECT id, filename, likes FROM videos WHERE id = ?', (video_id,))
        video = cur.fetchone()
        if not video:
            flash('존재하지 않는 동영상입니다.')
            return redirect(url_for('index'))

        cur.execute('''
            SELECT username, comment_text, created_at
            FROM comments
            WHERE video_id = ?
            ORDER BY id DESC
        ''', (video_id,))
        comments = cur.fetchall()

    return render_template('watch.html', video=video, comments=comments)

@app.route('/like/<int:video_id>')
def like_video(video_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('UPDATE videos SET likes = likes + 1 WHERE id = ?', (video_id,))
        conn.commit()
    return redirect(url_for('watch_video', video_id=video_id))

@app.route('/comment/<int:video_id>', methods=['POST'])
def comment_video(video_id):
    username = request.form.get('username')
    comment_text = request.form.get('comment_text')
    if not username:
        username = '익명'

    if comment_text:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO comments (video_id, username, comment_text) VALUES (?, ?, ?)',
                        (video_id, username, comment_text))
            conn.commit()

    return redirect(url_for('watch_video', video_id=video_id))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -----------------------------
# 검색 라우트
# -----------------------------
@app.route('/search', methods=['GET'])
def search_videos():
    """파일명에 검색어가 포함된 동영상 목록을 보여줍니다."""
    query = request.args.get('q', '')  # GET 파라미터 q
    results = []
    if query:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            # filename LIKE '%검색어%'
            like_query = f'%{query}%'
            cur.execute('''
                SELECT id, filename, likes 
                FROM videos
                WHERE filename LIKE ?
                ORDER BY id DESC
            ''', (like_query,))
            results = cur.fetchall()
    return render_template('search_results.html', query=query, results=results)

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=2000, debug=True)
