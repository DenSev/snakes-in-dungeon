from __future__ import print_function
import shelve

import libtcodpy as libtcod
import objects as o
import globals as g


class Rect:
    # a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        # returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)


class Tile:
    # a tile of the map and its properties
    def __init__(self, blocked, block_sight=None):
        self.explored = False
        self.blocked = blocked

        # by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight


tile_map = None
fov_map = None
fov_recompute = None
objects = None
player = None
con = None
MAX_OPTIONS = 26
dungeon_level = 1


def create_room(room):
    global tile_map
    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            tile_map[x][y].blocked = False
            tile_map[x][y].block_sight = False


def make_map():
    global tile_map, objects, stairs

    # fill map with "blocked" tiles
    tile_map = [[Tile(True)
                 for y in range(g.MAP_HEIGHT)]
                for x in range(g.MAP_WIDTH)]

    objects = [player]

    rooms = []
    num_rooms = 0
    new_x = 0
    new_y = 0

    for r in range(g.MAX_ROOMS):
        # random width and height
        w = libtcod.random_get_int(0, g.ROOM_MIN_SIZE, g.ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, g.ROOM_MIN_SIZE, g.ROOM_MAX_SIZE)
        # random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, g.MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, g.MAP_HEIGHT - h - 1)

        # "Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        # run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            # this means there are no intersections, so this room is valid

            # "paint" it to the map's tiles
            create_room(new_room)

            # center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                # this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
            else:
                # all rooms after the first:
                # connect it to the previous room with a tunnel

                # center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                # draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    # first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    # first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            # finally, append the new room to the list
            place_objects(new_room)
            rooms.append(new_room)
            num_rooms += 1

    # create stairs at the center of the last room
    stairs = o.Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back(objects)  # so it's drawn below the monsters


def create_h_tunnel(x1, x2, y):
    global tile_map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        tile_map[x][y].blocked = False
        tile_map[x][y].block_sight = False


def create_v_tunnel(y1, y2, x):
    global tile_map
    # vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        tile_map[x][y].blocked = False
        tile_map[x][y].block_sight = False


def render_all():
    global fov_map, fov_recompute

    if fov_recompute:
        # recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, g.TORCH_RADIUS, g.FOV_LIGHT_WALLS, g.FOV_ALGO)

        # go through all tiles, and set their background color
        for y in range(g.MAP_HEIGHT):
            for x in range(g.MAP_WIDTH):

                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = tile_map[x][y].block_sight

                if not visible:
                    if tile_map[x][y].explored:
                        if wall:
                            libtcod.console_set_char_background(con, x, y, g.color_dark_wall, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_char_background(con, x, y, g.color_dark_ground, libtcod.BKGND_SET)
                else:
                    # it's visible
                    if wall:
                        libtcod.console_set_char_background(con, x, y, g.color_light_wall, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background(con, x, y, g.color_light_ground, libtcod.BKGND_SET)
                    tile_map[x][y].explored = True

    # draw all objects in the list
    for object in objects:
        if object != player:
            object.draw(fov_map, tile_map, con)
    player.draw(fov_map, tile_map, con)

    # blit the contents of con to the root console and present it
    libtcod.console_blit(con, 0, 0, g.SCREEN_WIDTH, g.SCREEN_HEIGHT, 0, 0, 0)

    # prepare to render the GUI panel
    libtcod.console_set_default_background(g.panel, libtcod.black)
    libtcod.console_clear(g.panel)

    # print the game messages, one line at a time
    y = 1
    for (line, color) in g.game_msgs:
        libtcod.console_set_default_foreground(g.panel, color)
        libtcod.console_print_ex(g.panel, g.MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    # show the player's stats
    render_bar(1, 1, g.BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp(player),
               libtcod.light_red, libtcod.darker_red)

    # display names of objects under the mouse
    libtcod.console_set_default_foreground(g.panel, libtcod.light_gray)
    libtcod.console_print_ex(g.panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
    libtcod.console_print_ex(g.panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon level ' + str(dungeon_level))

    # blit the contents of "panel" to the root console
    libtcod.console_blit(g.panel, 0, 0, g.SCREEN_WIDTH, g.PANEL_HEIGHT, 0, 0, g.PANEL_Y)


def from_dungeon_level(table):
    # returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0


def handle_keys():
    global fov_recompute, stairs

    if g.key.vk == libtcod.KEY_ENTER and g.key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif g.key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  # exit game

    if g.game_state == 'playing':
        # movement keys
        if g.key.vk == libtcod.KEY_UP or g.key.vk == libtcod.KEY_KP8:
            player_move_or_attack(0, -1)
        elif g.key.vk == libtcod.KEY_DOWN or g.key.vk == libtcod.KEY_KP2:
            player_move_or_attack(0, 1)
        elif g.key.vk == libtcod.KEY_LEFT or g.key.vk == libtcod.KEY_KP4:
            player_move_or_attack(-1, 0)
        elif g.key.vk == libtcod.KEY_RIGHT or g.key.vk == libtcod.KEY_KP6:
            player_move_or_attack(1, 0)
        elif g.key.vk == libtcod.KEY_HOME or g.key.vk == libtcod.KEY_KP7:
            player_move_or_attack(-1, -1)
        elif g.key.vk == libtcod.KEY_PAGEUP or g.key.vk == libtcod.KEY_KP9:
            player_move_or_attack(1, -1)
        elif g.key.vk == libtcod.KEY_END or g.key.vk == libtcod.KEY_KP1:
            player_move_or_attack(-1, 1)
        elif g.key.vk == libtcod.KEY_PAGEDOWN or g.key.vk == libtcod.KEY_KP3:
            player_move_or_attack(1, 1)
        elif g.key.vk == libtcod.KEY_KP5:
            pass  # do nothing ie wait for the monster to come to you

        else:
            key_char = chr(g.key.c)

            if key_char == 'g':
                # pick up an item
                for object in objects:  # look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up(objects)
                        break

            if key_char == 'i':
                # show the inventory
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()

            if key_char == 'd':
                # show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop(player, objects)

            if key_char == 'u':
                # go down stairs, if the player is on them
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()

            if key_char == 'c':
                # show character information
                level_up_xp = g.LEVEL_UP_BASE + (player.level - 1) * g.LEVEL_UP_FACTOR
                msgbox(
                    'Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                    '\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(
                        player.fighter.max_hp(player)) +
                    '\nAttack: ' + str(player.fighter.power(player)) + '\nDefense: ' + str(
                        player.fighter.defense(player)),
                    g.CHARACTER_SCREEN_WIDTH)

            return 'didnt-take-turn'


def next_level():
    global dungeon_level
    # advance to the next level
    g.message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
    player.fighter.heal(player.fighter.max_hp(player) / 2, player)  # heal the player by 50%

    g.message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
    make_map()  # create a fresh new level!
    initialize_fov()
    dungeon_level += 1


def check_level_up():
    # see if the player's experience is enough to level-up
    level_up_xp = g.LEVEL_UP_BASE + (player.level - 1) * g.LEVEL_UP_FACTOR
    if player.fighter.xp >= level_up_xp:
        # it is! level up
        player.level += 1
        player.fighter.xp -= level_up_xp
        g.message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)

        choice = None
        while choice is None:  # keep asking until a choice is made
            choice = menu('Level up! Choose a stat to raise:\n',
                          ['Constitution (+20 HP, from ' + str(player.fighter.max_hp(player)) + ')',
                           'Strength (+1 attack, from ' + str(player.fighter.power(player)) + ')',
                           'Agility (+1 defense, from ' + str(player.fighter.defense(player)) + ')'],
                          g.LEVEL_SCREEN_WIDTH)

        if choice == 0:
            player.fighter.base_max_hp += 20
            player.fighter.hp += 20
        elif choice == 1:
            player.fighter.base_power += 1
        elif choice == 2:
            player.fighter.base_defense += 1


def place_objects(room):
    # maximum number of monsters per room
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])

    # chance of each monster
    monster_chances = {
        'orc': 80,
        'troll': from_dungeon_level([[15, 3], [30, 5], [60, 7]])
    }

    # monster_chances = {'orc': 80, 'troll': 20}
    monster_creators = {'orc': o.create_orc, 'troll': o.create_troll}

    # choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)

    for i in range(num_monsters):
        # choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        choice = random_choice(monster_chances)
        monster = monster_creators[choice](x, y)

        # only place it if the tile is not blocked
        if not o.is_blocked(x, y, tile_map, objects):
            objects.append(monster)
    # place the items
    place_items(room)


def place_items(room):
    # maximum number of items per room
    max_items = from_dungeon_level([[1, 1], [2, 4]])

    # chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {
        'heal': 35,
        'lightning': from_dungeon_level([[25, 4]]),
        'fireball': from_dungeon_level([[25, 6]]),
        'confuse': from_dungeon_level([[10, 2]]),
        'sword': from_dungeon_level([[5, 4]]),
        'shield': from_dungeon_level([[15, 8]])
    }

    # item_chances = {'heal': 70, 'lightning': 10, 'fireball': 10, 'confuse': 10}
    item_creators = {
        'heal': o.create_heal_potion,
        'lightning': o.create_lightning_scroll,
        'fireball': o.create_fireball_scroll,
        'confuse': o.create_confuse_scroll,
        'sword': o.place_sword,
        'shield': o.place_shield
    }
    item_uses = {
        'heal': cast_heal,
        'lightning': cast_lightning,
        'fireball': cast_fireball,
        'confuse': cast_confuse,
        'sword': None,
        'shield': None
    }

    # choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)

    for i in range(num_items):
        # choose random spot for this item
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        # only place it if the tile is not blocked
        if not o.is_blocked(x, y, tile_map, objects):
            choice = random_choice(item_chances)
            item = item_creators[choice](x, y, item_uses[choice])

            objects.append(item)
            item.send_to_back(objects)  # items appear below other objects


def random_choice(chances_dict):
    # choose one option from dictionary of chances, returning its key
    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[random_choice_index(chances)]


def random_choice_index(chances):
    # choose one option from list of chances, returning its index
    # the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))

    # go through all chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w

        # see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1


def player_move_or_attack(dx, dy):
    global fov_recompute, player

    # the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    # try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break

    # attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target, objects, player)
    else:
        player.move(dx, dy, tile_map, objects)
        fov_recompute = True


def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    # render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)

    # render the background first
    libtcod.console_set_default_background(g.panel, back_color)
    libtcod.console_rect(g.panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    # now render the bar on top
    libtcod.console_set_default_background(g.panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(g.panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    # finally, some centered text with the values
    libtcod.console_set_default_foreground(g.panel, libtcod.white)
    libtcod.console_print_ex(g.panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
                             name + ': ' + str(value) + '/' + str(maximum))


def get_names_under_mouse():
    # return a string with the names of all objects under the mouse
    (x, y) = (g.mouse.cx, g.mouse.cy)

    # create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
             if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

    names = ', '.join(names)  # join the names, separated by commas
    return names.capitalize()


def main_menu():
    global con

    con = libtcod.console_new(g.SCREEN_WIDTH, g.SCREEN_HEIGHT)
    libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
    libtcod.console_init_root(g.SCREEN_WIDTH, g.SCREEN_HEIGHT, 'python/libtcod tutorial', False)
    libtcod.sys_set_fps(g.LIMIT_FPS)

    img = libtcod.image_load('menu_background1.png')

    # show the background image, at twice the regular console resolution

    while not libtcod.console_is_window_closed():
        # show the background image, at twice the regular console resolution
        libtcod.image_blit_2x(img, 0, 0, 0)

        # show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.light_yellow)
        libtcod.console_print_ex(0, g.SCREEN_WIDTH / 2, g.SCREEN_HEIGHT / 2 - 4, libtcod.BKGND_NONE, libtcod.CENTER,
                                 'SNAKES IN THE DUNGEON')
        libtcod.console_print_ex(0, g.SCREEN_WIDTH / 2, g.SCREEN_HEIGHT - 2, libtcod.BKGND_NONE, libtcod.CENTER,
                                 'by whothefuckcares')

        # show options and wait for the player's choice
        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)

        if choice == 0:  # new game
            new_game()
            play_game()
        if choice == 1:  # load last game
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
                continue
            play_game()
        elif choice == 2:  # quit
            break


def msgbox(text, width=50):
    menu(text, [], width)  # use menu() as a sort of "message box"


def menu(header, options, width):
    if len(options) > MAX_OPTIONS:
        raise ValueError('Cannot have a menu with more than 26 options.')

    # calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, g.SCREEN_HEIGHT, header)

    if header == '':
        header_height = 0

    height = len(options) + header_height

    # create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)

    # print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    # print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    # blit the contents of "window" to the root console
    x = g.SCREEN_WIDTH / 2 - width / 2
    y = g.SCREEN_HEIGHT / 2 - height / 2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    # present the root console to the player and wait for a key-press
    libtcod.console_flush()
    g.key = libtcod.console_wait_for_keypress(True)

    if g.key.vk == libtcod.KEY_ENTER and g.key.lalt:  # (special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    index = g.key.c - ord('a')
    if 0 <= index < len(options):
        return index
    return None


def inventory_menu(header):
    # show a menu with each item of the inventory as an option
    if len(g.inventory) == 0:
        options = ['Inventory is empty.']
    else:

        options = []
        for item in g.inventory:
            text = item.name
            # show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

        # options = [item.name for item in g.inventory]

    index = menu(header, options, g.INVENTORY_WIDTH)
    # convert the ASCII code to an index; if it corresponds to an option, return it

    # if an item was chosen, return it
    if index is None or len(g.inventory) == 0:
        return None
    return g.inventory[index].item


def cast_heal():
    # heal the player
    if player.fighter.hp == player.fighter.max_hp(player):
        g.message('You are already at full health.', libtcod.red)
        return 'cancelled'

    g.message('Your wounds start to feel better!', libtcod.light_violet)
    player.fighter.heal(g.HEAL_AMOUNT, player)


def cast_lightning():
    # find closest enemy (inside a maximum range) and damage it
    monster = closest_monster(g.LIGHTNING_RANGE)
    if monster is None:  # no enemy found within maximum range
        g.message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'

    # zap it!
    g.message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
              + str(g.LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
    monster.fighter.take_damage(g.LIGHTNING_DAMAGE, objects, player)


def cast_confuse():
    # ask the player for a target to confuse
    g.message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
    monster = target_monster(g.CONFUSE_RANGE)
    if monster is None:
        return 'cancelled'

    # replace the monster's AI with a "confused" one; after some turns it will restore the old AI
    old_ai = monster.ai
    monster.ai = o.ConfusedMonster(old_ai)
    monster.ai.owner = monster  # tell the new component who owns it
    g.message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)


def cast_fireball():
    global objects, player
    # ask the player for a target tile to throw a fireball at
    g.message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None: return 'cancelled'
    g.message('The fireball explodes, burning everything within ' + str(g.FIREBALL_RADIUS) + ' tiles!', libtcod.orange)

    for obj in objects:  # damage every fighter in range, including the player
        if obj.distance(x, y) <= g.FIREBALL_RADIUS and obj.fighter:
            g.message('The ' + obj.name + ' gets burned for ' + str(g.FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
            obj.fighter.take_damage(g.FIREBALL_DAMAGE, objects, player)


def closest_monster(max_range):
    global objects, player
    # find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  # start with (slightly more than) maximum range

    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            # calculate distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist:  # it's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy


def target_tile(max_range=None):
    # return the position of a tile left-clicked in player's FOV (optionally in a range),
    # or (None,None) if right-clicked.
    while True:
        # render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, g.key, g.mouse)
        render_all()

        (x, y) = (g.mouse.cx, g.mouse.cy)

        if (g.mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
                (max_range is None or player.distance(x, y) <= max_range)):
            return x, y

        if g.mouse.rbutton_pressed or g.key.vk == libtcod.KEY_ESCAPE:
            return None, None  # cancel if the player right-clicked or pressed Escape


def target_monster(max_range=None):
    # returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  # player cancelled
            return None

        # return the first clicked monster, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj


def new_game():
    global player, con

    # create object representing the player
    fighter_component = o.Fighter(hp=30, defense=2, power=5, death_function=o.player_death, xp=0)
    player = o.Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)
    player.level = 1

    # generate map (at this point it's not drawn to the screen)
    make_map()
    initialize_fov()

    g.game_state = 'playing'
    g.inventory = []

    # create the list of game messages and their colors, starts empty
    g.game_msgs = []

    # initial equipment: a dagger
    equipment_component = o.Equipment(slot='right hand', power_bonus=2)
    obj = o.Object(0, 0, '-', 'dagger', libtcod.sky, equipment=equipment_component)
    g.inventory.append(obj)
    equipment_component.equip()
    obj.always_visible = True

    # a warm welcoming message!
    g.message('Welcome stranger! Prepare to die.', libtcod.red)


def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True
    libtcod.console_clear(con)  # unexplored areas start black (which is the default background color)

    # create the FOV map, according to the generated map
    fov_map = libtcod.map_new(g.MAP_WIDTH, g.MAP_HEIGHT)
    for y in range(g.MAP_HEIGHT):
        for x in range(g.MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not tile_map[x][y].block_sight, not tile_map[x][y].blocked)


def save_game():
    # open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = tile_map
    file['objects'] = objects
    file['player_index'] = objects.index(player)
    file['inventory'] = g.inventory
    file['game_msgs'] = g.game_msgs
    file['game_state'] = g.game_state
    file['stairs_index'] = objects.index(stairs)
    file['dungeon_level'] = dungeon_level

    file.close()


def load_game():
    # open the previously saved shelve and load the game data
    global tile_map, objects, player, stairs, dungeon_level

    file = shelve.open('savegame', 'r')
    tile_map = file['map']
    objects = file['objects']
    player = objects[file['player_index']]  # get index of player in objects list and access it
    g.inventory = file['inventory']
    g.game_msgs = file['game_msgs']
    g.game_state = file['game_state']
    stairs = objects[file['stairs_index']]
    dungeon_level = file['dungeon_level']

    file.close()

    initialize_fov()


def play_game():
    global objects, fov_map, player, tile_map
    player_action = None
    counter = 1

    while not libtcod.console_is_window_closed():
        counter += 1

        if counter % 100 == 0:
            print(counter)
        # render the screen
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, g.key, g.mouse)
        render_all()

        libtcod.console_flush()
        check_level_up()

        # erase all objects at their old locations, before they move
        for object in objects:
            object.clear(con)

        # handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break

        # let monsters take their turn
        if g.game_state == 'playing' and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.ai.take_turn(fov_map, player, tile_map, objects)


main_menu()
