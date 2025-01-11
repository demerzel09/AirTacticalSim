import pygame
import random

class Aircraft:
    def __init__(self, x, y, speed, acceleration, color):
        self.x = x
        self.y = y
        self.speed = speed
        self.acceleration = acceleration
        self.color = color

    def update(self):
        self.speed += self.acceleration
        self.x += self.speed
        if self.x > 800:
            self.x = 0

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 5)


# 飛行隊クラス
class Squadron:
    def __init__(self, color):
        self.aircrafts = [Aircraft(random.randint(0, 800), random.randint(0, 600), random.uniform(1, 3), random.uniform(-0.1, 0.1), color) for _ in range(3)]

    def update(self):
        for aircraft in self.aircrafts:
            aircraft.update()

    def draw(self, screen):
        for aircraft in self.aircrafts:
            aircraft.draw(screen)



class AircraftAI:
    def __init__(self, aircraft):
        self.aircraft = aircraft

    def make_decision(self):
        # 簡単なAIロジック
        if self.aircraft.x < 400:
            self.aircraft.acceleration = 1
        else:
            self.aircraft.acceleration = -1