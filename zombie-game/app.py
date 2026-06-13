from flask import Flask, render_template, request, jsonify
import json
import time

app = Flask(__name__)

# Game state
game_state = {
    "score": 0,
    "zombies": [],
    "zombie_count": 0,
    "spawn_rate": 2.0,
    "spawn_timer": 0,
    "game_over": False,
    "last_spawn_time": time.time()
}

MAX_ZOMBIES = 50
SPAWN_RATE_MIN = 0.5

@app.route('/')
def index():
    return render_template('index.html', 
                         score=game_state["score"],
                         zombie_count=game_state["zombie_count"],
                         is_game_over=game_state["game_over"],
                         spawn_rate=game_state["spawn_rate"])

@app.route('/game/action', methods=['POST'])
def game_action():
    global game_state
    
    data = request.json
    
    action = data.get('action', '')
    x = data.get('x', 0)
    y = data.get('y', 0)
    
    if action == 'shoot':
        shoot_zombie(x, y)
    
    return jsonify({"success": True})

def shoot_zombie(x, y):
    # game_state is global now, no need to pass it as parameter
    global game_state
    
    game_state["spawn_timer"] = time.time()
    
    for zombie in game_state["zombies"]:
        # Check if zombie is clicked
        if abs(zombie["x"] - x) < 15 and abs(zombie["y"] - y) < 15:
            zombie["dead"] = True
            game_state["score"] += 10
            game_state["zombie_count"] -= 1
    
    # Check game over condition
    if game_state["zombie_count"] >= MAX_ZOMBIES:
        game_state["game_over"] = True
    
    # Update spawn rate
    game_state["spawn_rate"] = max(SPAWN_RATE_MIN, game_state["spawn_rate"] - 0.05)

def spawn_zombie():
    global game_state
    
    # Add some randomness to spawn position
    x = 100 + (game_state["score"] / 5)
    y = 150 + (game_state["score"] / 10)
    
    zombie = {
        "x": x,
        "y": y,
        "size": 30,
        "dead": False
    }
    
    game_state["zombies"].append(zombie)
    game_state["zombie_count"] += 1

def update_game():
    global game_state
    
    # Spawn zombies
    spawn_interval = max(SPAWN_RATE_MIN, game_state["spawn_rate"])
    game_state["spawn_timer"] += time.time()
    
    if game_state["spawn_timer"] >= spawn_interval:
        spawn_zombie()
        game_state["spawn_timer"] = 0
    
    # Remove dead zombies
    game_state["zombies"] = [z for z in game_state["zombies"] if not z["dead"]]
    game_state["zombie_count"] = len(game_state["zombies"])

if __name__ == '__main__':
    app.run(debug=True, port=5050)
