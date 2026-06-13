// Zombie Game Logic
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// Game state
let score = 0;
let zombieCount = 0;
let zombies = [];
let zombiesToSpawn = 3;
let gameRunning = true;
let spawnTimer = 0;
let maxZombies = 5; // Maximum zombies allowed on screen
let zombiesLeft = 0; // Zombies remaining to spawn in current batch
let animationId;

// Colors
const zombieColors = ['#ff6b6b', '#feca57', '#48dbfb', '#ff9ff6', '#1dd1a1'];
const bulletColors = ['#1e90ff', '#ff6b6b', '#48dbfb'];

class Zombie {
    constructor() {
        this.radius = 30 + Math.random() * 10;
        this.x = Math.random() * (canvas.width - 100) + 50;
        this.y = canvas.height + 20;
        this.speed = 0.5 + Math.random() * 1.5;
        this.color = zombieColors[Math.floor(Math.random() * zombieColors.length)];
        this.health = 1 + Math.floor(Math.random() * 3);
        this.movementTimer = 0;
        this.movementDirection = Math.random() > 0.5 ? 1 : -1;
    }

    update() {
        this.movementTimer++;
        if (this.movementTimer % 10 === 0) {
            this.movementDirection = Math.random() > 0.5 ? 1 : -1;
        }

        this.x += this.speed * this.movementDirection;

        // Bounce off walls
        if (this.x + this.radius > canvas.width || this.x - this.radius < 0) {
            this.movementDirection *= -1;
        }

        // Move up
        this.y -= this.speed * 1.2;

        // Check if zombie reached top
        if (this.y < -50) {
            this.health = 0;
            this.remove();
        }

        // Check collision with bullets
        for (let i = bullets.length - 1; i >= 0; i--) {
            const bullet = bullets[i];
            const dx = this.x - bullet.x;
            const dy = this.y - bullet.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < this.radius + bullet.radius) {
                this.health--;
                this.radius -= 5; // Slight shrink on hit
                bullet.health--;
                bullets.splice(i, 1);
                
                if (this.health <= 0) {
                    this.remove();
                    score += 10;
                    zombiesLeft++;
                    checkSpawnCondition();
                }
            }
        }

        // Check collision with other zombies
        for (let j = 0; j < zombies.length; j++) {
            if (i !== j) {
                const other = zombies[j];
                const dx = this.x - other.x;
                const dy = this.y - other.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < this.radius + other.radius) {
                    this.health -= 0.5;
                }
            }
        }
    }

    remove() {
        const index = zombies.indexOf(this);
        if (index > -1) {
            zombies.splice(index, 1);
        }
    }

    draw() {
        // Body
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.fill();
        ctx.strokeStyle = '#1a1a2e';
        ctx.stroke();

        // Eye
        ctx.beginPath();
        ctx.arc(this.x + this.radius * 0.4, this.y - this.radius * 0.3, this.radius * 0.2, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();

        // Mouth
        ctx.beginPath();
        ctx.arc(this.x, this.y + this.radius * 0.2, this.radius * 0.2, 0, Math.PI, false);
        ctx.strokeStyle = '#1a1a2e';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Health bar if damaged
        if (this.radius < 40) {
            ctx.fillStyle = '#ff0000';
            ctx.beginPath();
            ctx.rect(this.x - 20, this.y - this.radius - 10, 40, 5);
            ctx.fill();
            ctx.fillStyle = '#00ff00';
            ctx.beginPath();
            ctx.rect(this.x - 20, this.y - this.radius - 10, 40 * (this.radius / 40), 5);
            ctx.fill();
        }
    }
}

class Bullet {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.radius = 5;
        this.speed = 8;
        this.color = bulletColors[Math.floor(Math.random() * bulletColors.length)];
        this.health = 1;
    }

    update() {
        this.x -= this.speed;

        if (this.x < 0) {
            this.remove();
        }
    }

    remove() {
        const index = bullets.indexOf(this);
        if (index > -1) {
            bullets.splice(index, 1);
        }
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.fill();
    }
}

// Game state variables
let bullets = [];

function checkSpawnCondition() {
    if (zombiesLeft < zombiesToSpawn && zombiesCount < maxZombies) {
        zombiesToSpawn++;
        zombiesLeft++;
    }
}

function spawnZombie() {
    if (zombiesCount < maxZombies && zombiesToSpawn > 0) {
        zombies.push(new Zombie());
        zombiesCount++;
        zombiesToSpawn--;
    }
}

function gameLoop() {
    if (!gameRunning) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Spawn zombies
    if (zombiesToSpawn > 0 && Math.random() < 0.02) {
        spawnZombie();
    }

    // Update and draw zombies
    for (let i = zombies.length - 1; i >= 0; i--) {
        zombies[i].update();
        zombies[i].draw();

        if (zombies[i].radius <= 0) {
            zombies.splice(i, 1);
            zombiesCount--;
        }
    }

    // Update and draw bullets
    for (let i = bullets.length - 1; i >= 0; i--) {
        bullets[i].update();
        bullets[i].draw();

        if (bullets[i].health <= 0 || bullets[i].x < 0) {
            bullets.splice(i, 1);
        }
    }

    // Check game over condition
    if (zombiesCount >= maxZombies) {
        endGame();
    }

    animationId = requestAnimationFrame(gameLoop);
}

// Handle clicks
canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Check if clicked on a zombie
    for (let i = zombies.length - 1; i >= 0; i--) {
        const dx = mouseX - zombies[i].x;
        const dy = mouseY - zombies[i].y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < zombies[i].radius + 10) {
            // Create bullet
            bullets.push(new Bullet(mouseX, mouseY));
            
            // Get zombie data for animation
            const zombie = zombies[i];
            const startZombieX = zombie.x;
            const startZombieY = zombie.y;

            // Animate zombie
            let animIndex = 0;
            const animateZombie = () => {
                if (animIndex > 10) {
                    clearInterval(animInterval);
                    continue;
                }

                const progress = animIndex / 10;
                zombie.x = startZombieX + (mouseX - startZombieX) * progress;
                zombie.y = startZombieY + (mouseY - startZombieY) * progress;
                zombie.radius = 25;

                animIndex++;
                animInterval = requestAnimationFrame(animateZombie);
            };
            animInterval = requestAnimationFrame(animateZombie);
            break;
        }
    }
});

// Restart game button
document.getElementById('restartBtn').addEventListener('click', () => {
    // Reset game state
    score = 0;
    zombieCount = 0;
    zombies = [];
    zombiesToSpawn = 3;
    zombiesLeft = 3;
    maxZombies = 5;
    bullets = [];
    zombies = [];
    gameRunning = true;

    // Hide modals
    document.getElementById('gameOverModal').style.display = 'none';
    document.getElementById('gameModal').style.display = 'none';

    // Start game loop
    gameLoop();
});

// Start game on load
gameLoop();
