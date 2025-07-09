import pygame
import random
import math
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
YELLOW = (255, 255, 0)

# Classe pour le joueur
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 20
        self.speed = 5
        self.level = 1
        self.exp = 0
        self.exp_to_level = 100
        self.health = 100
        self.max_health = 100
        self.damage = 10
        self.attack_speed = 0.5
        self.attack_cooldown = 0
        self.color = BLUE

    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = max(self.radius, min(self.x, SCREEN_WIDTH - self.radius))
        self.y = max(self.radius, min(self.y, SCREEN_HEIGHT - self.radius))

    def attack(self, enemies):
        if self.attack_cooldown <= 0:
            for enemy in enemies:
                distance = math.sqrt((self.x - enemy.x) ** 2 + (self.y - enemy.y) ** 2)
                if distance < 100:
                    enemy.health -= self.damage
            self.attack_cooldown = self.attack_speed
        else:
            self.attack_cooldown -= 1 / FPS

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_to_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_level
        self.exp_to_level = int(self.exp_to_level * 1.5)
        self.max_health += 20
        self.health = self.max_health
        self.damage += 5

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)
        # Barre de vie
        pygame.draw.rect(screen, RED, (self.x - self.radius, self.y - self.radius - 10, self.radius * 2, 5))
        pygame.draw.rect(screen, GREEN, (self.x - self.radius, self.y - self.radius - 10, self.radius * 2 * (self.health / self.max_health), 5))

# Classe pour les ennemis
class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 15
        self.speed = 2
        self.health = 30
        self.max_health = 30
        self.damage = 5
        self.color = RED

    def move_towards_player(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        if distance > 0:
            dx /= distance
            dy /= distance
        self.x += dx * self.speed
        self.y += dy * self.speed

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 1)
        # Barre de vie
        pygame.draw.rect(screen, RED, (self.x - self.radius, self.y - self.radius - 5, self.radius * 2, 3))
        pygame.draw.rect(screen, GREEN, (self.x - self.radius, self.y - self.radius - 5, self.radius * 2 * (self.health / self.max_health), 3))

# Classe pour les gemmes d'expérience
class ExpGem:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.value = 10
        self.color = YELLOW

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

# Classe pour gérer les vagues d'ennemis
class WaveManager:
    def __init__(self):
        self.current_wave = 0
        self.enemies_per_wave = 5
        self.enemies_remaining = 0
        self.wave_cooldown = 0
        self.wave_duration = 10

    def start_wave(self):
        self.current_wave += 1
        self.enemies_remaining = self.enemies_per_wave + self.current_wave * 2
        self.enemies_per_wave += 1

    def spawn_enemy(self):
        if self.enemies_remaining > 0:
            side = random.randint(0, 3)
            if side == 0:  # Haut
                x = random.randint(0, SCREEN_WIDTH)
                y = -20
            elif side == 1:  # Bas
                x = random.randint(0, SCREEN_WIDTH)
                y = SCREEN_HEIGHT + 20
            elif side == 2:  # Gauche
                x = -20
                y = random.randint(0, SCREEN_HEIGHT)
            else:  # Droite
                x = SCREEN_WIDTH + 20
                y = random.randint(0, SCREEN_HEIGHT)
            self.enemies_remaining -= 1
            return Enemy(x, y)
        return None

    def update(self, dt):
        if self.wave_cooldown > 0:
            self.wave_cooldown -= dt
        else:
            if self.enemies_remaining <= 0:
                self.start_wave()
                self.wave_cooldown = self.wave_duration

# Classe pour gérer l'état du jeu
class GameState:
    def __init__(self):
        self.score = 0
        self.game_over = False
        self.paused = False
        self.show_start_screen = True
        self.show_end_screen = False

# Fonction pour dessiner du texte
def draw_text(screen, text, size, x, y, color=WHITE):
    font = pygame.font.SysFont(None, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    screen.blit(text_surface, text_rect)

# Fonction principale du jeu
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Bullet Heaven")
    clock = pygame.time.Clock()

    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    wave_manager = WaveManager()
    game_state = GameState()

    enemies = []
    exp_gems = []
    bullets = []

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state.paused = not game_state.paused
                if game_state.show_start_screen and event.key == pygame.K_RETURN:
                    game_state.show_start_screen = False
                if game_state.show_end_screen and event.key == pygame.K_r:
                    # Réinitialiser le jeu
                    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    wave_manager = WaveManager()
                    game_state = GameState()
                    enemies = []
                    exp_gems = []
                    bullets = []

        if game_state.paused or game_state.show_start_screen or game_state.show_end_screen:
            screen.fill(BLACK)
            if game_state.show_start_screen:
                draw_text(screen, "Bullet Heaven", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
                draw_text(screen, "Appuyez sur Entrée pour commencer", 36, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
            elif game_state.show_end_screen:
                draw_text(screen, "Game Over", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
                draw_text(screen, f"Score: {game_state.score}", 36, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                draw_text(screen, "Appuyez sur R pour recommencer", 36, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
            pygame.display.flip()
            continue

        # Mouvement du joueur
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        player.move(dx, dy)

        # Attaque du joueur
        player.attack(enemies)

        # Mise à jour des ennemis
        wave_manager.update(dt)
        if random.random() < 0.02 and wave_manager.enemies_remaining > 0:
            enemy = wave_manager.spawn_enemy()
            if enemy:
                enemies.append(enemy)

        for enemy in enemies[:]:
            enemy.move_towards_player(player)
            if math.sqrt((player.x - enemy.x) ** 2 + (player.y - enemy.y) ** 2) < player.radius + enemy.radius:
                player.health -= enemy.damage
                if player.health <= 0:
                    game_state.game_over = True
                    game_state.show_end_screen = True
            if enemy.health <= 0:
                enemies.remove(enemy)
                game_state.score += 10
                if random.random() < 0.5:
                    exp_gems.append(ExpGem(enemy.x, enemy.y))

        # Mise à jour des gemmes d'expérience
        for gem in exp_gems[:]:
            distance = math.sqrt((player.x - gem.x) ** 2 + (player.y - gem.y) ** 2)
            if distance < player.radius + gem.radius:
                player.gain_exp(gem.value)
                exp_gems.remove(gem)

        # Dessin
        screen.fill(BLACK)
        for enemy in enemies:
            enemy.draw(screen)
        for gem in exp_gems:
            gem.draw(screen)
        player.draw(screen)

        # Affichage des informations
        draw_text(screen, f"Niveau: {player.level}", 24, 70, 20)
        draw_text(screen, f"Exp: {player.exp}/{player.exp_to_level}", 24, 70, 50)
        draw_text(screen, f"Vague: {wave_manager.current_wave}", 24, SCREEN_WIDTH - 70, 20)
        draw_text(screen, f"Score: {game_state.score}", 24, SCREEN_WIDTH - 70, 50)
        draw_text(screen, f"Santé: {player.health}/{player.max_health}", 24, SCREEN_WIDTH // 2, 20)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()