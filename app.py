from flask import Flask, render_template, jsonify, request
import random
import time

app = Flask(__name__)

# Game state
game_state = {
    "active": False,
    "score": 0,
    "zombies_on_screen": 0,
    "zombies_limit": 10,
    "max_zombies": 0,
    "spawn_timer": 0,
    "spawn_interval": 5.0,
    "spawn_rate_increase": 0.1,
    "zombies": []
}

@app.route('/')
def index():
    return render_template('game.html')

@app.route('/api/game-status', methods=['GET'])
def get_game_status():
    return jsonify(game_state)

@app.route('/api/start-game', methods=['POST'])
def start_game():
    global game_state
    game_state["active"] = True
    game_state["score"] = 0
    game_state["zombies_on_screen"] = 0
    game_state["max_zombies"] = 10
    game_state["spawn_rate_increase"] = 0.1
    return jsonify({"status": "started"})

@app.route('/api/spawn-zombie', methods=['POST'])
def spawn_zombie():
    global game_state
    game_state["zombies_on_screen"] += 1
    # Get coordinates from client
    client_data = request.get_json()
    if client_data:
        zombie_data = {
            "x": client_data.get("x"),
            "y": client_data.get("y"),
            "id": random.randint(1000, 9999)
        }
    else:
        # Default spawn position
        zombie_data = {
            "x": random.uniform(0, 100),
            "y": random.uniform(50, 100),
            "id": random.randint(1000, 9999)
        }
    game_state["zombies"] = [zombie_data]
    return jsonify({"status": "spawned", "zombies": game_state["zombies"]})

@app.route('/api/kill-zombie', methods=['POST'])
def kill_zombie():
    global game_state
    client_data = request.get_json()
    if client_data and "zombie_id" in client_data:
        game_state["zombies_on_screen"] -= 1
        game_state["score"] += 10
        return jsonify({"status": "killed", "score": game_state["score"]})
    else:
        return jsonify({"status": "error", "message": "No zombie ID provided"})

@app.route('/api/check-game-over', methods=['POST'])
def check_game_over():
    global game_state
    if game_state["zombies_on_screen"] >= game_state["max_zombies"]:
        game_state["active"] = False
        return jsonify({"status": "gameover", "message": "Too many zombies!", "score": game_state["score"]})
    return jsonify({"status": "playing"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
