import math
import random
import pygame
import theme
from snake import GRID, OFFSET, SIZE, TAIL_HIT_SQ
from food import EAT_DISTANCE

SPAWN_INTERVAL = 9.0       # マグネットが湧くまでの間隔(秒) ※効果が切れてからカウント
ITEM_LIFETIME = 8.0        # 拾われずに残れる寿命(秒)
BOOST_DURATION = 15.0       # 効果の持続時間(秒)
BOOST_MULTIPLIER = 5       # foodの当たり判定を何倍にするか（reach=EAT_DISTANCE*5=50px≒2.5セル）
BLINK_LAST = 3.0           # 効果が切れる前この秒数だけオーラを点滅させる
HEAD_CLEARANCE_SQ = 30 * 30  # 頭のすぐ近くには湧かせない(px²)
SAFE_DISTANCE_SQ = SIZE * SIZE
GRID_SQ = GRID * GRID
MAX_TRIES = 60


# 蛇が触れると、一定時間 food の当たり判定を BOOST_MULTIPLIER 倍に広げるアイテム
class Magnet:
    def __init__(self, x, y, ttl):
        self.x = x
        self.y = y
        self.ttl = ttl

    def distance_sq(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    # 馬蹄形マグネット（赤い本体＋シルバーの極）を描く
    def draw(self, surface):
        cx, cy = theme.to_screen(self.x, self.y)
        r = 8          # 馬蹄のアーチ半径
        th = 5         # 線の太さ
        leg = 6        # 脚の長さ
        body = theme.MAGNET_BODY
        rect = pygame.Rect(cx - r, cy - r - 2, 2 * r, 2 * r)
        # 上半分のアーチ（U字の開きは下向き）
        pygame.draw.arc(surface, body, rect, 0, math.pi, th)
        for side in (-1, 1):
            lx = cx + side * (r - th / 2)
            pygame.draw.line(surface, body, (lx, cy - 2), (lx, cy - 2 + leg), th)       # 脚
            pygame.draw.line(surface, theme.MAGNET_TIP, (lx, cy - 2 + leg),             # 極
                             (lx, cy - 2 + leg + 3), th)


CAPACITY = 3               # 同時に出現しうるマグネットの数（将来ショップで増やす想定）
SPAWN_STAGGER = 4.0        # 各スポナーの初回出現をずらす間隔(秒)


# 1スポナー分の状態（盤面上のマグネット1個と、その再出現タイマー）。
# A/B…は同じこのクラスで動く。
class _Spawner:
    def __init__(self, initial_timer):
        self.item = None
        self.timer = initial_timer


# マグネットの出現・寿命・取得・効果（foodの当たり判定を広げる）を管理する。
# CAPACITY 個のスポナーが独立に出現/寿命/取得を回す。効果(ブースト)は全体で1つの共有で、
# どれかを拾うと満タンから再カウントし、所有スポナーだけが効果中は再出現しない。
class MagnetManager:
    def __init__(self, snake, food, obstacles, settings, duration_source=None):
        self.snake = snake
        self.food = food
        self.obstacles = obstacles
        self.settings = settings  # 難易度の has_magnet で有効/無効を判定
        # 効果中に拾うと持続が伸びるアイテム（DurationBoostEffect）。None なら等倍。
        self.duration_source = duration_source
        self.visible = True
        self.capacity = CAPACITY
        # 重なり禁止の相手マネージャ（shield など）。snakegame.py で生成後にセットされる
        self.peers = []
        self.boost_timer = 0.0
        self.boost_owner = -1     # 現在の効果を発生させたスポナーの index（-1=効果なし）
        self.spawners = []
        self._build_spawners()

    def _build_spawners(self):
        # 初回出現を SPAWN_STAGGER ずつずらして同時湧きを避ける
        self.spawners = [_Spawner(SPAWN_INTERVAL + i * SPAWN_STAGGER)
                         for i in range(self.capacity)]
        self.boost_timer = 0.0
        self.boost_owner = -1

    @property
    def boosted(self):
        return self.boost_timer > 0

    # 効果時間3倍ポーションを発動中に飲んだ時: 残り時間を伸ばす
    def extend_active(self, mult):
        if self.boost_timer > 0:
            self.boost_timer *= mult

    # food.check_eaten に渡す当たり判定の倍率
    @property
    def eat_multiplier(self):
        return BOOST_MULTIPLIER if self.boosted else 1

    def _make_magnet(self):
        ttl = ITEM_LIFETIME * self.settings.difficulty.item_duration_scale  # EASY長/HARD短
        for _ in range(MAX_TRIES):
            x = random.randrange(-290, 291, GRID)
            y = random.randrange(-290, 291, GRID)
            m = Magnet(x, y, ttl)
            if self._placeable(m):
                return m
        return None

    def _placeable(self, m):
        # 頭のすぐ近くは避ける
        if m.distance_sq(self.snake.head) < HEAD_CLEARANCE_SQ:
            return False
        # 蛇の体
        for segment in self.snake.segments:
            if m.distance_sq(segment) < SAFE_DISTANCE_SQ:
                return False
        # food（ボーナスオーブ含む）と被らない（仕様）
        for f in self.food.foods:
            if m.distance_sq(f) < GRID_SQ:
                return False
        if self.food.bonus is not None and m.distance_sq(self.food.bonus) < GRID_SQ:
            return False
        # レンガと被らない
        for block in self.obstacles.blocks:
            if m.distance_sq(block) < GRID_SQ:
                return False
        # 既に出ている他のマグネットと被らない
        for sp in self.spawners:
            if sp.item is not None and m.distance_sq(sp.item) < GRID_SQ:
                return False
        # 盤面に出ている他種アイテム（シールド等）とも被らない
        for mgr in self.peers:
            for it in mgr.items_on_board():
                if m.distance_sq(it) < GRID_SQ:
                    return False
        return True

    # 盤面に出ているマグネットの一覧（他マネージャの重なりチェック用）
    def items_on_board(self):
        return [sp.item for sp in self.spawners if sp.item is not None]

    # 拾われた時: 効果を満タンから再発動し、所有権を i へ移す（A効果中にBを拾うと上書き）
    def _pick_up(self, i):
        if 0 <= self.boost_owner < len(self.spawners) and self.boost_owner != i:
            # 旧所有スポナーは効果が切れた扱い→一定間隔後に再出現
            self.spawners[self.boost_owner].timer = SPAWN_INTERVAL
        # 効果時間3倍アイテムが有効なら持続を伸ばす（拾った瞬間の倍率を反映）
        mult = self.duration_source.duration_multiplier if self.duration_source else 1
        self.boost_timer = BOOST_DURATION * self.settings.difficulty.item_duration_scale * mult
        self.boost_owner = i

    # 毎フレーム: 効果・各スポナーの寿命・出現・取得を進める
    def update(self, dt):
        # この難易度でマグネットが無効なら何もしない（クラシック等）
        if not self.settings.difficulty.has_magnet:
            for sp in self.spawners:
                sp.item = None
            self.boost_timer = 0.0
            self.boost_owner = -1
            return

        # 共有の効果タイマー。切れたら所有スポナーが間隔を置いて再出現を始める
        if self.boost_timer > 0:
            self.boost_timer -= dt
            if self.boost_timer <= 0:
                self.boost_timer = 0.0
                if 0 <= self.boost_owner < len(self.spawners):
                    self.spawners[self.boost_owner].timer = SPAWN_INTERVAL
                self.boost_owner = -1

        head = self.snake.head
        for i, sp in enumerate(self.spawners):
            # 効果中の所有スポナーは再出現しない（この制約は他スポナーには及ばない）
            if i == self.boost_owner:
                continue
            if sp.item is None:
                sp.timer -= dt
                if sp.timer <= 0:
                    sp.timer = SPAWN_INTERVAL
                    sp.item = self._make_magnet()
            else:
                sp.item.ttl -= dt
                if sp.item.ttl <= 0:
                    sp.item = None
                elif head.distance_sq(sp.item) < TAIL_HIT_SQ:
                    sp.item = None
                    self._pick_up(i)

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def reset(self):
        self.visible = True
        self._build_spawners()

    def draw(self, surface):
        if not self.visible:
            return
        # 効果中は頭に拾い範囲を示すオーラを脈動表示。
        # 残り BLINK_LAST 秒は点滅させて終了が近いことを知らせる。
        blink_on = self.boost_timer >= BLINK_LAST or (pygame.time.get_ticks() // 180) % 2 == 0
        if self.boosted and blink_on:
            radius = int(EAT_DISTANCE * BOOST_MULTIPLIER)
            pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1) / 2
            alpha = int(60 + 70 * pulse)
            aura = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*theme.MAGNET_AURA[:3], alpha), (radius, radius), radius)
            hx, hy = theme.to_screen(self.snake.head.x, self.snake.head.y)
            surface.blit(aura, (hx - radius, hy - radius))
        for sp in self.spawners:
            if sp.item is not None:
                sp.item.draw(surface)
