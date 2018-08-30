import libtcodpy as libtcod
import math


class Fighter:
    # combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, death_function=None):
        self.death_function = death_function
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power

    def take_damage(self, damage, objects):
        # apply damage if possible
        if damage > 0:
            self.hp -= damage
            # check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner, objects)

    def attack(self, target, objects):
        # a simple formula for attack damage
        damage = self.power - target.fighter.defense

        if damage > 0:
            # make the target take some damage
            print(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage, objects)
        else:
            print(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')


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
                monster.fighter.attack(player, objects)


class Object:

    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None):
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

    def draw(self, fov_map, con):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
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
    print(monster.name.capitalize() + ' is dead!')
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back(objects)