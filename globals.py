import libtcodpy as libtcod
import textwrap

#############################################
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
# sizes and coordinates relevant for the GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
INVENTORY_WIDTH = 50

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

LIMIT_FPS = 15
#############################################
MAP_WIDTH = 80
MAP_HEIGHT = 43

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
MAX_ROOM_ITEMS = 2

player_x = 25
player_y = 23
#############################################

HEAL_AMOUNT = 4

game_state = 'playing'
player_action = None
game_msgs = []
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

mouse = libtcod.Mouse()
key = libtcod.Key()


inventory = []


def message(new_msg, color=libtcod.white):
    # split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        # if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        # add the new line as a tuple, with the text and the color
        game_msgs.append((line, color))
