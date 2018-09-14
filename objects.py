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
        # special case: automatically equip, if the corresponding equipment slot is unused
        equipment = self.owner.equipment
        if equipment and get_equipped_in_slot(equipment.slot, g.inventory) is None:
            equipment.equip()

    def use(self):
        # special case: if the object has the Equipment component, the "use" action is to equip/dequip
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return
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
        # special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip()
        g.message('You dropped a ' + self.owner.name + '.', libtcod.yellow)


class Fighter:
    # combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, death_function=None):
        self.base_power = power
        self.base_max_hp = hp
        self.base_defense = defense
        self.xp = xp
        self.death_function = death_function
        self.hp = hp

    # @property
    def power(self, player):
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner, player))
        return self.base_power + bonus

    # @property
    def defense(self, player):  # return actual defense, by summing up the bonuses from all equipped items
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner, player))
        return self.base_defense + bonus

    # @property
    def max_hp(self, player):  # return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner, player))
        return self.base_max_hp + bonus

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

    def heal(self, amount, player):
        # heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp(player):
            self.hp = self.max_hp(player)

    def attack(self, target, objects, player):
        # a simple formula for attack damage
        damage = self.power(player) - target.fighter.defense(player)

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


class Equipment:
    # an object that can be equipped, yielding bonuses. automatically adds the Item component.
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus
        self.slot = slot
        self.is_equipped = False

    def toggle_equip(self):  # toggle equip/dequip status
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self):
        # if the slot is already being used, dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot, g.inventory)
        if old_equipment is not None:
            old_equipment.dequip()
        # equip object and show a message about it
        self.is_equipped = True
        g.message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)

    def dequip(self):
        # dequip object and show a message about it
        if not self.is_equipped: return
        self.is_equipped = False
        g.message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)


class Object:

    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None,
                 level=1, equipment=None):
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
        self.equipment = equipment
        if self.equipment:
            self.equipment.owner = self
            self.item = Item()
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


def get_equipped_in_slot(slot, inventory):
    # returns the equipment in a slot, or None if it's empty
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None


def get_all_equipped(obj, player):  # returns a list of equipped items
    if obj == player:
        equipped_list = []
        for item in g.inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list
    else:
        return []  # other objects have no equipment


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


def place_sword(x, y, use_function=None):
    # create a sword
    equipment_component = Equipment(slot='right hand')
    item = Object(x, y, '/', 'sword', libtcod.sky, equipment=equipment_component)
    return item


def place_shield(x, y, use_function=None):
    # create a shield
    equipment_component = Equipment(slot='left hand', defense_bonus=1)
    item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
    return item
