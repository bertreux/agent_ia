import tkinter as tk
from tkinter import messagebox

class SudokuGame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sudoku Game")
        self.geometry("450x500")
        self.create_widgets()

    def create_widgets(self):
        self.canvas = tk.Canvas(self, width=450, height=450, bg="white")
        self.canvas.pack()
        self.draw_grid()
        self.buttons_frame = tk.Frame(self)
        self.buttons_frame.pack()
        self.check_button = tk.Button(self.buttons_frame, text="Vérifier", command=self.check_solution)
        self.check_button.pack(side=tk.LEFT, padx=5)
        self.new_button = tk.Button(self.buttons_frame, text="Nouveau", command=self.new_game)
        self.new_button.pack(side=tk.LEFT, padx=5)

    def draw_grid(self):
        for i in range(10):
            color = "black" if i % 3 == 0 else "gray"
            self.canvas.create_line(i * 50, 0, i * 50, 450, fill=color, width=2)
            self.canvas.create_line(0, i * 50, 450, i * 50, fill=color, width=2)

        self.cells = []
        for row in range(9):
            for col in range(9):
                x1, y1 = col * 50, row * 50
                x2, y2 = x1 + 50, y1 + 50
                cell = self.canvas.create_rectangle(x1, y1, x2, y2, outline="", fill="white")
                self.cells.append((row, col, cell))

    def new_game(self):
        self.canvas.delete("all")
        self.draw_grid()

    def check_solution(self):
        if True:
            messagebox.showinfo("Résultat", "Solution correcte!")

if __name__ == "__main__":
    SudokuGame().mainloop()