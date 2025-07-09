import pygame
import sys
import random

# Initialisation de Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_WIDTH = 50
PLAYER_HEIGHT = 50
OBSTACLE_WIDTH = 50
OBSTACLE_HEIGHT = 50
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Création de l'écran
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Jeu d'évitement")
clock = pygame.time.Clock()

# Classe du joueur
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)
        self.speed = 5

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < SCREEN_WIDTH:
            self.rect.x += self.speed

# Classe des obstacles
class Obstacle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((OBSTACLE_WIDTH, OBSTACLE_HEIGHT))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - OBSTACLE_WIDTH)
        self.rect.y = random.randint(-100, -40)
        self.speed = random.randint(3, 7)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.rect.x = random.randint(0, SCREEN_WIDTH - OBSTACLE_WIDTH)
            self.rect.y = random.randint(-100, -40)
            self.speed = random.randint(3, 7)

# Fonction pour afficher l'écran de démarrage
def show_start_screen():
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 72)
    text = font.render("Jeu d'évitement", True, WHITE)
    text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
    screen.blit(text, text_rect)
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False

# Fonction pour afficher l'écran de fin
def show_end_screen(score):
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 72)
    text = font.render(f"Game Over! Score: {score}", True, WHITE)
    text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
    screen.blit(text, text_rect)
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False
                    return True
                if event.key == pygame.K_ESCAPE:
                    waiting = False
                    return False
    return False

# Fonction principale du jeu
def main():
    # Création des sprites
    all_sprites = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    player = Player()
    all_sprites.add(player)

    # Boucle principale du jeu
    running = True
    score = 0
    obstacle_timer = 0
    while running:
        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Mise à jour
        all_sprites.update()
        obstacles.update()

        # Génération des obstacles
        obstacle_timer += 1
        if obstacle_timer > 60:
            obstacle = Obstacle()
            obstacles.add(obstacle)
            all_sprites.add(obstacle)
            obstacle_timer = 0

        # Vérification des collisions
        if pygame.sprite.spritecollide(player, obstacles, False):
            running = False

        # Incrémentation du score
        score += 1

        # Dessin
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # Affichage du score
        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    # Affichage de l'écran de fin
    if show_end_screen(score):
        main()

# Démarrage du jeu
show_start_screen()
main()
pygame.quit()
