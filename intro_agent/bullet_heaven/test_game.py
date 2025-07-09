import unittest
import pygame
from game import Player, Enemy, ExpGem, WaveManager

class TestGame(unittest.TestCase):
    def setUp(self):
        pygame.init()

    def test_player_initialization(self):
        player = Player(100, 100)
        self.assertEqual(player.x, 100)
        self.assertEqual(player.y, 100)
        self.assertEqual(player.radius, 20)
        self.assertEqual(player.level, 1)

    def test_player_move(self):
        player = Player(100, 100)
        player.move(1, 0)
        self.assertEqual(player.x, 105)
        player.move(-1, 0)
        self.assertEqual(player.x, 100)

    def test_enemy_initialization(self):
        enemy = Enemy(200, 200)
        self.assertEqual(enemy.x, 200)
        self.assertEqual(enemy.y, 200)
        self.assertEqual(enemy.radius, 15)

    def test_exp_gem_initialization(self):
        gem = ExpGem(300, 300)
        self.assertEqual(gem.x, 300)
        self.assertEqual(gem.y, 300)
        self.assertEqual(gem.value, 10)

    def test_wave_manager_initialization(self):
        wave_manager = WaveManager()
        self.assertEqual(wave_manager.current_wave, 0)
        self.assertEqual(wave_manager.enemies_per_wave, 5)

    def tearDown(self):
        pygame.quit()

if __name__ == '__main__':
    unittest.main()