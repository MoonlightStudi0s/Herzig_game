class GameManager {
    constructor() {
        this.gameId = this.getGameIdFromURL();
        this.username = this.getUsername();
        this.init();
        this.socket = io();
        this.socket.emit('join_game', { game_id: this.gameId });

        this.socket.on('game_started', (data) => {
            if (data.game_id == this.gameId) {
                window.location.href = '/game';
            }
        });

    }

    // Получаем ID игры из URL
    getGameIdFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('id') || urlParams.get('gameId') || '1'; // По умолчанию игра 1
    }

    // Получаем имя пользователя (можно из localStorage или cookie)
    getUsername() {
        return localStorage.getItem('username') || 'Игрок';
    }

    async init() {
        // Устанавливаем имя пользователя в шапке
        document.getElementById('username').textContent = this.username;
        
        // Загружаем данные игры
        await this.loadGameData();
        // Присоединяем игрока к игре при входе
        await fetch(`/api/game/${this.gameId}/join`, { method: 'POST' });

        // Проверяем статус игры каждые 3 секунды
        setInterval(async () => {
            const gameData = await this.fetchGameData(this.gameId);

            // Обновляем список игроков
            this.updatePlayersList(gameData.playersList);

            // Если игра запущена — редирект
            if (gameData.status === 'in_progress' && !gameData.isAdmin) {
                window.location.href = '/game';
            }
        }, 3000);


    }

    async loadGameData() {
        try {
            // Здесь будет запрос к вашему API
            const gameData = await this.fetchGameData(this.gameId);
            this.renderGame(gameData);
        } catch (error) {
            this.showError('Ошибка загрузки игры: ' + error.message);
        }
    }

    async fetchGameData(gameId) {
        const response = await fetch(`/api/game/${gameId}`);
        if (!response.ok) throw new Error("Ошибка загрузки игры");
        return await response.json();
    }

    updatePlayersList(players) {
        const container = document.querySelector('.players-list');
        if (!container) return;
        
        container.innerHTML = `
            <h3>Участники (${players.length})</h3>
            ${players.map(player => `
                <div class="player-card">
                    <strong>${player}</strong>
                    ${player === this.username ? '<div>🌟 Вы</div>' : ''}
                </div>
            `).join('')}
        `;
    }


    renderGame(gameData) {
        const gameContent = document.getElementById('game-content');
        
        gameContent.innerHTML = `
            <div class="game-header">
                <h1 class="game-title">${gameData.name}</h1>

            </div>

            <div class="game-info">
                <div class="info-item">ID игры: #${gameData.id}</div>
                <div class="info-item">Тип: ${this.getTypeName(gameData.type)}</div>
                <div class="info-item">Длительность: ${gameData.duration}</div>
                <div class="info-item">Игроки: ${gameData.players}/${gameData.maxPlayers}</div>
                <div class="info-item">Статус: ${this.getStatusName(gameData.status)}</div>
            </div>

            <div class="game-area">
                <h3>Игровая зона</h3>
                ${this.renderGameArea(gameData)}
            </div>

            <div class="players-list">
                <h3>Участники (${gameData.playersList.length})</h3>
                ${gameData.playersList.map(player => `
                    <div class="player-card">
                        <strong>${player}</strong>
                        ${player === this.username ? '<div>🌟 Вы</div>' : ''}
                    </div>
                `).join('')}
            </div>

            <div class="game-controls">
                ${this.renderControls(gameData)}
            </div>
        `;
    }

    getTypeName(type) {
        const types = {
            'adventure': 'Приключение',
            'strategy': 'Стратегия',
            'racing': 'Гонки'
        };
        return types[type] || type;
    }

    getStatusName(status) {
        const statuses = {
            'waiting': '⏳ Ожидание',
            'in_progress': '🎮 В процессе',
            'finished': '✅ Завершена'
            };
        return statuses[status] || status;
    }

    renderGameArea(gameData) {
        switch (gameData.status) {
            case 'waiting':
                return `
                    <div style="text-align: center; padding: 40px; color: white;">
                        <h4>Ожидаем игроков...</h4>
                        <p>Присоединилось: ${gameData.players}/${gameData.maxPlayers}</p>
                        ${gameData.isAdmin ? `
                            <button class="control-button" onclick="gameManager.startGame()">
                                Начать игру
                            </button>
                        ` : `<p style="color:#aaa;">Ожидание администратора для старта игры</p>`}
                    </div>
                `;
            case 'in_progress':
                return `
                    <div style="text-align: center; padding: 40px; color: white;">
                        <h4>Игра в процессе!</h4>
                        <p>Действуйте быстро, время ограничено!</p>
                        <div id="game-timer">Осталось: ${gameData.duration}</div>
                    </div>
                `;
            case 'finished':
                return `
                    <div style="text-align: center; padding: 40px; color: white;">
                        <h4>Игра завершена!</h4>
                        <p>Победитель: ${gameData.playersList[0]}</p>
                        <button class="control-button" onclick="gameManager.playAgain()">
                            Играть снова
                        </button>
                    </div>
                `;
            default:
                return '<p>Неизвестный статус игры</p>';
        }
    }


    renderControls(gameData) {
        const controls = [];
        
        if (gameData.status === 'waiting') {
            controls.push('<button class="control-button" onclick="gameManager.leaveGame()">Покинуть игру</button>');
            controls.push('<button class="control-button" onclick="gameManager.inviteFriends()">Пригласить друзей</button>');
        } else if (gameData.status === 'in_progress') {
            controls.push('<button class="control-button" onclick="gameManager.makeMove()">Сделать ход</button>');
            controls.push('<button class="control-button" onclick="gameManager.surrender()">Сдаться</button>');
        } else {
            controls.push('<button class="control-button" onclick="gameManager.returnToLobby()">Вернуться в лобби</button>');
        }

        return controls.join('');
    }

    // Методы управления игрой
    startGame() {
        fetch(`/api/game/${this.gameId}/start`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Перенаправляем всех игроков на страницу игры
                    window.location.href = '/game';
                } else {
                    alert(data.error || 'Не удалось начать игру');
                }
            })
            .catch(() => alert('Ошибка при попытке начать игру'));
    }


    leaveGame() {
        if (confirm('Вы уверены, что хотите покинуть игру?')) {
            window.location.href = '/lobby';
        }
        
        this.socket.emit('leave_game', { game_id: this.gameId });
    }

    inviteFriends() {
        const link = window.location.href;
        navigator.clipboard.writeText(link).then(() => {
            alert('Ссылка на игру скопирована в буфер обмена!');
        });
    }

    makeMove() {
        alert('Ход сделан!');
        // Логика хода
    }

    surrender() {
        if (confirm('Вы уверены, что хотите сдаться?')) {
            alert('Вы сдались!');
        }
    }

    playAgain() {
        alert('Начинаем новую игру!');
        // Логика новой игры
    }

    returnToLobby() {
        window.location.href = '/lobby';
    }

    showError(message) {
        document.getElementById('game-content').innerHTML = `
            <div class="error-message">
                <h2>Ошибка</h2>
                <p>${message}</p>
                <button class="control-button" onclick="window.location.href='/lobby'">
                    Вернуться в лобби
                </button>
            </div>
        `;
    }
}

// Инициализация при загрузке страницы
let gameManager;
document.addEventListener('DOMContentLoaded', () => {
    gameManager = new GameManager();
});