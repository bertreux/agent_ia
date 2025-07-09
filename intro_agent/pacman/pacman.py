import pygame
import sys
import random

# Initialisation de Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 20
GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // GRID_SIZE
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Création de la fenêtre
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pacman")
clock = pygame.time.Clock()

# Classe Pacman
class Pacman:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.direction = (0, 0)
        self.next_direction = (0, 0)
        self.score = 0

    def move(self):
        # Mise à jour de la direction actuelle
        self.direction = self.next_direction

        # Calcul de la nouvelle position
        new_x = self.x + self.direction[0]
        new_y = self.y + self.direction[1]

        # Vérification des limites du labyrinthe
        if 0 <= new_x < GRID_WIDTH and 0 <= new_y < GRID_HEIGHT:
            self.x = new_x
            self.y = new_y

    def draw(self):
        pygame.draw.circle(screen, YELLOW, (self.x * GRID_SIZE + GRID_SIZE // 2, self.y * GRID_SIZE + GRID_SIZE // 2), GRID_SIZE // 2)

# Classe Fantôme
class Ghost:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.direction = (random.choice([-1, 1]), random.choice([-1, 1]))

    def move(self):
        # Calcul de la nouvelle position
        new_x = self.x + self.direction[0]
        new_y = self.y + self.direction[1]

        # Vérification des limites du labyrinthe
        if 0 <= new_x < GRID_WIDTH and 0 <= new_y < GRID_HEIGHT:
            self.x = new_x
            self.y = new_y
        else:
            self.direction = (-self.direction[0], -self.direction[1])

    def draw(self):
        pygame.draw.circle(screen, RED, (self.x * GRID_SIZE + GRID_SIZE // 2, self.y * GRID_SIZE + GRID_SIZE // 2), GRID_SIZE // 2)

# Classe Boule
class Dot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.eaten = False

    def draw(self):
        if not self.eaten:
            pygame.draw.circle(screen, WHITE, (self.x * GRID_SIZE + GRID_SIZE // 2, self.y * GRID_SIZE + GRID_SIZE // 2), GRID_SIZE // 4)

# Création du labyrinthe
maze = [[1 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

# Placement des murs (1) et des chemins (0)
for i in range(GRID_HEIGHT):
    for j in range(GRID_WIDTH):
        if i % 2 == 0 or j % 2 == 0:
            maze[i][j] = 1
        else:
            maze[i][j] = 0

# Création des boules
dots = []
for i in range(GRID_HEIGHT):
    for j in range(GRID_WIDTH):
        if maze[i][j] == 0:
            dots.append(Dot(j, i))

# Création de Pacman
pacman = Pacman(1, 1)

# Création des fantômes
ghosts = [Ghost(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)) for _ in range(3)]

# Boucle principale du jeu
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                pacman.next_direction = (0, -1)
            elif event.key == pygame.K_DOWN:
                pacman.next_direction = (0, 1)
            elif event.key == pygame.K_LEFT:
                pacman.next_direction = (-1, 0)
            elif event.key == pygame.K_RIGHT:
                pacman.next_direction = (1, 0)

    # Déplacement de Pacman
    pacman.move()

    # Déplacement des fantômes
    for ghost in ghosts:
        ghost.move()

    # Vérification des collisions avec les boules
    for dot in dots:
        if not dot.eaten and pacman.x == dot.x and pacman.y == dot.y:
            dot.eaten = True
            pacman.score += 10

    # Vérification des collisions avec les fantômes
    for ghost in ghosts:
        if pacman.x == ghost.x and pacman.y == ghost.y:
            print("Game Over!")
            running = False

    # Dessin du labyrinthe
    screen.fill(BLACK)
    for i in range(GRID_HEIGHT):
        for j in range(GRID_WIDTH):
            if maze[i][j] == 1:
                pygame.draw.rect(screen, BLUE, (j * GRID_SIZE, i * GRID_SIZE, GRID_SIZE, GRID_SIZE))

    # Dessin des boules
    for dot in dots:
        dot.draw()

    # Dessin de Pacman
    pacman.draw()

    # Dessin des fantômes
    for ghost in ghosts:
        ghost.draw()

    # Affichage du score
    font = pygame.font.SysFont(None, 36)
    score_text = font.render(f"Score: {pacman.score}", True, WHITE)
    screen.blit(score_text, (10, 10))

    pygame.display.flip()
    clock.tick(10)

pygame.quit()
