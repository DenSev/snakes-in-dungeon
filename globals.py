import libtcodpy as libtcod

#############################################
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 60
#############################################
MAP_WIDTH = 80
MAP_HEIGHT = 50

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

color_dark_wall = libtcod.Color(50, 50, 50)
color_dark_ground = libtcod.Color(100, 100, 100)
color_light_wall = libtcod.Color(70, 70, 70)
color_light_ground = libtcod.Color(120, 120, 120)
#############################################

FOV_ALGO = 0  # default FOV algorithm
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

#############################################
MAX_ROOM_MONSTERS = 3

player_x = 25
player_y = 23
#############################################
game_state = 'playing'
player_action = None