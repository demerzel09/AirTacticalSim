class Missile:
    def __init__(self, x, y, range):
        self.x = x
        self.y = y
        self.range = range

    def update(self):
        self.x += 10  # ミサイルの速度
