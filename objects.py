import libtcodpy as libtcod
import math
import globals as g


class Item:

    def __init__(self, use_function=None):
        self.use_function = use_function

    # an item that can be picked up and used.
    def pick_up(self, objects):
        # add to the player's inventory and remove from the map
        if len(g.inventory) >= 26:
            g.message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            g.inventory.append(self.owner)
            objects.remove(self.owner)
            g.message('You picked up a ' + self.owner.name + '!', libtcod.green)

    def use(self):
        # just call the "use_function" if it is defined
        if self.use_function is None:
            g.message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                g.inventory.remove(self.owner)  # destroy after use, unless it was cancelled for some reason

    def drop(self, player, objects):

        # add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        g.inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        g.message('You dropped a ' + self.owner.name + '.', libtcod.yellow)


class Fighter:
    # combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, death_function=None):
        self.xp = xp
        self.death_function = death_function
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power

    def take_damage(self, damage, objects, player):
        # apply damage if possible
        if damage > 0:
            self.hp -= damage
            # check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner, objects)
                    if self.owner != player:  # yield experience to the player
                        player.fighter.xp += self.xp

    def heal(self, amount):
        # heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def attack(self, target, objects, player):
        # a simple formula for attack damage
        damage = self.power - target.fighter.defense

        if damage > 0:
            # make the target take some damage
            g.message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage, objects, player)
        else:
            g.message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')


class BasicMonster:

    def __init__(self):
        print("whatever")

    # AI for a basic monster.
    def take_turn(self, fov_map, player, map, objects):
        # a basic monster takes its turn. If you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):

            # move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y, map, objects)

            # close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player, objects, player)


class ConfusedMonster:
    # AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=g.CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns

    def take_turn(self, fov_map, player, map, objects):
        if self.num_turns > 0:  # still confused...
            # move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1), map, objects)
            self.num_turns -= 1

        else:  # restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            g.message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)


class Object:

    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None,
                 level=1):
        self.always_visible = always_visible
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:  # let the fighter component know who owns it
            self.fighter.owner = self
        self.ai = ai
        if self.ai:  # let the AI component know who owns it
            self.ai.owner = self
        self.item = item
        if self.item:  # let the Item component know who owns it
            self.item.owner = self
        self.level = level

    def distance(self, x, y):
        # return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self, objects):
        # make this object be drawn first, so all others appear above it if they're in the same tile.
        objects.remove(self)
        objects.insert(0, self)

    def move_towards(self, target_x, target_y, map, objects):
        # vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        # normalize it to length 1 (preserving direction), then round it and
        # convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy, map, objects)

    def move(self, dx, dy, map, objects):
        # move by the given amount, if the destination is not blocked
        if not is_blocked(self.x + dx, self.y + dy, map, objects):
            self.x += dx
            self.y += dy

    def draw(self, fov_map, tile_map, con):
        if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
                (self.always_visible and tile_map[self.x][self.y].explored)):
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self, con):
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

    def distance_to(self, other):
        # return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)


def is_blocked(x, y, map, objects):
    # first test the map tile
    if map[x][y].blocked:
        return True

    # now check for any blocking objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False


def monster_death(monster, objects):
    # transform it into a nasty corpse! it doesn't block, can't be
    # attacked and doesn't move
    g.message('The ' + monster.name + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.',
              libtcod.orange)
    g.message(monster.name.capitalize() + ' is dead!')
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back(objects)


def player_death(player, objects):
    # the game ended!
    g.message('You died!', libtcod.red)
    g.game_state = 'dead'

    # for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red


def create_orc(x, y):
    orc_fighter_component = Fighter(hp=10, defense=0, power=3, death_function=monster_death, xp=35)
    ai_component = BasicMonster()

    monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green,
                     blocks=True, fighter=orc_fighter_component, ai=ai_component)

    return monster


def create_troll(x, y):
    troll_fighter_component = Fighter(hp=16, defense=1, power=4, death_function=monster_death, xp=100)
    ai_component = BasicMonster()

    monster = Object(x, y, 'T', 'troll', libtcod.darker_green,
                     blocks=True, fighter=troll_fighter_component, ai=ai_component)

    return monster


def create_heal_potion(x, y, use_function):
    item_component = Item(use_function=use_function)
    item = Object(x, y, '!', 'healing potion', libtcod.violet, item=item_component)
    return item


def create_fireball_scroll(x, y, use_function):
    item_component = Item(use_function=use_function)
    item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component)
    return item


def create_lightning_scroll(x, y, use_function):
    item_component = Item(use_function=use_function)
    item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)
    return item


def create_confuse_scroll(x, y, use_function):
    item_component = Item(use_function=use_function)
    item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)
    return item
