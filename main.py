import flask
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SearchField, EmailField
from wtforms.validators import DataRequired 
import sqlite3
from datetime import datetime
import os

app = Flask(__name__, static_folder='static', template_folder='templates')


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
                created_at TIMESHTAMP DEFAULT CURRENT_TIMESHTAMP                 
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
    return(render_template('login.html'))

@app.route('/registration')
def registerpage():
    return(render_template('register.html'))

@app.route('/lobby')
def lobbypage():
    return(render_template('lobby.html'))



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
    app.run(host='0.0.0.0', port=5500, debug=True)