import flask
from flask import Flask, render_template, request, redirect, url_for, jsonify
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            )
        ''')
        conn.execute('''
            CREATE TABLE games(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                duration TEXT,
                start_time DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''') 
        conn.commit()
        conn.close()

initdb()


def is_admin():
    if not current_user.is_authenticated:
        return False
    conn = getdb()
    user_data = conn.execute('SELECT is_admin FROM users WHERE id = ?', (current_user.id,)).fetchone()
    conn.close()
    return user_data and user_data['is_admin']









@app.route('/')
def mainpage():
    return render_template('main.html')

@app.route('/login')
def loginpage():
    if current_user.is_authenticated:
        return redirect(url_for('lobbypage'))
    return render_template('login.html')

@app.route('/registration')
def registerpage():
    if current_user.is_authenticated:
        return redirect(url_for('lobbypage'))
    return render_template('register.html')

@app.route('/lobby')
@login_required
def lobbypage():

    conn = getdb()
    games = conn.execute('SELECT * FROM games ORDER BY start_time DESC, id DESC').fetchall()
    conn.close()

    is_admin_user = is_admin()
    return render_template('lobby.html', username=current_user.username, is_admin=is_admin_user, games=games)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('mainpage'))


@app.route('/admin/')
@login_required
def admin_dashboard():
    if not is_admin():
        return "Доступ запрещен", 403
    
    conn = getdb()
    stats = conn.execute('''
        SELECT 
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM users WHERE is_admin = 1) as admin_users,
            (SELECT COUNT(*) FROM games) as total_games
    ''').fetchone()
    conn.close()
    
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/users')
@login_required
def admin_users():
    if not is_admin():
        return "Доступ запрещен", 403
    
    conn = getdb()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/make_admin/<int:user_id>')
@login_required
def admin_make_admin(user_id):
    if not is_admin():
        return "Доступ запрещен", 403
    
    conn = getdb()
    try:
        conn.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))
    except sqlite3.Error as e:
        conn.close()
        return f"Ошибка при назначении админа: {e}", 500

@app.route('/admin/users/remove_admin/<int:user_id>')
@login_required
def admin_remove_admin(user_id):
    if not is_admin():
        return "Доступ запрещен", 403
    
    if user_id == current_user.id:
        return "Нельзя снять админку с самого себя", 400
    
    conn = getdb()
    try:
        conn.execute('UPDATE users SET is_admin = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))
    except sqlite3.Error as e:
        conn.close()
        return f"Ошибка при снятии админки: {e}", 500

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if not is_admin():
        return "Доступ запрещен", 403
    
    if user_id == current_user.id:
        return "Нельзя удалить самого себя", 400
    
    conn = getdb()
    try:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))
    except sqlite3.Error as e:
        conn.close()
        return f"Ошибка при удалении пользователя: {e}", 500


@app.route('/admin/games')
@login_required
def admin_games():
    if not is_admin():
        return "Доступ запрещен", 403
    
    conn = getdb()
    games = conn.execute('SELECT * FROM games ORDER BY start_time DESC, id DESC').fetchall()
    conn.close()
    
    return render_template('admin_games.html', games=games)

@app.route('/game.html')
@login_required
def game_page():
    return render_template('game.html')









@app.route('/api/game/<int:game_id>', methods=['GET'])
def api_get_game(game_id):
    conn = getdb()
    game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    conn.close()

    if not game:
        return jsonify({"error": "Игра не найдена"}), 404

    fake_game = {
        "id": game["id"],
        "name": game["name"],
        "duration": game["duration"] or "10 минут",
        "start_time": game["start_time"] or str(datetime.now()), 
        "players": 1,
        "maxPlayers": 8,
        "description": "Тестовая игра: подключение API",
        "playersList": ["Игрок1"]
    }

    return jsonify(fake_game)

@app.route('/admin/games/add', methods=['GET', 'POST'])
@login_required
def admin_add_game():
    if not is_admin():
        return "Доступ запрещен", 403
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration', '').strip()
        start_time = request.form.get('start_time', '').strip()
        
        if not name:
            return "Название игры обязательно", 400
        
        if start_time:
            try:
                start_time_dt = datetime.fromisoformat(start_time.replace('T', ' '))
                start_time = start_time_dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                return "Неверный формат времени", 400
        
        conn = getdb()
        try:
            conn.execute('INSERT INTO games (name, duration, start_time) VALUES (?, ?, ?)', 
                       (name, duration, start_time))
            conn.commit()
            return redirect(url_for('admin_games'))
        except sqlite3.Error as e:
            return f"Ошибка при добавлении игры: {e}", 500
        finally:
            conn.close()
    
    return render_template('admin_add_game.html')

@app.route('/admin/games/edit/<int:game_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_game(game_id):
    if not is_admin():
        return "Доступ запрещен", 403
    
    conn = getdb()
    game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    
    if not game:
        conn.close()
        return "Игра не найдена", 404
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration', '').strip()
        start_time = request.form.get('start_time', '').strip()
        
        if not name:
            conn.close()
            return "Название игры обязательно", 400
        
        if start_time:
            try:
                start_time_dt = datetime.fromisoformat(start_time.replace('T', ' '))
                start_time = start_time_dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                conn.close()
                return "Неверный формат времени", 400
        
        try:
            conn.execute('UPDATE games SET name = ?, duration = ?, start_time = ? WHERE id = ?', 
                       (name, duration, start_time, game_id))
            conn.commit()
            conn.close()
            return redirect(url_for('admin_games'))
        except sqlite3.Error as e:
            conn.close()
            return f"Ошибка при обновлении игры: {e}", 500
    
    game_dict = dict(game)
    if game_dict['start_time']:
        try:
            dt = datetime.fromisoformat(game_dict['start_time'])
            game_dict['start_time'] = dt.strftime('%Y-%m-%dT%H:%M')
        except ValueError:
            game_dict['start_time'] = ''
    
    conn.close()
    return render_template('admin_edit_game.html', game=game_dict)

@app.route('/admin/games/delete/<int:game_id>')
@login_required
def admin_delete_game(game_id):
    if not is_admin():
        return "Доступ запрещен", 403
    
    conn = getdb()
    try:
        conn.execute('DELETE FROM games WHERE id = ?', (game_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_games'))
    except sqlite3.Error as e:
        conn.close()
        return f"Ошибка при удалении игры: {e}", 500

    
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
            
            user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
            is_admin = (user_count == 0)
            
            conn.execute('INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)', 
                        (username, email, password, is_admin))
            conn.commit()

            new_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            user_obj = User(new_user['id'], new_user['username'], new_user['email'])
            login_user(user_obj, remember=True)

            print(f"Пользователь {username} создан. Админ: {is_admin}")

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
                login_user(user_obj, remember=True)
                return redirect(url_for('lobbypage'))
            else:
                return render_template('login.html', error="Неверный email или пароль")
            
        except sqlite3.Error as e:
            return f"Произошла ошибка во время входа в личный аккаунт {e}", 500
        
    return "Method not allowed", 405

@app.errorhandler(404)
def notfound(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)