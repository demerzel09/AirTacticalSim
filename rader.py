class Radar:
    def __init__(self, range, fov, frequency):
        self.range = range
        self.fov = fov
        self.frequency = frequency

    def detect(self, aircraft):
        # 簡単な検出ロジック
        if abs(self.x - aircraft.x) < self.range:
            return True
        return False
