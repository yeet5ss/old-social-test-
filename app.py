from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DATABASE = 'oldsocial.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS friend_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, status TEXT DEFAULT 'pending')")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS heats (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, post_id INTEGER, UNIQUE(user_id, post_id))")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()

@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session:
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
            g.user = c.fetchone()

@app.route('/')
def index():
    if not g.user:
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT posts.id, users.username, posts.content, posts.timestamp,
                (SELECT COUNT(*) FROM heats WHERE post_id = posts.id) as heat_count
            FROM posts
            JOIN users ON users.id = posts.user_id
            ORDER BY posts.timestamp DESC
        """)
        posts = c.fetchall()
    return render_template('index.html', user=g.user, posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash("Username and password required.")
        else:
            hashed_pw = generate_password_hash(password)
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
                    conn.commit()
                    return redirect(url_for('login'))
                except sqlite3.IntegrityError:
                    flash("Username already exists.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                return redirect(url_for('index'))
            else:
                flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/post', methods=['POST'])
def post():
    if not g.user:
        return redirect(url_for('login'))
    content = request.form['content'].strip()
    if content:
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO posts (user_id, content) VALUES (?, ?)", (g.user[0], content))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/heat/<int:post_id>')
def heat(post_id):
    if not g.user:
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO heats (user_id, post_id) VALUES (?, ?)", (g.user[0], post_id))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
    return redirect(url_for('index'))

@app.route('/friends')
def friends():
    if not g.user:
        return redirect(url_for('login'))
    user_id = g.user[0]
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT users.id, users.username FROM friend_requests JOIN users ON users.id = friend_requests.sender_id WHERE friend_requests.receiver_id = ? AND friend_requests.status = 'pending'", (user_id,))
        requests = c.fetchall()
        c.execute("""
            SELECT users.id, users.username FROM friend_requests
            JOIN users ON users.id = friend_requests.receiver_id
            WHERE friend_requests.sender_id = ? AND friend_requests.status = 'accepted'
            UNION
            SELECT users.id, users.username FROM friend_requests
            JOIN users ON users.id = friend_requests.sender_id
            WHERE friend_requests.receiver_id = ? AND friend_requests.status = 'accepted'
        """, (user_id, user_id))
        friends = c.fetchall()
    return render_template('friends.html', requests=requests, friends=friends)

@app.route('/add_friend/<int:user_id>')
def add_friend(user_id):
    if not g.user:
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM friend_requests WHERE sender_id = ? AND receiver_id = ?", (g.user[0], user_id))
        if not c.fetchone():
            c.execute("INSERT INTO friend_requests (sender_id, receiver_id) VALUES (?, ?)", (g.user[0], user_id))
            conn.commit()
    return redirect(url_for('friends'))

@app.route('/accept_friend/<int:user_id>')
def accept_friend(user_id):
    if not g.user:
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("UPDATE friend_requests SET status = 'accepted' WHERE sender_id = ? AND receiver_id = ?", (user_id, g.user[0]))
        conn.commit()
    return redirect(url_for('friends'))

@app.route('/message/<int:friend_id>', methods=['GET', 'POST'])
def message(friend_id):
    if not g.user:
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            msg = request.form['message'].strip()
            if msg:
                c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)", (g.user[0], friend_id, msg))
                conn.commit()
        c.execute("SELECT users.username, messages.message, messages.timestamp FROM messages JOIN users ON users.id = messages.sender_id WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?) ORDER BY messages.timestamp ASC", (g.user[0], friend_id, friend_id, g.user[0]))
        chat = c.fetchall()
    return render_template('message.html', chat=chat, friend_id=friend_id)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=3000, debug=True)
