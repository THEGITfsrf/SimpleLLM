// Game state
let gameState = {
    zombies: [],
    bullets: [],
    score: 0,
    zombieCount: 0,
    isGameOver: false,
    zombieSpawnDelay: 2000,
    
    spawnZombie: function() {
        if (this.zombies.length >= 15) {
            return;
        }
        
        const x = Math.random() * 700 + 50;
        const y = Math.random() * 500 + 50;
        this.zombies.push({ x, y });
        this.zombieCount++;
    },
    
    updateBullets: function() {
        if (this.bullets.length > 0) {
            for (let i = this.bullets.length - 1; i >= 0; i--) {
                const b = this.bullets[i];
                b.x += b.speed * 0.005;
                if (b.x > 750 || b.x < 0) {
                    this.bullets.splice(i, 1);
                }
            }
        }
    },
    
    checkCollisions: function() {
        for (let b = this.bullets.length - 1; b >= 0; b--) {
            for (let z = this.zombies.length - 1; z >= 0; z--) {
                const bullet = this.bullets[b];
                const zombie = this.zombies[z];
                
                const dx = bullet.x - zombie.x;
                const dy = bullet.y - zombie.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < 20) {
                    this.score += 10;
                    this.zombies.splice(z, 1);
                    this.bullets.splice(b, 1);
                    
                    if (this.score % 50 === 0) {
                        this.zombieSpawnDelay = Math.max(500, this.zombieSpawnDelay - 100);
                    }
                }
            }
        }
    },
    
    checkZombieCount: function() {
        if (this.zombieCount > 10) {
            return true;
        }
        return false;
    },
    
    draw: function(ctx) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        
        const gradient = ctx.createLinearGradient(0, 0, 750, 500);
        gradient.addColorStop(0, '#2c1810');
        gradient.addColorStop(1, '#1a1a1a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        
        this.zombies.forEach(zombie => {
            const pulseScale = 1 + Math.sin(Date.now() / 200) * 0.05;
            ctx.fillStyle = '#e74c3c';
            ctx.beginPath();
            ctx.arc(zombie.x, zombie.y, 15 * pulseScale, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#c0392b';
            ctx.stroke();
            
            ctx.fillStyle = '#ecf0f1';
            ctx.font = '10px Arial';
            ctx.fillText('Z', zombie.x - 5, zombie.y + 10);
        });
        
        this.bullets.forEach(bullet => {
            ctx.fillStyle = '#3498db';
            ctx.beginPath();
            ctx.arc(bullet.x, bullet.y, 5, 0, Math.PI * 2);
            ctx.fill();
        });
        
        ctx.fillStyle = '#f1c40f';
        ctx.font = '20px Arial';
        ctx.fillText(this.score, 700, 40);
    }
};

// Create canvas
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
canvas.width = 800;
canvas.height = 550;

// Game loop
let lastFrameTime = Date.now();
function gameLoop() {
    if (gameState.isGameOver) {
        if (gameState.checkZombieCount()) {
            document.getElementById('gameOverModal').style.display = 'block';
        }
        return;
    }
    
    // Spawn zombies
    if (Date.now() - lastFrameTime > gameState.zombieSpawnDelay) {
        gameState.spawnZombie();
        lastFrameTime = Date.now();
    }
    
    // Update bullets
    gameState.updateBullets();
    
    // Check collisions
    gameState.checkCollisions();
    
    // Draw everything
    gameState.draw(ctx);
    
    requestAnimationFrame(gameLoop);
}

// Mouse click to shoot
canvas.addEventListener('mousedown', function(e) {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    // Find closest zombie
    let closestZombie = null;
    let minDist = Infinity;
    
    for (let z of gameState.zombies) {
        const dx = z.x - mouseX;
        const dy = z.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        if (dist < minDist && dist < 50) {
            minDist = dist;
            closestZombie = z;
        }
    }
    
    if (closestZombie) {
        // Spawn bullet
        gameState.bullets.push({ x: closestZombie.x, y: closestZombie.y, speed: 10 });
        gameState.score += 5;
        
        // Add score visual
        ctx.fillStyle = '#2ecc71';
        ctx.fillText('+5', closestZombie.x, closestZombie.y - 20);
    }
});

// Keyboard restart
document.getElementById('restartBtn').addEventListener('click', function() {
    // Reset game state
    gameState = {
        zombies: [],
        bullets: [],
        score: 0,
        zombieCount: 0,
        isGameOver: false,
        zombieSpawnDelay: 2000,
    };
    
    // Hide game over modal
    document.getElementById('gameOverModal').style.display = 'none';
    document.getElementById('gameModal').style.display = 'none';
    
    // Start game
    gameLoop();
});

// Start game on load
gameLoop();