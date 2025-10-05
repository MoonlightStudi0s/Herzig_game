import flask
from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, timedelta
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room



app = Flask(__name__, static_folder='static', template_folder='templates')

app.secret_key = 'a3f4d6e8c91b207f5e8a946a835a8d1f2b7c4e5d60a93f184b2e6d7c901a2b3f'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)    
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)      
app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True


socketio = SocketIO(app)


# ============================================================================
#                                         Настройки bash

from flask import Flask, request, jsonify, render_template
import subprocess, shlex, locale, os, sys, time


ALLOWED_PROGS = {"echo", "whoami", "pwd", "ipconfig", "dir", "type", "ls", "cat", "netstat"}
MAX_CMD_LEN = 1000
MAX_OUTPUT_CHARS = 20000
RUN_TIMEOUT = 6  # seconds

def decode_output(b: bytes) -> str:
    encs = []
    try:
        sys_enc = locale.getpreferredencoding(False)
    except Exception:
        sys_enc = None
    if sys_enc:
        encs.append(sys_enc)
    if os.name == "nt":
        encs.append("cp866")
    encs += ["utf-8", "cp1251", "latin1"]
    seen = []
    for e in encs:
        if e and e not in seen:
            seen.append(e)
    for enc in seen:
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("latin1", errors="replace")

def preexec_limits():
    if not HAVE_RESOURCE:
        return
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (2,2))
        resource.setrlimit(resource.RLIMIT_AS, (300_000_000, 300_000_000))
    except Exception:
        pass

# ============================================================================



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
    conn = sqlite3.connect('database.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration TEXT,
            start_time DATETIME,
            status TEXT DEFAULT 'waiting',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
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

@app.route('/game')
@login_required
def gamebash():
    return(render_template('main_game_bash.html'))









@app.route('/api/game/<int:game_id>', methods=['GET'])
@login_required
def api_get_game(game_id):
    conn = getdb()

    game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    if not game:
        conn.close()
        return jsonify({"error": "Игра не найдена"}), 404

    # Получаем игроков
    players = conn.execute('''
        SELECT u.username 
        FROM players p 
        JOIN users u ON p.user_id = u.id 
        WHERE p.game_id = ?
    ''', (game_id,)).fetchall()

    conn.close()

    players_list = [p['username'] for p in players]

    game_data = {
        "id": game["id"],
        "name": game["name"],
        "duration": game["duration"] or "10 минут",
        "start_time": game["start_time"] or str(datetime.now()),
        "players": len(players_list),
        "maxPlayers": 8,
        "description": "Игра с реальным API и таблицей игроков",
        "playersList": players_list,
        "type": "adventure",
        "status": game["status"],
        "isAdmin": is_admin()
    }

    return jsonify(game_data)



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


@app.route("/exec", methods=["POST"])
def exec_cmd():
    data = request.get_json() or {}
    cmd = (data.get("command") or "").strip()
    if not cmd:
        return jsonify({"output": "Введите команду", "cwd": os.getcwd()}), 400
    if len(cmd) > MAX_CMD_LEN:
        return jsonify({"output": "Команда слишком длинная.", "cwd": os.getcwd()}), 400

    # безопасный разбор аргументов
    try:
        parts = shlex.split(cmd, posix=(os.name != "nt"))
    except Exception:
        return jsonify({"output": "Ошибка парсинга команды", "cwd": os.getcwd()}), 400
    if not parts:
        return jsonify({"output": "", "cwd": os.getcwd()})

    prog = parts[0].lower()
    # специальная обработка встроенных команд, которые мы хотим реализовать в Python
    if prog == "cd":
        # cd without args -> show current
        if len(parts) == 1:
            return jsonify({"output": os.getcwd(), "cwd": os.getcwd()})
        target = parts[1]
        # попытка разрешить относительные и абсолютные пути
        try:
            # на Windows позволим пути с / и \
            new_path = target
            if not (os.path.isabs(new_path) or (os.name == "nt" and ":" in new_path)):
                new_path = os.path.join(os.getcwd(), new_path)
            new_path = os.path.abspath(new_path)
            if os.path.isdir(new_path):
                os.chdir(new_path)
                return jsonify({"output": "", "cwd": os.getcwd()})
            else:
                return jsonify({"output": "The system cannot find the path specified.", "cwd": os.getcwd()})
        except Exception as e:
            return jsonify({"output": str(e), "cwd": os.getcwd()})

    if prog == "mkdir":
        if len(parts) == 1:
            return jsonify({"output": "The syntax of the command is incorrect.", "cwd": os.getcwd()})
        target = parts[1]
        try:
            path = target
            if not os.path.isabs(path) and not (os.name == "nt" and ":" in path):
                path = os.path.join(os.getcwd(), path)
            os.makedirs(path, exist_ok=True)
            return jsonify({"output": "", "cwd": os.getcwd()})
        except Exception as e:
            return jsonify({"output": f"Ошибка: {e}", "cwd": os.getcwd()})

    # дальше: проверим по белому списку
    if prog not in ALLOWED_PROGS:
        return jsonify({"output": f"Команда '{prog}' запрещена.", "cwd": os.getcwd()})

    # Выполнение: Windows - через cmd /c (чтобы поддержать dir, ipconfig и т.п.)
    try:
        if os.name == "nt":
            # Используем cmd /c <original cmd string>
            run_cmd = ["cmd", "/c", cmd]
            completed = subprocess.run(
                run_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=RUN_TIMEOUT,
                shell=False
            )
        else:
            # Unix: запускаем безопасно как список
            kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "timeout": RUN_TIMEOUT, "shell": False}
            if HAVE_RESOURCE:
                kwargs["preexec_fn"] = preexec_limits
            completed = subprocess.run(parts, **kwargs)

        raw = completed.stdout + completed.stderr
        text = decode_output(raw)
        if len(text) > MAX_OUTPUT_CHARS:
            text = text[:MAX_OUTPUT_CHARS] + "\n\n[output truncated]"
    except subprocess.TimeoutExpired:
        text = "Timeout: команда превысила лимит времени."
    except FileNotFoundError:
        text = f"Команда '{prog}' не найдена на системе."
    except Exception as e:
        text = f"Ошибка выполнения: {e}"

    return jsonify({"output": text, "cwd": os.getcwd()})


@app.route('/api/game/<int:game_id>/start', methods=['POST'])
@login_required
def api_start_game(game_id):
    if not is_admin():
        return jsonify({"error": "Только администратор может начать игру"}), 403

    conn = getdb()
    game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    if not game:
        conn.close()
        return jsonify({"error": "Игра не найдена"}), 404

    try:
        # Меняем статус игры на in_progress и ставим время старта
        conn.execute('UPDATE games SET status = ?, start_time = ? WHERE id = ?', 
                     ("in_progress", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), game_id))
        conn.commit()
        conn.close()

        # Сообщаем всем игрокам через Socket.IO
        socketio.emit('game_started', {'game_id': game_id}, room=f'game_{game_id}')

        return jsonify({"success": True})
    except sqlite3.Error as e:
        conn.close()
        return jsonify({"error": f"Ошибка при старте игры: {e}"}), 500


    

@app.route('/api/game/<int:game_id>/join', methods=['POST'])
@login_required
def api_join_game(game_id):
    conn = getdb()
    user_id = current_user.id

    # Проверим, есть ли игра
    game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    if not game:
        conn.close()
        return jsonify({"error": "Игра не найдена"}), 404

    # Проверим, есть ли уже игрок
    existing = conn.execute('SELECT * FROM players WHERE game_id = ? AND user_id = ?', 
                            (game_id, user_id)).fetchone()
    if not existing:
        conn.execute('INSERT INTO players (game_id, user_id) VALUES (?, ?)', (game_id, user_id))
        conn.commit()

    conn.close()
    return jsonify({"success": True})




@socketio.on('join_game')
def handle_join_game(data):
    game_id = data.get('game_id')
    join_room(f'game_{game_id}')
    print(f"Пользователь подключился к комнате игры {game_id}")

@socketio.on('leave_game')
def handle_leave_game(data):
    game_id = data.get('game_id')
    leave_room(f'game_{game_id}')
    print(f"Пользователь покинул комнату игры {game_id}")



@app.errorhandler(404)
def notfound(e):
    return render_template('404.html'), 404




if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)