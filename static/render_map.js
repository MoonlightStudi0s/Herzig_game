// const MapContent = document.getElementById('render-content');
// MapContent.innerHTML = `
//     <div id="kvadratik-l1"></div>
//     <div id="kvadratik-l2"></div>
//     <div id="vline1"></div>
//     <div id="vline2"></div>
//     <div id="hline1"></div>
//     <div id="hline2"></div>
// `;


const canvas = document.getElementById('render-content');
const ctx = canvas.getContext('2d');

// Фиксированные размеры canvas
const CANVAS_WIDTH = 1920;
const CANVAS_HEIGHT = 1080;

// Настройки анимации
const ANIMATION_CONFIG = {
    startOffset: 800,    // Начальное смещение (конструкция полностью внизу)
    endOffset: 100,      // Конечное смещение (финальная позиция)
    duration: 2000,      // Длительность анимации в миллисекундах
    easing: 'easeOutCubic' // Функция плавности
};

let animationStartTime = null;
let currentOffset = ANIMATION_CONFIG.startOffset;

// Устанавливаем фиксированный размер canvas
function setupCanvas() {
    canvas.width = CANVAS_WIDTH;
    canvas.height = CANVAS_HEIGHT;
    startAnimation();
}

// Функции плавности (easing)
const easingFunctions = {
    linear: (t) => t,
    easeOutCubic: (t) => 1 - Math.pow(1 - t, 3),
    easeOutQuad: (t) => 1 - (1 - t) * (1 - t),
    easeOutExpo: (t) => t === 1 ? 1 : 1 - Math.pow(2, -10 * t)
};

// Запуск анимации
function startAnimation() {
    animationStartTime = Date.now();
    currentOffset = ANIMATION_CONFIG.startOffset;
    animate();
}

// Основной цикл анимации
function animate() {
    const currentTime = Date.now();
    const elapsed = currentTime - animationStartTime;
    const progress = Math.min(elapsed / ANIMATION_CONFIG.duration, 1);
    
    // Применяем функцию плавности
    const easeProgress = easingFunctions[ANIMATION_CONFIG.easing](progress);
    
    // Вычисляем текущее смещение
    currentOffset = ANIMATION_CONFIG.startOffset + 
                   (ANIMATION_CONFIG.endOffset - ANIMATION_CONFIG.startOffset) * easeProgress;
    
    // Отрисовываем кадр
    draw();
    
    // Продолжаем анимацию, если не достигли конца
    if (progress < 1) {
        requestAnimationFrame(animate);
    }
}

// Функция отрисовки с текущим смещением
function draw() {
    // Очищаем canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Рисуем квадрат в правом нижнем углу
    ctx.fillStyle = 'rgb(243,233,32)';
    roundRect(ctx, CANVAS_WIDTH - 200, CANVAS_HEIGHT - 200 + currentOffset, 100, 100, 16);
    
    // Рисуем квадрат в левом верхнем углу
    roundRect(ctx, 1109, 400 + currentOffset, 100, 100, 16);
    
    // Рисуем вертикальные линии
    ctx.strokeStyle = 'whitesmoke';
    ctx.lineWidth = 3;
    
    // Первая вертикальная линия (правая сторона)
    ctx.beginPath();
    ctx.moveTo(CANVAS_WIDTH - 130, 430 + currentOffset);
    ctx.lineTo(CANVAS_WIDTH - 130, 880 + currentOffset);
    ctx.stroke();
    
    // Вторая вертикальная линия (правая сторона)
    ctx.beginPath();
    ctx.moveTo(CANVAS_WIDTH - 162.5, 470 + currentOffset);
    ctx.lineTo(CANVAS_WIDTH - 162.5, 880 + currentOffset);
    ctx.stroke();
    
    // Горизонтальные линии
    // Первая горизонтальная линия
    ctx.beginPath();
    ctx.moveTo(1208, 430 + currentOffset);
    ctx.lineTo(1208 + 583.5, 430 + currentOffset);
    ctx.stroke();
    
    // Вторая горизонтальная линия
    ctx.beginPath();
    ctx.moveTo(1209, 470 + currentOffset);
    ctx.lineTo(1209 + 550, 470 + currentOffset);
    ctx.stroke();
}

// Функция для рисования прямоугольника с закругленными углами
function roundRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
}

// Центрируем canvas на странице
function centerCanvas() {
    const container = canvas.parentElement;
    const scaleX = window.innerWidth / CANVAS_WIDTH;
    const scaleY = window.innerHeight / CANVAS_HEIGHT;
    const scale = Math.min(scaleX, scaleY);
    
    canvas.style.width = `${CANVAS_WIDTH * scale}px`;
    canvas.style.height = `${CANVAS_HEIGHT * scale}px`;
    canvas.style.margin = 'auto';
    canvas.style.position = 'absolute';
    canvas.style.left = '50%';
    canvas.style.top = '50%';
    canvas.style.transform = 'translate(-50%, -50%)';
}

// Перезапуск анимации по клику (опционально)
canvas.addEventListener('click', startAnimation);

// Инициализация
setupCanvas();
centerCanvas();
window.addEventListener('resize', centerCanvas);