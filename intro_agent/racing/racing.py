import pygame
import random
import sys

# Initialisation de Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Classe pour le joueur
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 80))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.speed = 0
        self.max_speed = 10
        self.acceleration = 0.2
        self.deceleration = 0.1

    def update(self):
        # Gestion de l'accélération et de la décélération
        if self.speed < 0:
            self.speed = 0
        if self.speed > self.max_speed:
            self.speed = self.max_speed

        # Mise à jour de la position
        self.rect.x += self.speed

        # Limites de l'écran
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def accelerate(self):
        self.speed += self.acceleration

    def decelerate(self):
        self.speed -= self.deceleration

# Classe pour les obstacles
class Obstacle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((100, 50))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randint(-100, -40)
        self.speed = random.randint(3, 8)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
            self.rect.y = random.randint(-100, -40)
            self.speed = random.randint(3, 8)

# Classe pour le jeu
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Racing Game")
        self.clock = pygame.time.Clock()
        self.running = True
        self.player = Player()
        self.all_sprites = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.all_sprites.add(self.player)

        # Création des obstacles initiaux
        for i in range(5):
            obstacle = Obstacle()
            self.obstacles.add(obstacle)
            self.all_sprites.add(obstacle)

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self.events()
            self.update()
            self.draw()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.player.rect.x -= 5
        if keys[pygame.K_RIGHT]:
            self.player.rect.x += 5
        if keys[pygame.K_UP]:
            self.player.accelerate()
        if keys[pygame.K_DOWN]:
            self.player.decelerate()

    def update(self):
        self.all_sprites.update()

        # Vérification des collisions
        if pygame.sprite.spritecollide(self.player, self.obstacles, False):
            self.running = False

    def draw(self):
        self.screen.fill(BLACK)
        self.all_sprites.draw(self.screen)
        pygame.display.flip()

# Point d'entrée du programme
if __name__ == "__main__":
    game = Game()
    game.run()
    pygame.quit()
    sys.exit()