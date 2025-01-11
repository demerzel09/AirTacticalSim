import pygame
import math
import random

# Pygameの初期化
pygame.init()

# ウィンドウの設定
WIDTH, HEIGHT = 1280, 720  # 画面サイズを1280x720に設定
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AIによる自動戦闘シミュレーション")

# 色の定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)         # ミサイルの色をBLACKに設定
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)    # 回避用の色
MAGENTA = (255, 0, 255) # 攻撃用の色
GRAY = (200, 200, 200)  # コーンの色

# FPS設定
BASE_FPS = 60  # 基本のFPS
FPS = BASE_FPS
clock = pygame.time.Clock()

# 戦闘機とミサイルの設定
FIGHTER_SIZE = 3  # 戦闘機の描画半径
MISSILE_SIZE = 2  # ミサイルの描画半径
FIGHTER_SPEED = 0.2  # 戦闘機の速度
MISSILE_MAX_SPEED = 0.6  # ミサイルの最大速度
MISSILE_INITIAL_SPEED = FIGHTER_SPEED  # ミサイルの初速
MISSILE_ACCELERATION_TIME = 3 * BASE_FPS  # ミサイルの加速時間（3秒）
MISSILE_ACCELERATION_RATE = (MISSILE_MAX_SPEED - MISSILE_INITIAL_SPEED) / MISSILE_ACCELERATION_TIME  # ミサイルの加速度
MISSILE_TURN_RATE = 45  # ミサイルの最大旋回角速度（度/秒）
MISSILE_TURN_RATE_PER_FRAME = MISSILE_TURN_RATE / BASE_FPS
MISSILE_MIN_SPEED = FIGHTER_SPEED * 0.8  # ミサイルが消滅する最小速度
RADAR_RANGE = 500  # レーダー範囲を500に設定
MAX_MISSILES = 4  # 各戦闘機が同時に発射できるミサイル数
FIRE_COOLDOWN = 2 * BASE_FPS  # ミサイルを撃つ際に2秒のインターバル（フレーム数で設定）
ROTATION_SPEED = 30  # 30°/秒の回転速度

# 視線角速度の閾値
LOS_RATE_THRESHOLD = 0.5  # 調整可能

# 時間定数
TIME_IN_SECONDS = 3.5  # ミサイルの到達可能セクターを計算する際の時間

# チームの飛行基地の座標
BLUE_BASE = (30, 30)
RED_BASE = (WIDTH - 30, HEIGHT - 30)

# 角度計算関数
def calculate_angle(dx, dy):
    angle = math.degrees(math.atan2(dy, dx)) % 360
    return angle

# 爆発アニメーションを管理するクラス
class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.frame = 0
        self.max_frames = 6

    def draw(self, screen):
        if self.frame < self.max_frames:
            pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), 10 + self.frame * 2, 1)
            self.frame += 1  # フレームを進める

    def is_finished(self):
        return self.frame >= self.max_frames

def point_in_sector(point, center, radius, direction, angle_width):
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    distance = math.hypot(dx, dy)

    if distance > radius:
        return False  # 点が半径の外側にある

    # セクターの角度幅が360度以上の場合、全ての点を含む
    if angle_width >= 360:
        return True

    # 中心から点への角度を計算
    point_angle = calculate_angle(dx, dy)

    # セクターの開始角度と終了角度を計算
    start_angle = (direction - angle_width / 2) % 360
    end_angle = (direction + angle_width / 2) % 360

    # 角度が跨いでいる場合を考慮
    if start_angle <= end_angle:
        return start_angle <= point_angle <= end_angle
    else:
        return point_angle >= start_angle or point_angle <= end_angle

def calculate_missile_sector(missile):
    # ミサイルの最大旋回角度を計算
    max_turn_angle = MISSILE_TURN_RATE * TIME_IN_SECONDS  # 度単位
    max_turn_angle = min(max_turn_angle, 180)  # 最大で180度

    # ミサイルの最大移動距離を計算（加速を考慮）
    time_in_frames = int(TIME_IN_SECONDS * BASE_FPS)
    distance = 0
    current_speed = missile.speed
    remaining_time = time_in_frames

    # ミサイルが加速中の場合
    if missile.age < MISSILE_ACCELERATION_TIME:
        accel_time = min(MISSILE_ACCELERATION_TIME - missile.age, remaining_time)
        distance += current_speed * accel_time + 0.5 * MISSILE_ACCELERATION_RATE * accel_time ** 2
        current_speed += MISSILE_ACCELERATION_RATE * accel_time
        remaining_time -= accel_time
    else:
        current_speed = missile.speed

    # 最大速度を超えないようにする
    current_speed = min(current_speed, MISSILE_MAX_SPEED)

    # 残りの時間での移動距離を計算
    if remaining_time > 0:
        distance += current_speed * remaining_time

    # セクターの角度幅を360度に制限
    angle_width = min(max_turn_angle * 2, 360)

    # セクター情報を返す
    sector = {
        'center': (missile.x, missile.y),
        'radius': distance,
        'direction': missile.direction,  # ミサイルの進行方向
        'angle_width': angle_width  # セクターの角度幅
    }

    return sector

# 戦闘機クラス
class Fighter:
    def __init__(self, team_color, enemy_base):
        self.team_color = team_color
        self.enemy_base = enemy_base  # 敵の基地の座標
        self.speed = FIGHTER_SPEED
        self.radar_range = RADAR_RANGE
        self.missiles = []  # 発射されたミサイルのリスト
        self.is_alive = True
        self.last_fired_time = 0  # 最後にミサイルを発射したフレーム
        self.avoiding_missile = None  # 回避中のミサイルを記録
        self.attacking_enemy = None  # 攻撃対象の敵を記録
        self.avoid_direction = None  # 回避時の方向ベクトル
        self.respawn_timer = 0  # リスポーンまでの残り時間
        self.previous_los_angles = {}  # ミサイルごとの前回の視線角を記録
        self.respawn()  # 初期位置と向きを設定

    def respawn(self):
        # チームの飛行基地周辺に再配置
        offset_range = 20  # オフセットの範囲
        if self.team_color == BLUE:
            self.x = BLUE_BASE[0] + random.uniform(-offset_range, offset_range)
            self.y = BLUE_BASE[1] + random.uniform(-offset_range, offset_range)
            self.direction = 0  # 右向き
        else:
            self.x = RED_BASE[0] + random.uniform(-offset_range, offset_range)
            self.y = RED_BASE[1] + random.uniform(-offset_range, offset_range)
            self.direction = 180  # 左向き
        self.is_alive = True
        self.last_fired_time = pygame.time.get_ticks()  # ミサイル発射時間リセット
        self.target_direction = self.direction  # 目標方向を初期化
        self.previous_los_angles = {}  # 視線角の履歴をリセット

    def update_respawn_timer(self):
        if not self.is_alive:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.respawn()

    def rotate_towards_target(self):
        # 目標方向に向かってROTATION_SPEED°/秒で回転
        rotation_per_frame = ROTATION_SPEED / BASE_FPS
        angle_diff = (self.target_direction - self.direction + 360) % 360
        if angle_diff > 180:
            angle_diff -= 360
        if abs(angle_diff) < rotation_per_frame:
            self.direction = self.target_direction  # 目標方向に到達
        else:
            self.direction += rotation_per_frame * (1 if angle_diff > 0 else -1)
        self.direction %= 360  # 角度を0-360の範囲に

    def avoid_screen_edges(self):
        margin = 50  # 画面端からの距離（ピクセル）
        avoid_vector = [0, 0]
        if self.x < margin:
            avoid_vector[0] += 1 / (self.x + 1e-6)
        if self.x > WIDTH - margin:
            avoid_vector[0] -= 1 / (WIDTH - self.x + 1e-6)
        if self.y < margin:
            avoid_vector[1] += 1 / (self.y + 1e-6)
        if self.y > HEIGHT - margin:
            avoid_vector[1] -= 1 / (HEIGHT - self.y + 1e-6)
        if avoid_vector != [0, 0]:
            avoid_angle = calculate_angle(avoid_vector[0], avoid_vector[1])
            self.target_direction = avoid_angle
            return True
        return False

    def move(self):
        # 回避行動またはターゲット方向に向かう
        self.rotate_towards_target()

        # 常に進む
        dx = self.speed * math.cos(math.radians(self.direction))
        dy = self.speed * math.sin(math.radians(self.direction))

        # 画面端に到達したらそれ以上進まない
        new_x = self.x + dx
        new_y = self.y + dy

        if 0 <= new_x <= WIDTH:
            self.x = new_x

        if 0 <= new_y <= HEIGHT:
            self.y = new_y

    def draw(self, screen):
        # 戦闘機が生きている場合のみ描画
        if self.is_alive:
            pygame.draw.circle(screen, self.team_color, (int(self.x), int(self.y)), FIGHTER_SIZE)
            # レーダーの範囲を円で表示
            pygame.draw.circle(screen, GREEN, (int(self.x), int(self.y)), int(self.radar_range), 1)

        # 回避中のミサイルと戦闘機をシアンの線で結ぶ
        if self.avoiding_missile:
            pygame.draw.line(screen, CYAN, (int(self.x), int(self.y)),
                             (int(self.x + self.avoid_direction[0]*50), int(self.y + self.avoid_direction[1]*50)), 1)

        # 攻撃中の敵と戦闘機をマゼンタの線で結ぶ
        if self.attacking_enemy:
            pygame.draw.line(screen, MAGENTA, (int(self.x), int(self.y)),
                             (int(self.attacking_enemy.x), int(self.attacking_enemy.y)), 1)

    def detect_enemy(self, enemy):
        # 敵が生きているか確認
        if not enemy.is_alive:
            return False
        # レーダー範囲内に敵がいるかどうかを確認
        distance = math.hypot(self.x - enemy.x, self.y - enemy.y)
        return distance < self.radar_range

    def in_attack_cone(self, enemy):
        # 敵が生きているか確認
        if not enemy.is_alive:
            return False
        # 同じチームの敵は攻撃しない
        if enemy.team_color == self.team_color:
            return False

        # ミサイル回避中でも攻撃するため、攻撃コーンを広げる
        if self.avoiding_missile:
            return True  # 方向に関係なく攻撃可能
        else:
            # 前方45度以内に敵がいるかどうかを判定
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            distance = math.hypot(dx, dy)  # 距離を計算
            angle_to_enemy = calculate_angle(dx, dy)
            angle_diff = (angle_to_enemy - self.direction + 360) % 360
            if angle_diff > 180:
                angle_diff -= 360
            return distance < self.radar_range and abs(angle_diff) < 22.5

    def fire_missile(self, enemy):
        # 同時に発射できるミサイル数とインターバルを確認
        current_time = pygame.time.get_ticks()
        if len(self.missiles) < MAX_MISSILES and current_time - self.last_fired_time >= FIRE_COOLDOWN:
            missile = Missile(self.x, self.y, enemy, self)
            self.missiles.append(missile)
            self.last_fired_time = current_time  # 発射時間を更新
            self.attacking_enemy = enemy  # 攻撃対象を記録

    def aim_at_enemy(self, enemy):
        # 敵の位置に向かって回転し、接近する
        dx = enemy.x - self.x
        dy = enemy.y - self.y
        angle_to_enemy = calculate_angle(dx, dy)
        self.target_direction = angle_to_enemy

    def avoid_missile(self, missiles):
        # 自分に接近しているミサイルを検知して回避行動を取る
        avoidance_vector = [0, 0]
        threat_detected = False

        for missile in missiles:
            # 自分の発射したミサイルは無視
            if missile.owner == self:
                continue

            # ミサイルと戦闘機の位置差
            dx = missile.x - self.x
            dy = missile.y - self.y
            distance = math.hypot(dx, dy)

            # ミサイルがレーダー範囲外なら無視
            if distance > self.radar_range:
                continue

            # ミサイルの速度が自機の2.0倍未満の場合、セクターの範囲外なら無視
            if missile.speed < FIGHTER_SPEED * 2.0:
                # ミサイルの到達可能セクターを計算
                sector = calculate_missile_sector(missile)

                # 戦闘機がセクター内にいるかを判定
                if not point_in_sector((self.x, self.y), sector['center'], sector['radius'], sector['direction'], sector['angle_width']):
                    continue  # このミサイルを無視

            # ここから先はミサイルを脅威と判断
            # 視線角の計算
            los_angle = calculate_angle(dx, dy)

            # 前回の視線角を取得
            previous_los_angle = self.previous_los_angles.get(missile, los_angle)

            # 視線角速度の計算
            los_rate = (los_angle - previous_los_angle + 360) % 360
            if los_rate > 180:
                los_rate -= 360
            los_rate = abs(los_rate)

            # 視線角速度が小さい場合、脅威と判断
            if los_rate < LOS_RATE_THRESHOLD:
                # 距離に反比例する重みを計算
                weight = 1 / (distance + 1e-6)
                # ミサイルから遠ざかるベクトルを加算
                avoidance_vector[0] -= dx * weight
                avoidance_vector[1] -= dy * weight
                threat_detected = True
                self.avoiding_missile = missile  # 回避中のミサイルを記録

            # 視線角を更新
            self.previous_los_angles[missile] = los_angle

        if threat_detected:
            # 合成された回避ベクトルの方向にターゲット方向を設定
            avoid_angle = calculate_angle(avoidance_vector[0], avoidance_vector[1])
            self.target_direction = avoid_angle
            norm = math.hypot(*avoidance_vector)
            if norm != 0:
                self.avoid_direction = [avoidance_vector[0]/norm, avoidance_vector[1]/norm]
            else:
                self.avoid_direction = [0, 0]
            return True
        else:
            self.avoiding_missile = None
            self.avoid_direction = None
            return False

    def act(self, enemies, missiles):
        if not self.is_alive:
            return

        # 画面端を回避
        if self.avoid_screen_edges():
            return  # 画面端を回避している場合、他の行動はしない

        # まず、ミサイルを回避する（優先度1）
        self.avoid_missile(missiles)
        # ミサイル回避中でも攻撃は行う

        # 次に、敵を攻撃する（優先度2）
        for enemy in enemies:
            if enemy.team_color != self.team_color and enemy.is_alive:  # 同じチームでない敵のみ攻撃
                if self.detect_enemy(enemy):
                    if not self.avoiding_missile:
                        self.aim_at_enemy(enemy)
                    if self.in_attack_cone(enemy):
                        self.fire_missile(enemy)
                        break  # 一度攻撃したら他の敵は無視

        if not self.avoiding_missile:
            # 敵がレーダー範囲内にいない場合、敵基地に向かう
            dx = self.enemy_base[0] - self.x
            dy = self.enemy_base[1] - self.y
            angle_to_base = calculate_angle(dx, dy)
            self.target_direction = angle_to_base

# ミサイルクラス
class Missile:
    def __init__(self, x, y, target, owner):
        self.x = x
        self.y = y
        self.target = target
        self.owner = owner  # 発射者を記録
        self.age = 0  # ミサイルの経過フレーム数
        self.speed = MISSILE_INITIAL_SPEED  # ミサイルの初速
        self.expired = False  # ミサイルが消滅したかどうか

        # ターゲットへの初期方向を設定
        dx = target.x - x
        dy = target.y - y
        self.direction = calculate_angle(dx, dy)
        self.turn_rate = MISSILE_TURN_RATE_PER_FRAME  # フレームごとの最大旋回角度

    def move(self):
        # ミサイルの寿命を更新
        self.age += 1

        # 加速フェーズ
        if self.age <= MISSILE_ACCELERATION_TIME:
            # 加速度を適用
            self.speed += MISSILE_ACCELERATION_RATE
            # 最大速度を超えないようにする
            if self.speed > MISSILE_MAX_SPEED:
                self.speed = MISSILE_MAX_SPEED
        else:
            # 空気抵抗による減速
            drag = 0.001  # 空気抵抗係数（調整可能）
            self.speed -= drag * self.speed ** 2

            # 旋回によるエネルギー損失
            turn_energy_loss = abs(self.turn_rate) * 0.0005  # 調整可能
            self.speed -= turn_energy_loss

            # 最小速度を下回らないようにする
            if self.speed < 0:
                self.speed = 0

        # ミサイルの速度が最小速度未満になったら消滅フラグを立てる
        if self.speed < MISSILE_MIN_SPEED:
            self.speed = 0  # 速度を0に
            self.expired = True  # 消滅フラグを立てる

        # ターゲットの現在位置に向かって方向を更新（比例航法）
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        los_angle = calculate_angle(dx, dy)

        # 視線角速度を計算
        angle_diff = (los_angle - self.direction + 360) % 360
        if angle_diff > 180:
            angle_diff -= 360

        # Proportional Navigationで方向を更新
        N = 3  # ナビゲーション比（調整可能）
        omega = N * math.radians(angle_diff)
        turn = math.degrees(omega) / BASE_FPS

        # ミサイルの旋回角速度を制限
        if abs(turn) > self.turn_rate:
            turn = self.turn_rate * (1 if turn > 0 else -1)

        self.direction += turn
        self.direction %= 360

        # ミサイルの移動
        dx = self.speed * math.cos(math.radians(self.direction))
        dy = self.speed * math.sin(math.radians(self.direction))

        # 画面端に到達したらそれ以上進まない
        new_x = self.x + dx
        new_y = self.y + dy

        if 0 <= new_x <= WIDTH:
            self.x = new_x

        if 0 <= new_y <= HEIGHT:
            self.y = new_y

    def draw(self, screen):
        # ミサイルの描画
        pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), MISSILE_SIZE)

        # ミサイルの到達可能セクターを計算
        sector = calculate_missile_sector(self)

        # セクターの角度幅が360度以上の場合、全円を描画
        if sector['angle_width'] >= 360:
            pygame.draw.circle(screen, GRAY, (int(self.x), int(self.y)), int(sector['radius']), 1)
        else:
            # セクターの開始角度と終了角度を計算
            start_angle = (sector['direction'] - sector['angle_width'] / 2) % 360
            end_angle = (sector['direction'] + sector['angle_width'] / 2) % 360

            # 開始角度と終了角度をラジアンに変換（Pygameは時計回りに増加）
            start_rad = math.radians(-start_angle % 360)
            end_rad = math.radians(-end_angle % 360)

            # 開始角度が終了角度より小さい場合、開始角度に2πを加算
            if start_rad < end_rad:
                start_rad += 2 * math.pi

            # 円弧を描画するための矩形を作成
            rect = pygame.Rect(self.x - sector['radius'], self.y - sector['radius'],
                               2 * sector['radius'], 2 * sector['radius'])

            # 円弧を描画
            pygame.draw.arc(screen, GRAY, rect, end_rad, start_rad, 1)

            # セクターの両端からミサイルの位置へ線を描画
            left_angle = (sector['direction'] - sector['angle_width'] / 2) % 360
            left_dx = sector['radius'] * math.cos(math.radians(left_angle))
            left_dy = sector['radius'] * math.sin(math.radians(left_angle))
            left_x = self.x + left_dx
            left_y = self.y + left_dy

            right_angle = (sector['direction'] + sector['angle_width'] / 2) % 360
            right_dx = sector['radius'] * math.cos(math.radians(right_angle))
            right_dy = sector['radius'] * math.sin(math.radians(right_angle))
            right_x = self.x + right_dx
            right_y = self.y + right_dy

            # 線を描画
            pygame.draw.line(screen, GRAY, (int(self.x), int(self.y)), (int(left_x), int(left_y)), 1)
            pygame.draw.line(screen, GRAY, (int(self.x), int(self.y)), (int(right_x), int(right_y)), 1)

    def check_collision(self, fighter):
        # 発射者や同じチームの戦闘機には当たらないようにする
        if fighter.team_color == self.owner.team_color:
            return False
        # 戦闘機との衝突判定
        distance = math.hypot(self.x - fighter.x, self.y - fighter.y)
        return distance < (FIGHTER_SIZE + MISSILE_SIZE)

    def is_expired(self):
        # ミサイルが消滅したかどうか
        return self.expired

# メインループ
def main():
    global FPS
    run = True

    # 各チームの戦闘機を作成
    fighters = []

    # ブルーチームの戦闘機を作成
    for i in range(3):
        fighter = Fighter(BLUE, RED_BASE)
        fighter.respawn_timer = i * BASE_FPS  # 1秒おきにリスポーン
        fighter.is_alive = False  # 最初は待機状態
        fighters.append(fighter)

    # レッドチームの戦闘機を作成
    for i in range(3):
        fighter = Fighter(RED, BLUE_BASE)
        fighter.respawn_timer = i * BASE_FPS  # 1秒おきにリスポーン
        fighter.is_alive = False  # 最初は待機状態
        fighters.append(fighter)

    explosions = []  # 爆発アニメーションのリスト

    while run:
        # 全ての戦闘機が敵を検知しているか確認
        any_enemy_detected = False
        for fighter in fighters:
            if fighter.is_alive:
                enemies = [f for f in fighters if f != fighter and f.is_alive and f.team_color != fighter.team_color]
                for enemy in enemies:
                    if fighter.detect_enemy(enemy):
                        any_enemy_detected = True
                        break
                if any_enemy_detected:
                    break

        # FPSを調整
        if any_enemy_detected:
            FPS = BASE_FPS
        else:
            FPS = BASE_FPS * 2  # 2倍に設定

        clock.tick(FPS)
        screen.fill(WHITE)

        # イベント処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        missiles = [missile for fighter in fighters for missile in fighter.missiles]

        # 削除予定のミサイルリスト
        missiles_to_remove = []

        # 全ての戦闘機の行動を実行
        for fighter in fighters:
            fighter.update_respawn_timer()
            if fighter.is_alive:
                enemies = [f for f in fighters if f != fighter and f.is_alive and f.team_color != fighter.team_color]
                fighter.act(enemies, missiles)

        # ミサイルの移動と描画
        for fighter in fighters:
            for missile in fighter.missiles:
                missile.move()
                missile.draw(screen)
                for enemy in fighters:
                    if enemy.is_alive and missile.check_collision(enemy):
                        explosions.append(Explosion(enemy.x, enemy.y))  # 爆発をリストに追加
                        enemy.is_alive = False
                        enemy.respawn_timer = BASE_FPS  # 1秒後にリスポーン
                        missiles_to_remove.append(missile)

                # ミサイルが消滅条件を満たした場合に削除リストに追加
                if missile.is_expired():
                    missiles_to_remove.append(missile)

        # 削除用リストに追加したミサイルを削除
        for fighter in fighters:
            fighter.missiles = [m for m in fighter.missiles if m not in missiles_to_remove]

        # 爆発アニメーションの描画と管理
        for explosion in explosions:
            explosion.draw(screen)
        explosions = [exp for exp in explosions if not exp.is_finished()]

        # 戦闘機の移動と描画
        for fighter in fighters:
            if fighter.is_alive:
                fighter.move()
            fighter.draw(screen)

        # 画面更新（フレームに1回だけ）
        pygame.display.update()

    pygame.quit()

if __name__ == "__main__":
    main()
