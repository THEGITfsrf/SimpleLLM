"""
Zombie Game - Simple Game Application
A basic zombie survival game with Python
"""

import random
import time

class ZombieGame:
    def __init__(self, player_health=100, zombie_count=5):
        self.player_health = player_health
        self.max_health = 100
        self.zombie_count = zombie_count
        self.score = 0
        self.game_over = False
        
    def play_round(self):
        """Play a single round of the game"""
        if self.game_over:
            print("Game has already ended!")
            return False
            
        print(f"\n=== Round {self.zombie_count} ===")
        print(f"Health: {self.player_health}/{self.max_health}")
        print(f"Zombies: {self.zombie_count}")
        print("Score: {}".format(self.score))
        
        if self.player_health <= 0:
            print("You died! Game over.")
            self.game_over = True
            return False
        
        # Game logic would go here
        # For now, let's have a simple outcome
        survival_chance = 50  # 50% chance to survive
        
        if survival_chance > random.randint(1, 100):
            print("You survived this round!")
            self.score += 10
            if self.zombie_count > 1:
                self.zombie_count -= 1
        else:
            print("You were attacked! Health reduced.")
            self.player_health -= 10
            if self.zombie_count > 0:
                self.zombie_count -= 1
                self.score -= 5
        
        print("\n=== End of Round ===")
        return True
    
    def restart_game(self):
        """Restart the game with new parameters"""
        self.player_health = self.max_health
        self.zombie_count = self.zombie_count // 2 + 2
        self.score = 0
        self.game_over = False
        return True
    
    def print_stats(self):
        """Print current game statistics"""
        print("\n--- Game Statistics ---")
        print("Health: {}/{}".format(self.player_health, self.max_health))
        print("Zombies remaining: {}".format(self.zombie_count))
        print("Score: {}".format(self.score))
        print("=========================")
        
    def end_game(self):
        """Print final game results"""
        self.print_stats()
        if self.player_health > 0:
            print("🎉 You survived all {} rounds!".format(self.zombie_count))
        else:
            print("💀 You died in round {}".format(self.zombie_count))
        return self.score
    
    def play(self):
        """Main game loop"""
        print("Welcome to Zombie Game!")
        while not self.game_over:
            self.play_round()
            # Check if zombie count reached 0
            if self.zombie_count == 0:
                self.score += self.zombie_count * 10
                self.zombie_count = self.zombie_count // 2 + 2
                print("Zombies defeated! Game continues...")
            
            self.print_stats()
            
            # Check if player is dead
            if self.player_health <= 0:
                self.end_game()
                print("🏁 Game Over")
                break
                break
            
            # Ask if player wants to continue
            cont = input("Play another round? (y/n): ").lower().strip()
            if cont != 'y':
                self.end_game()
                print("🏁 Thank you for playing!")
                break

if __name__ == "__main__":
    game = ZombieGame(player_health=100, zombie_count=5)
    try:
        game.play()
    except KeyboardInterrupt:
        print("\nGame ended by user")
