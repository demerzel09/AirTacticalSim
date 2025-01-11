import pygame
import random
import math
import sys

# 画面サイズ
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# 色の定義
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

# ミサイルクラス（敵ミサイル）
class Missile:
    def __init__(self, x, y, target_x, target_y):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = 2
        # ミサイルの方向を計算
        angle = math.atan2(target_y - y, target_x - x)
        self.dx = math.cos(angle) * self.speed
        self.dy = math.sin(angle) * self.speed

    def update(self):
        # ミサイルの位置を更新
        self.x += self.dx
        self.y += self.dy

    def draw(self, screen):
        pygame.draw.line(screen, RED, (self.x, self.y), (self.x + self.dx * 2, self.y + self.dy * 2), 2)

# 都市クラス
class City:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True

    def draw(self, screen):
        if self.alive:
            pygame.draw.rect(screen, BLUE, (self.x, self.y, 40, 20))

# 防御ミサイルクラス（プレイヤーミサイル）
class DefenseMissile:
    def __init__(self, x, y, target_x, target_y):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = 5
        self.exploded = False
        # 角度計算
        angle = math.atan2(target_y - y, target_x - x)
        self.dx = math.cos(angle) * self.speed
        self.dy = math.sin(angle) * self.speed

    def update(self):
        if not self.exploded:
            # 位置を更新
            self.x += self.dx
            self.y += self.dy
            # ターゲットに到達したら爆発
            if math.hypot(self.target_x - self.x, self.target_y - self.y) < 5:
                self.exploded = True

    def draw(self, screen):
        if not self.exploded:
            pygame.draw.line(screen, GREEN, (self.x, self.y), (self.x + self.dx * 2, self.y + self.dy * 2), 2)
        else:
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 10)

# メインゲーム関数
def game_loop():
    # 都市の配置
    cities = [City(100 + i * 150, SCREEN_HEIGHT - 30) for i in range(5)]

    # ゲーム変数
    missiles = []
    defense_missiles = []
    score = 0
    clock = pygame.time.Clock()

    running = True
    game_over = False

    while running:
        screen.fill(BLACK)

        # イベント処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                # クリックで防御ミサイルを発射
                x, y = pygame.mouse.get_pos()
                defense_missiles.append(DefenseMissile(SCREEN_WIDTH // 2, SCREEN_HEIGHT, x, y))

        # 敵ミサイルをランダムで生成
        if random.randint(0, 50) == 0 and not game_over:
            target_city = random.choice([city for city in cities if city.alive])
            missiles.append(Missile(random.randint(0, SCREEN_WIDTH), 0, target_city.x + 20, target_city.y))

        # ミサイルの更新と描画
        for missile in missiles[:]:
            missile.update()
            missile.draw(screen)
            # ミサイルが都市に到達した場合
            for city in cities:
                if city.alive and math.hypot(missile.x - (city.x + 20), missile.y - city.y) < 10:
                    city.alive = False
                    missiles.remove(missile)

        # 防御ミサイルの更新と描画
        for d_missile in defense_missiles[:]:
            d_missile.update()
            d_missile.draw(screen)
            # 防御ミサイルが敵ミサイルに当たるかをチェック
            if d_missile.exploded:
                for missile in missiles[:]:
                    if math.hypot(d_missile.x - missile.x, d_missile.y - missile.y) < 20:
                        missiles.remove(missile)
                        score += 100
                defense_missiles.remove(d_missile)

        # 都市の描画
        for city in cities:
            city.draw(screen)

        # スコア表示
        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        # ゲームオーバー判定
        if all(not city.alive for city in cities):
            game_over = True
            game_over_text = font.render("GAME OVER", True, RED)
            screen.blit(game_over_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))
            pygame.display.flip()

        # ゲームオーバー時にリプレイを促す
        if game_over:
            replay_text = font.render("Press R to Replay or Q to Quit", True, WHITE)
            screen.blit(replay_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 + 50))
            pygame.display.flip()

            # リプレイか終了の入力を待つ
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                return True  # リプレイ
            if keys[pygame.K_q]:
                return False  # 終了

        pygame.display.flip()
        clock.tick(60)

    return False

def main():
    pygame.init()

    # 画面の設定
    global screen
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Missile Command")

    # メインゲームループ
    while True:
        if not game_loop():
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
