from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# --- Setup ---
app = Ursina()

# --- Game Logic ---
def block_hit(hit_info):
    """Handles what happens when the turret hits a block."""
    # Check if what we hit is an actual block (we give them a specific model/name)
    if hit_info.entity.name == "block":
        # Simple "destruction": make the block fall and despawn after a delay
        hit_info.entity.y += 1 # Move it slightly up first for visual effect
        hit_info.entity.animate_position(
            (hit_info.entity.x, hit_info.entity.y - 2, hit_info.entity.z), 
            duration=1.5
        )
        # After falling, destroy it
        invoke(destroy, hit_info.entity, delay=2)
        print("💥 Block Knocked Down!")
    else:
        # Maybe hit something else, like the ground?
        pass

def input(key):
    """Input handler for shooting (Left Click)."""
    if key == 'left mouse down':
        # Raycast: Shoot an invisible line forward from the camera
        # We check 10 units out (reach)
        hit_ray = raycast(camera.world_position, camera.forward, distance=20)
        
        if hit_ray.hit:
            # Pass the hit information to our handler function
            block_hit(hit_ray)

# --- Environment Setup ---

# 1. Ground
ground = Entity(model='plane', collider='box', scale=(100, 1, 100), color=color.gray)

# 2. Spawn the blocks
def spawn_block(x, z):
    """Creates a destructible cube at specific coordinates."""
    block = Entity(
        model='cube', 
        collider='box', 
        position=(x, 0.5, z), 
        scale=(1, 1, 1), 
        color=color.rgb(100, 100, 200), 
        name="block" # IMPORTANT: This name allows our hit function to know what to destroy
    )
    return block

# Place a few blocks randomly
spawn_block(-10, 5)
spawn_block(10, -5)
spawn_block(5, 10)
spawn_block(-5, -15)
spawn_block(15, 0)


# 3. Player Setup (We replace the default camera with a controllable character)
player = FirstPersonController(speed=5)
player.y = 2 # Start player slightly elevated

# --- Run the App ---
Sky() # Nice sky background
Title(text='Turret Tower Defense', color=color.white)
Text(text='WASD/Arrows to Move | Left Click to Shoot', y=0.5, z=2)

app.run()