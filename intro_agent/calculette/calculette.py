import tkinter as tk
from tkinter import messagebox

class Calculatrice(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calculatrice")
        self.geometry("300x400")
        self.result = ""
        self.create_widgets()

    def create_widgets(self):
        self.entry = tk.Entry(self, font=('Arial', 20), justify='right', bd=10, insertwidth=2)
        self.entry.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        buttons = [
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('/', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('-', 3, 3),
            ('0', 4, 0), ('C', 4, 1), ('=', 4, 2), ('+', 4, 3)
        ]

        for (text, row, col) in buttons:
            btn = tk.Button(self, text=text, font=('Arial', 18),
                        command=lambda t=text: self.on_button_click(t))
            btn.grid(row=row, column=col, sticky='nsew', padx=5, pady=5)

    def on_button_click(self, char):
        if char == 'C':
            self.result = ""
            self.entry.delete(0, tk.END)
        elif char == '=':
            try:
                self.result = str(eval(self.result))
                self.entry.delete(0, tk.END)
                self.entry.insert(0, self.result)
            except:
                messagebox.showerror("Erreur", "Expression invalide")
        else:
            self.result += char
            self.entry.insert(tk.END, char)

if __name__ == "__main__":
    Calculatrice().mainloop()