import pygame


from menu import MainMenu
from mini_map import MiniMap
from particles import ParticleManager
from background import BackgroundEffects
from world_manager import WorldManager
from object_manager import ObjectManager
from enemy_manager import EnemyManager
from game_over import GameOver
from player import Player
import time
pygame.init()
pygame.mixer.init()

world_size = (21 * 64, 14 * 64)



class Game:
    def __init__(self):
        self.display = pygame.display.set_mode(world_size)
        self.screen = pygame.Surface(world_size).convert()
        self.clock = pygame.time.Clock()
        self.particle_manager = ParticleManager(self)
        self.world_manager = WorldManager(self)
        self.enemy_manager = EnemyManager(self)
        self.object_manager = ObjectManager(self)
        self.player = Player(self)
        self.running = True
        self.menu = MainMenu(self)
        self.mini_map = MiniMap(self)
        self.game_time = None
        self.fps = 60
        self.background = BackgroundEffects()
        self.game_over = GameOver(self)
        pygame.mixer.init()
        self.dt = 0
        self.screen_position = (0, 0)

    def refresh(self):
        pygame.mixer.Sound.stop(self.sound)
        self.__init__()
        pygame.display.flip()
        self.run_game()

    def update_groups(self):
        self.enemy_manager.update_enemies()
        self.object_manager.update()
        self.player.update()
        self.particle_manager.update_particles()
        self.particle_manager.update_fire_particles()
        self.background.update()
        self.world_manager.update()
        self.game_over.update()
        self.mini_map.update()

    def draw_groups(self):
        self.background.draw(self.screen)
        self.world_manager.draw_map(self.screen)
        if self.player:
            self.player.draw(self.screen)
        self.enemy_manager.draw_enemies(self.screen)
        self.object_manager.draw()
        self.mini_map.draw(self.screen)
        self.particle_manager.draw_particles(self.world_manager.current_map.map_surface)
        self.particle_manager.draw_fire_particles()
        self.game_over.draw()

    def input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
            if event.type == pygame.USEREVENT:
                self.object_manager.up += 1
                self.object_manager.hover = True

        self.player.input()
        pressed = pygame.key.get_pressed()
        # if pressed[pygame.K_r]:
        #     self.refresh()

        if pressed[pygame.K_ESCAPE]:
            if self.game_over.game_over:
                self.refresh()
            self.menu.running = True
            self.menu.play_button.clicked = False

    def run_game(self):
        self.enemy_manager.add_enemies()
        prev_time = time.time()
        while self.running:
            self.clock.tick(self.fps)
            now = time.time()
            self.dt = now - prev_time
            prev_time = now
            self.menu.show()
            self.screen.fill((0, 0, 0))
            self.input()
            self.update_groups()
            self.draw_groups()
            self.game_time = pygame.time.get_ticks()
            self.display.blit(self.screen, self.screen_position)
            if self.running:
                pygame.display.flip()
        pygame.quit()