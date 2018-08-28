import libtcodpy as libtcod


def handle_keys():
    global player_x, player_y

    #key = libtcod.console_check_for_keypress()  #real-time
    key = libtcod.console_wait_for_keypress(True)  # turn-based

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return True  # exit game

    # movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        player_y -= 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        player_y += 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        player_x -= 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        player_x += 1


#############################################
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 60
player_x = SCREEN_WIDTH / 2
player_y = SCREEN_HEIGHT / 2

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)

while not libtcod.console_is_window_closed():

    libtcod.console_set_default_foreground(0, libtcod.white)
    libtcod.console_put_char(0, player_x, player_y, '@', libtcod.BKGND_NONE)

    libtcod.console_flush()

    libtcod.console_put_char(0, player_x, player_y, ' ', libtcod.BKGND_NONE)

    # handle keys and exit game if needed
    shutdown = handle_keys()
    if shutdown:
        break