

import os

def count_symbols(folder):
    total = 0
    for root, dirs, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(".py"):
                path = os.path.join(root, name)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    total += len(f.read())
    return total




if __name__ == "__main__":
    symbols = count_symbols("C:/Users/vilia/Documents/GitHub/nappulapeli")
    print("SYMBOLS:", symbols)