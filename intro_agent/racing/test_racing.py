import unittest
import pygame
from racing import Player, Obstacle

class TestRacingGame(unittest.TestCase):
    def setUp(self):
        pygame.init()

    def test_player_initialization(self):
        player = Player()
        self.assertEqual(player.rect.center, (400, 500))
        self.assertEqual(player.speed, 0)
        self.assertEqual(player.max_speed, 10)

    def test_player_acceleration(self):
        player = Player()
        initial_speed = player.speed
        player.accelerate()
        self.assertEqual(player.speed, initial_speed + 0.2)

    def test_player_deceleration(self):
        player = Player()
        player.speed = 5
        initial_speed = player.speed
        player.decelerate()
        self.assertEqual(player.speed, initial_speed - 0.1)

    def test_obstacle_initialization(self):
        obstacle = Obstacle()
        self.assertTrue(0 <= obstacle.rect.x <= 700)
        self.assertTrue(-100 <= obstacle.rect.y <= -40)
        self.assertTrue(3 <= obstacle.speed <= 8)

    def tearDown(self):
        pygame.quit()

if __name__ == '__main__':
    unittest.main()