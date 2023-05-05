import math
import random
import pygame
from pygame.math import Vector2
from utils import get_mask_rect
from utils import *
from PIL import Image
from object import Object
from particles import ParticleManager
from particles import EnemyHitParticle, WallHitParticle, StaffParticle
from player import Player



class WeaponSwing:
    left_swing = 10
    right_swing = -190
    image = ""

    def __init__(self, weapon):
        self.weapon = weapon
        self.angle = 0
        self.offset = Vector2(0, -50)
        self.offset_rotated = Vector2(0, -25)
        self.counter = 0
        self.swing_side = 1
        self.image = f'src/assets/objects/weapon/{weapon}/{weapon}.png'
        self.rect = weapon.rect

    def reset(self):
        self.counter = 0

    def rotate(self, weapon=None):
        mx, my = pygame.mouse.get_pos()
        dx = mx - self.weapon.player.hitbox.centerx  # - 64
        dy = my - self.weapon.player.hitbox.centery  # - 32
        if self.swing_side == 1:
            self.angle = (180 / math.pi) * math.atan2(-self.swing_side * dy, dx) + self.left_swing
        else:
            self.angle = (180 / math.pi) * math.atan2(self.swing_side * dy, dx) + self.right_swing

        position = self.weapon.player.hitbox.center
        if weapon:
            self.weapon.image = pygame.transform.rotozoom(self.weapon.image, self.angle, 1)
        else:
            self.weapon.image = pygame.transform.rotozoom(self.weapon.original_image, self.angle, 1)

        offset_rotated = self.offset.rotate(-self.angle)
        self.weapon.rect = self.weapon.image.get_rect(center=position + offset_rotated)
        self.weapon.hitbox = pygame.mask.from_surface(self.weapon.image)
        self.offset_rotated = Vector2(0, -35).rotate(-self.angle)

    def swing(self):
        self.angle += 20 * self.swing_side
        position = self.weapon.player.hitbox.center
        self.weapon.image = pygame.transform.rotozoom(self.weapon.original_image, self.angle, 1)
        offset_rotated = self.offset.rotate(-self.angle)
        self.weapon.rect = self.weapon.image.get_rect(center=position + offset_rotated)
        self.rect_mask = get_mask_rect(self.image, *self.rect.topleft)
        self.weapon.hitbox = pygame.mask.from_surface(self.weapon.image)
        self.counter += 1


class Weapon(Object):
    def __init__(self, game, name=None, size=None, room=None, position=None):
        self.scale = 3
        Object.__init__(self, game, name, 'weapon', size, room, position)
        self.size = size
        self.player = None
        self.load_image()
        if position:
            self.rect.x, self.rect.y = position[0], position[1]
        self.time = 0
        self.weapon_swing = WeaponSwing(self)
        self.starting_position = [self.hitbox.bottomleft[0] - 1, self.hitbox.bottomleft[1]]

    def load_image(self):
        """Load weapon image and initialize instance variables"""
        self.size = tuple(self.scale * x for x in Image.open(f'src/assets/objects/weapon/{self.name}/{self.name}.png').size)
        self.original_image = pygame.image.load(f'src/assets/objects/weapon/{self.name}/{self.name}.png').convert_alpha()
        self.original_image = pygame.transform.scale(self.original_image, self.size)
        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.hitbox = get_mask_rect(self.original_image, *self.rect.topleft)

    def detect_collision(self):
        if self.game.player.hitbox.colliderect(self.rect):
            self.interaction = True
        else:
            self.image = self.original_image
            self.interaction = False
            self.show_name.reset_line_length()

    def interact(self):
        self.weapon_swing.reset()
        self.player = self.game.player
        self.player.items.append(self)
        if not self.player.weapon:
            self.player.weapon = self
        if self.room == self.game.world_manager.current_room:
            self.room.objects.remove(self)
        self.interaction = False
        self.show_name.reset_line_length()

    def drop(self):
        self.game.sound_manager.play_drop_sound()
        self.room = self.game.world_manager.current_room
        self.player.items.remove(self)
        self.player.weapon = None
        self.game.world_manager.current_room.objects.append(self)
        if self.player.items:
            self.player.weapon = self.player.items[-1]
        self.load_image()
        self.rect = self.image.get_rect()
        self.hitbox = get_mask_rect(self.image, *self.rect.topleft)
        self.rect.x = self.player.rect.x
        self.rect.y = self.player.rect.y
        self.player = None
        self.weapon_swing.offset_rotated = Vector2(0, -25)

    def enemy_collision(self):
        for enemy in self.game.enemy_manager.enemy_list:
            if (
                    pygame.sprite.collide_mask(self.game.player.weapon, enemy)
                    and enemy.dead is False
                    and enemy.can_get_hurt_from_weapon()
            ):
                self.game.player.weapon.special_effect(enemy)
                enemy.hurt = True
                enemy.hp -= self.game.player.weapon.damage * self.game.player.strength
                enemy.entity_animation.hurt_timer = pygame.time.get_ticks()
                self.game.sound_manager.play_hit_sound()
                enemy.weapon_hurt_cooldown = pygame.time.get_ticks()

    def player_update(self):
        self.interaction = False
        if self.weapon_swing.counter == 10:
            self.original_image = pygame.transform.flip(self.original_image, 1, 0)
            self.player.attacking = False
            self.weapon_swing.counter = 0
        if self.player.attacking and self.weapon_swing.counter <= 10:
            self.weapon_swing.swing()
            self.enemy_collision()
        else:
            self.weapon_swing.rotate()

    def draw_shadow(self, surface):
        if self.dropped:
            self.shadow.set_shadow_position()
            self.shadow.draw_shadow(surface)
        else:
            if not self.shadow.shadow_set:
                self.shadow.set_shadow_position()
            if self.player:
                self.shadow.shadow_set = False
            if self.player is None:
                self.shadow.draw_shadow(surface)

    def update(self):
        self.hovering.hovering()
        if self.player:
            self.player_update()
        else:
            self.show_price.update()
            self.update_bounce()
        self.update_hitbox()

    def draw(self):
        surface = self.room.tile_map.map_surface
        if self.player:
            surface = self.game.screen
        surface.blit(self.image, self.rect)
        if self.interaction:
            self.show_name.draw(surface, self.rect)
        self.show_price.draw(surface)
        self.draw_shadow(surface)


class Shotgun(Weapon):
    name = 'shotgun'
    damage = 10
    size = (30, 96)

    def __init__(self, game, room=None, position=None):
        super().__init__(game, self.name, self.size, room, position)
        self.value = 150
        self.animation_frame = 0
        self.images = []
        self.load_images()
        self.firing_position = self.hitbox.topleft
        self.bullets = []
        self.shadow.set_correct(3)
        self.bullets = []

    def remove_bullets(self):
        for bullet in self.bullets:
            if self.game.world_manager.current_room is not bullet.room:
                self.bullets.remove(bullet)

    def add_bullet(self, bullet):
        self.bullets.append(bullet)

    def kill(self, bullet):
        self.bullets.remove(bullet)

    def update(self):
        self.remove_bullets()
        for bullet in self.bullets:
            bullet.update()

    def draw(self):
        for bullet in self.bullets:
            bullet.draw()

    def load_images(self):
        for i in range(4):
            image = pygame.image.load(f'src/assets/objects/weapon/{self.name}/{self.name}.png').convert_alpha()
            image = pygame.transform.scale(image, self.size)
            self.images.append(image)
        self.image = self.images[0]

    def calculate_firing_position(self):
        if 0 <= self.weapon_swing.angle < 90:
            self.firing_position = self.hitbox.topleft
        elif 90 <= self.weapon_swing.angle < 180:
            self.firing_position = (self.hitbox.bottomleft[0], self.hitbox.bottomleft[1] - 15)
        elif 0 > self.weapon_swing.angle > -90:
            self.firing_position = self.hitbox.topright
        else:
            self.firing_position = (self.hitbox.bottomright[0], self.hitbox.bottomright[1] - 15)

    def fire(self):
        pos = pygame.mouse.get_pos()
        self.update_hitbox()
        self.calculate_firing_position()
        self.add_bullet(ShotgunBullet(self.game, self, self.game.world_manager.current_room, self.firing_position[0], self.firing_position[1] - 15, pos))
        self.calculate_firing_position()
        self.add_bullet(ShotgunBullet(self.game, self, self.game.world_manager.current_room, self.firing_position[0],self.firing_position[1], pos))
        self.calculate_firing_position()
        self.add_bullet(ShotgunBullet(self.game, self, self.game.world_manager.current_room, self.firing_position[0],self.firing_position[1] + 15, pos))

    def player_update(self):
        self.interaction = False
        self.weapon_swing.rotate(self)
        if self.player.attacking:
            self.fire()
            self.player.attacking = False

    def animate(self):
        self.animation_frame += 1.5 / 15
        if self.animation_frame > 4:
            self.animation_frame = 0
        self.image = self.images[int(self.animation_frame)]

    def update(self):
        self.hovering.hovering()
        self.animate()
        if self.player:
            self.player_update()
        else:
            self.show_price.update()
            self.update_bounce()
        self.update_hitbox()

    def draw(self):
        surface = self.room.tile_map.map_surface
        if self.player:
            surface = self.game.screen
        surface.blit(self.image, self.rect)
        if self.interaction:
            self.show_name.draw(surface, self.rect)
        self.show_price.draw(surface)
        self.draw_shadow(surface)


class Revolver(Weapon):
    name = 'revolver'
    damage = 40
    size = (36, 90)


    def __init__(self, game, room=None, position=None):
        super().__init__(game, self.name, self.size, room, position)
        self.value = 100
        self.damage_enemies = []
        self.shadow.set_correct(-3)
        self.bullets = []

    def remove_bullets(self):
        for bullet in self.bullets:
            if self.game.world_manager.current_room is not bullet.room:
                self.bullets.remove(bullet)

    def add_bullet(self, bullet):
        self.bullets.append(bullet)

    def kill(self, bullet):
        self.bullets.remove(bullet)

    def update(self):
        self.remove_bullets()
        for bullet in self.bullets:
            bullet.update()

    def draw(self):
        for bullet in self.bullets:
            bullet.draw()

    def calculate_firing_position(self):
        if 0 <= self.weapon_swing.angle < 90:
            self.firing_position = self.hitbox.topleft
        elif 90 <= self.weapon_swing.angle < 180:
            self.firing_position = (self.hitbox.bottomleft[0], self.hitbox.bottomleft[1])
        elif 0 > self.weapon_swing.angle > -90:
            self.firing_position = self.hitbox.topright
        else:
            self.firing_position = (self.hitbox.bottomright[0], self.hitbox.bottomright[1])

    def fire(self):
        pos = pygame.mouse.get_pos()
        self.update_hitbox()
        self.calculate_firing_position()
        self.game.bullet_manager.add_bullet(RevolverBullet(self.game, self, self.game.world_manager.current_room, self.firing_position[0], self.firing_position[1], pos))

    def enemy_in_list(self, enemy):
        for e in self.damage_enemies:
            if e.enemy is enemy:
                return True

    def special_effect(self, enemy):
        for e in self.damage_enemies:
            if e.enemy is enemy:
                e.update()
        if not self.enemy_in_list(enemy):
            self.damage_enemies.append(self.Slash(enemy, self))

    def player_update(self):
        self.interaction = False
        if self.weapon_swing.counter == 10:
            self.original_image = pygame.transform.flip(self.original_image, 1, 0)
            self.player.attacking = False
            self.weapon_swing.counter = 0
            self.game.screen_position = (0, 0)
        if self.player.attacking and self.weapon_swing.counter <= 10:
            self.enemy_collision()

        else:
            self.weapon_swing.rotate()


class DestroyerCannon(Weapon):
    name = 'destroyercannon'
    damage = 30
    size = (36, 90)

    def __init__(self, game, room=None, position=None):
        super().__init__(game, self.name, self.size, room, position)
        self.value = 150

    def player_update(self):
        self.interaction = False
        if self.weapon_swing.counter == 10:
            self.original_image = pygame.transform.flip(self.original_image, 1, 0)
            self.player.attacking = False
            self.weapon_swing.counter = 0
        if self.player.attacking and self.weapon_swing.counter <= 10:
            self.weapon_swing.swing()
            self.enemy_collision()
            self.game.sound_manager.play_sword_sound('fire')
        else:
            self.weapon_swing.rotate()

    def update(self):
        self.hovering.hovering()
        if self.player:
            self.player_update()
        else:
            self.show_price.update()
            self.update_bounce()
        self.update_hitbox()

class Katana(Weapon):
    name = 'katana'
    damage = 30
    size = (36, 90)

    def __init__(self, game, room=None, position=None):
        super().__init__(game, self.name, self.size, room, position)
        self.value = 150

    def player_update(self):
        self.interaction = False
        if self.weapon_swing.counter == 10:
            self.original_image = pygame.transform.flip(self.original_image, 1, 0)
            self.player.attacking = False
            self.weapon_swing.counter = 0
        if self.player.attacking and self.weapon_swing.counter <= 10:
            self.weapon_swing.swing()
            self.enemy_collision()
            self.game.sound_manager.play_sword_sound('fire')
        else:
            self.weapon_swing.rotate()

    def update(self):
        self.hovering.hovering()
        if self.player:
            self.player_update()
        else:
            self.show_price.update()
            self.update_bounce()
        self.update_hitbox()

class Armyknife(Weapon):
    name = 'armyknife'
    damage = 30
    size = (36, 90)

    def __init__(self, game, room=None, position=None):
        super().__init__(game, self.name, self.size, room, position)
        self.value = 150

    def player_update(self):
        self.interaction = False
        if self.weapon_swing.counter == 10:
            self.original_image = pygame.transform.flip(self.original_image, 1, 0)
            self.player.attacking = False
            self.weapon_swing.counter = 0
        if self.player.attacking and self.weapon_swing.counter <= 10:
            self.weapon_swing.swing()
            self.enemy_collision()
            self.game.sound_manager.play_sword_sound('fire')
        else:
            self.weapon_swing.rotate()

    def update(self):
        self.hovering.hovering()
        if self.player:
            self.player_update()
        else:
            self.show_price.update()
            self.update_bounce()
        self.update_hitbox()

class Bow(Weapon):
    name = 'bow'
    damage = 30
    size = (36, 90)

    def __init__(self, game, room=None, position=None):
        super().__init__(game, self.name, self.size, room, position)
        self.value = 150

    def player_update(self):
        self.interaction = False
        if self.weapon_swing.counter == 10:
            self.original_image = pygame.transform.flip(self.original_image, 1, 0)
            self.player.attacking = False
            self.weapon_swing.counter = 0
        if self.player.attacking and self.weapon_swing.counter <= 10:
            self.weapon_swing.swing()
            self.enemy_collision()
            self.game.sound_manager.play_sword_sound('fire')
        else:
            self.weapon_swing.rotate()

    def update(self):
        self.hovering.hovering()
        if self.player:
            self.player_update()
        else:
            self.show_price.update()
            self.update_bounce()
        self.update_hitbox()

class Bullet():
    def __init__(self, game, master, room, x, y, target):
        super().__init__()
        self.game = game
        self.player = Player
        self.master = master
        self.room = room
        self.image = None
        self.rect = None
        self.load_image()
        self.rect.x = x
        self.rect.y = y
        self.pos = (x, y)
        self.dir = pygame.math.Vector2(target[0] - x, target[1] - y)
        self.calculate_dir(self.player)
        self.bounce_back = True

    def calculate_dir(self, player):
        if 0 <= self.weapon_swing.angle < 90:
            self.firing_position = self.hitbox.topleft
        elif 90 <= self.weapon_swing.angle < 180:
            self.firing_position = (self.hitbox.bottomleft[0], self.hitbox.bottomleft[1])
        elif 0 > self.weapon_swing.angle > -90:
            self.firing_position = self.hitbox.topright
        else:
            self.firing_position = (self.hitbox.bottomright[0], self.hitbox.bottomright[1])

    def set_damage(self, value):
        self.damage = value

    def load_image(self):
        self.image = pygame.Surface([self.bullet_size, self.bullet_size])
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect()

    def update_position(self):
        if self.room == self.game.world_manager.current_room:
            self.pos = (self.pos[0] + self.dir[0] * self.speed, self.pos[1] + self.dir[1] * self.speed)
            self.rect.x = self.pos[0]  #
            self.rect.y = self.pos[1]  #

    def kill(self):
        if self in self.game.bullet_manager.bullets:
            self.game.bullet_manager.bullets.remove(self)
        self.game.sound_manager.play(pygame.mixer.Sound('assets/sound/Impact5.wav'))

    def update(self):
        self.update_position()
        if self.bounce_back is False:
            for enemy in self.game.enemy_manager.enemy_list:
                if self.rect.colliderect(enemy.hitbox):
                    enemy.hp -= self.damage
                    self.game.particle_manager.particle_list.append(EnemyHitParticle(self.game, self.rect.x, self.rect.y))
                    self.kill()
                    break
        self.player_collision(self.game.player)
        self.bounce()
        if self.rect.y < 0 or self.rect.y > 1000 or self.rect.x < 0 or self.rect.x > 1300:
            self.kill()
        self.wall_collision()

    def draw(self):
        surface = self.master.room.tile_map.map_surface
        pygame.draw.circle(surface, (255, 255, 255), (self.rect.x + self.radius / 2, self.rect.y + self.radius / 2),self.radius)
        pygame.draw.circle(surface, (58, 189, 74), (self.rect.x + self.radius / 2, self.rect.y + self.radius / 2),self.radius - 1)

    def wall_collision(self):
        collide_points = (self.rect.midbottom, self.rect.bottomleft, self.rect.bottomright)
        for wall in self.game.world_manager.current_map.wall_list:
            if any(wall.hitbox.collidepoint(point) for point in collide_points):
                self.game.particle_manager.add_particle(WallHitParticle(self.game, self.rect.x, self.rect.y))
                self.kill()
                break

    def player_collision(self, collision_enemy):
        if self.rect.colliderect(collision_enemy.hitbox) and not self.game.world_manager.switch_room:
            if collision_enemy.shield:
                collision_enemy.shield -= 1
            else:
                self.game.player.hp -= self.damage
                self.game.player.hurt = True
                self.game.player.entity_animation.hurt_timer = pygame.time.get_ticks()
            self.sparkle()
            self.kill()

    def sparkle(self):
        for _ in range(random.randint(2, 4)):
            self.game.particle_manager.particle_list.append(EnemyHitParticle(self.game, self.rect.x, self.rect.y))

    def bounce(self):
        if (
                self.game.player.weapon
                and self.game.player.attacking
                and pygame.sprite.collide_mask(self.game.player.weapon, self)
                and self.bounce_back
        ):
            self.dir = (-self.dir[0] + random.randint(-20, 10) / 100, -self.dir[1] + random.randint(-10, 10) / 100)
            self.speed *= random.randint(10, 20) / 10
            self.bounce_back = False
            self.game.sound_manager.play(pygame.mixer.Sound('assets/sound/Hit.wav'))


class ImpBullet(Bullet):
    speed = 5
    bullet_size = 7
    radius = 5

    def __init__(self, game, master, room, x, y, target):
        super().__init__(game, master, room, x, y, target)
        self.damage = master.damage


class ShotgunBullet(Bullet):
    speed = 9
    bullet_size = 12
    radius = 7

    def __init__(self, game, master, room, x, y, target):
        super().__init__(game, master, room, x, y, target)
        self.damage = 25 * self.game.player.strength
        self.bounce_back = False
        self.weapon = objects.weapon.Shotgun

    def hit_enemy(self):
        for enemy in self.game.enemy_manager.enemy_list:
            if self.rect.colliderect(enemy.hitbox) and enemy.can_get_hurt_from_weapon():
                enemy.hp -= self.damage
                enemy.entity_animation.hurt_timer = pygame.time.get_ticks()
                enemy.hurt = True
                enemy.weapon_hurt_cooldown = pygame.time.get_ticks()
                self.game.particle_manager.particle_list.append(EnemyHitParticle(self.game, self.rect.x, self.rect.y))
                self.kill()

    def update(self):
        self.wall_collision()
        self.update_position()
        self.hit_enemy()
        if self.rect.y < 0 or self.rect.y > 1000 or self.rect.x < 0 or self.rect.x > 1400:
            self.kill()

    def draw(self):
        # surface = self.game.world_manager.current_map.map_surface
        surface = self.room.tile_map.map_surface
        self.load_image(f'src/assets/objects/weapon/shotgunbullet/shotgunbullet.png').convert_alpha


class DestroyerBullet(Bullet):
    bullet_size = 12
    radius = 7

    def __init__(self, game, master, room, x, y, target):
        super().__init__(game, master, room, x, y, target)
        self.calculate_dir()
        self.damage = 25 * self.game.player.strength
        self.bounce_back = False

    def hit_enemy(self):
        for enemy in self.game.enemy_manager.enemy_list:
            if self.rect.colliderect(enemy.hitbox) and enemy.can_get_hurt_from_weapon():
                enemy.hp -= self.damage
                enemy.entity_animation.hurt_timer = pygame.time.get_ticks()
                enemy.hurt = True
                enemy.weapon_hurt_cooldown = pygame.time.get_ticks()
                self.game.particle_manager.particle_list.append(EnemyHitParticle(self.game, self.rect.x, self.rect.y))
                self.kill()

    def update(self):
        self.wall_collision()
        self.hit_enemy()
        if self.rect.y < 0 or self.rect.y > 1000 or self.rect.x < 0 or self.rect.x > 1400:
            self.kill()

class RevolverBullet(Bullet):
    bullet_size = 12
    radius = 7

    def __init__(self, game, master, room, x, y, target):
        super().__init__(game, master, room, x, y, target)
        self.damage = 25 * self.game.player.strength
        self.bounce_back = False

    def hit_enemy(self):
        for enemy in self.game.enemy_manager.enemy_list:
            if self.rect.colliderect(enemy.hitbox) and enemy.can_get_hurt_from_weapon():
                enemy.hp -= self.damage
                enemy.entity_animation.hurt_timer = pygame.time.get_ticks()
                enemy.hurt = True
                enemy.weapon_hurt_cooldown = pygame.time.get_ticks()
                self.game.particle_manager.particle_list.append(EnemyHitParticle(self.game, self.rect.x, self.rect.y))
                self.kill()

    def update(self):
        self.wall_collision()
        self.hit_enemy()
        if self.rect.y < 0 or self.rect.y > 1000 or self.rect.x < 0 or self.rect.x > 1400:
            self.kill()

    def draw(self):
        # surface = self.game.world_manager.current_map.map_surface
        surface = self.room.tile_map.map_surface
        self.load_image(f'src/assets/objects/weapon/shotgunbullet/revolverbullet.png').convert_alpha


class BossBullet(Bullet):
    speed = 7
    bullet_size = 7
    radius = 5

    def __init__(self, game, master, room, x, y, target, rotation=None):
        super().__init__(game, master, room, x, y, target)
        if rotation:
            self.dir.rotate_ip(rotation)
        self.damage = master.bullet_damage

    def kill(self):
        if self in self.game.bullet_manager.bullets:
            self.game.bullet_manager.bullets.remove(self)


class MachineGunBullet(BossBullet):

    def __init__(self, game, master, room, x, y, target, rotation=None):
        super().__init__(game, master, room, x, y, target)

    def update(self):
        self.update_position()
        self.player_collision(self.game.player)
        if self.rect.y < 0 or self.rect.y > 1000 or self.rect.x < 0 or self.rect.x > 1300:
            self.kill()
        self.wall_collision()


class BulletManager:

    def __init__(self, game):
        self.game = game
        self.bullets = []

    def remove_bullets(self):
        for bullet in self.bullets:
            if self.game.world_manager.current_room is not bullet.room:
                self.bullets.remove(bullet)
                #self.kill(bullet)

    def add_bullet(self, bullet):
        self.bullets.append(bullet)

    def kill(self, bullet):
        self.bullets.remove(bullet)

    def update(self):
        self.remove_bullets()
        for bullet in self.bullets:
            bullet.update()

    def draw(self):
        for bullet in self.bullets:
            bullet.draw()