import flask
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SearchField, EmailField
from wtforms.validators import DataRequired 
import sqlite3
from datetime import datetime, timedelta
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__, static_folder='static', template_folder='templates')

app.secret_key = 'a3f4d6e8c91b207f5e8a946a835a8d1f2b7c4e5d60a93f184b2e6d7c901a2b3f'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)    
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)      
app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'loginpage'


class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = getdb()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['email'])
    return None


def getdb():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def initdb():
    if not os.path.exists('database.db'):
        conn = getdb()
        conn.execute('''
            CREATE TABLE users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()


initdb()


@app.route('/')
def mainpage():
    return(render_template('main.html'))

@app.route('/login')
def loginpage():
    if current_user.is_authenticated:
        return redirect(url_for('lobbypage'))

    return(render_template('login.html'))

@app.route('/registration')
def registerpage():
    if current_user.is_authenticated:
        return redirect(url_for('lobbypage'))
    return render_template('register.html')

@app.route('/lobby')
@login_required
def lobbypage():
    return render_template('lobby.html', username=current_user.username)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('mainpage'))



@app.route('/submitregister', methods=['POST'])
def getuser():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('user-email', '').strip()
        password = request.form.get('user-password', '').strip()
        
        if not username or not email or not password:
            return "Пожалуйста, корректно заполните все поля", 400
        
        conn = getdb()
        try:
            existing_user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
            if existing_user:
                conn.close()
                return "Такой пользователь уже существует", 400
            
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, password))
            conn.commit()

            new_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            user_obj = User(new_user['id'], new_user['username'], new_user['email'])
            login_user(user_obj, remember=True, duration=timedelta(days=7))

        except sqlite3.Error as e:
            return f"Произошла ошибка во время создания пользователя {e}", 500
        
        finally:
            conn.close()

        return redirect(url_for('lobbypage'))
    
    return "Method not allowed", 405


@app.route('/submitlogin', methods=['POST'])
def checklogin():
    if request.method == 'POST':
        email = request.form.get('user-email', '').strip()
        password = request.form.get('user-password', '').strip()
        
        if not email or not password:
            return "Пожалуйста, заполните все поля", 400
        
        conn = getdb()

        try:
            user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
            
            conn.close()

            if user:
                user_obj = User(user['id'], user['username'], user['email'])
                login_user(user_obj, remember=True, duration=timedelta(days=7))
                return(redirect(url_for('lobbypage')))
            
            else:
                return(render_template('login.html', error="Неверный email или пароль"))
            
        except sqlite3.Error as e:
            return f"Произошла ошибка во время входа в личный аккаунт {e}", 500
        
    return "Method not allowed", 405






@app.errorhandler(404)
def notfound(e):
    return(render_template('404.html')), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)