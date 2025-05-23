from flask import Flask, request, render_template, redirect
import sqlite3
import os

app = Flask(__name__)
DATABASE = 'users.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)")
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute(f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')")
            conn.commit()
            msg = "User registered!"
    return render_template('register.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
            print(f"Executing: {query}")
            c.execute(query)
            user = c.fetchone()
            if user:
                msg = f"Welcome, {user[1]}!"
            else:
                msg = "Invalid credentials."
    return render_template('login.html', msg=msg)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=3000, debug=True)
