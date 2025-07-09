import pygame
import random

# Initialisation de Pygame
pygame.init()

# Dimensions de la fenêtre
WIDTH, HEIGHT = 300, 600
GRID_SIZE = 30
GRID_WIDTH = WIDTH // GRID_SIZE
GRID_HEIGHT = HEIGHT // GRID_SIZE

# Couleurs
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
COLORS = [
    (0, 255, 255), (0, 0, 255), (255, 165, 0),
    (255, 255, 0), (0, 255, 0), (128, 0, 128),
    (255, 0, 0)
]

# Formes des pièces
SHAPES = [
    [[1, 1, 1, 1]],
    [[1, 1], [1, 1]],
    [[1, 1, 1], [0, 1, 0]],
    [[1, 1, 1], [1, 0, 0]],
    [[1, 1, 1], [0, 0, 1]],
    [[0, 1, 1], [1, 1, 0]],
    [[1, 1, 0], [0, 1, 1]]
]

class Tetris:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = self.new_piece()
        self.game_over = False

    def new_piece(self):
        shape = random.choice(SHAPES)
        color = random.choice(COLORS)
        x = GRID_WIDTH // 2 - len(shape[0]) // 2
        y = 0
        return {
            "shape": shape,
            "color": color,
            "x": x,
            "y": y
        }

    def valid_move(self, piece, x_offset, y_offset):
        for y, row in enumerate(piece["shape"]):
            for x, cell in enumerate(row):
                if cell:
                    new_x = piece["x"] + x + x_offset
                    new_y = piece["y"] + y + y_offset
                    if (new_x < 0 or new_x >= GRID_WIDTH or
                        new_y >= GRID_HEIGHT or
                        (new_y >= 0 and self.grid[new_y][new_x])):
                        return False
        return True

    def merge_piece(self):
        for y, row in enumerate(self.current_piece["shape"]):
            for x, cell in enumerate(row):
                if cell:
                    self.grid[self.current_piece["y"] + y][self.current_piece["x"] + x] = self.current_piece["color"]

    def clear_lines(self):
        lines_to_clear = [i for i, row in enumerate(self.grid) if all(row)]
        for i in lines_to_clear:
            del self.grid[i]
            self.grid.insert(0, [0 for _ in range(GRID_WIDTH)])

    def rotate_piece(self):
        rotated = list(zip(*self.current_piece["shape"][::-1]))
        if self.valid_move(self.current_piece, 0, 0):
            self.current_piece["shape"] = [list(row) for row in rotated]

    def draw_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                pygame.draw.rect(
                    self.screen,
                    self.grid[y][x] if self.grid[y][x] else BLACK,
                    (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE),
                    0 if self.grid[y][x] else 1
                )

    def draw_piece(self):
        for y, row in enumerate(self.current_piece["shape"]):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(
                        self.screen,
                        self.current_piece["color"],
                        (
                            (self.current_piece["x"] + x) * GRID_SIZE,
                            (self.current_piece["y"] + y) * GRID_SIZE,
                            GRID_SIZE,
                            GRID_SIZE
                        )
                    )

    def run(self):
        while not self.game_over:
            self.screen.fill(BLACK)
            self.draw_grid()
            self.draw_piece()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.game_over = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT and self.valid_move(self.current_piece, -1, 0):
                        self.current_piece["x"] -= 1
                    elif event.key == pygame.K_RIGHT and self.valid_move(self.current_piece, 1, 0):
                        self.current_piece["x"] += 1
                    elif event.key == pygame.K_DOWN and self.valid_move(self.current_piece, 0, 1):
                        self.current_piece["y"] += 1
                    elif event.key == pygame.K_UP:
                        self.rotate_piece()

            if self.valid_move(self.current_piece, 0, 1):
                self.current_piece["y"] += 1
            else:
                self.merge_piece()
                self.clear_lines()
                self.current_piece = self.new_piece()
                if not self.valid_move(self.current_piece, 0, 0):
                    self.game_over = True

            pygame.display.flip()
            self.clock.tick(5)

if __name__ == "__main__":
    game = Tetris()
    game.run()
    pygame.quit()