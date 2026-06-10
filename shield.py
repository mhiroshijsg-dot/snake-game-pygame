import math
import random
import pygame
import theme
from snake import GRID, SIZE, TAIL_HIT_SQ

SPAWN_INTERVAL = 9.0       # シールドが湧くまでの基本間隔(秒)
SPAWN_JITTER = 4.0         # 間隔のばらつき(±秒)。マグネットと出現タイミングをずらす
INITIAL_OFFSET = 4.5       # 初回はマグネットと初手をずらして同時出現を避ける
ITEM_LIFETIME = 8.0        # 拾われずに残れる寿命(秒)
SHIELD_DURATION = 12.0     # 効果の持続時間(秒)
BLINK_LAST = 3.0           # 効果が切れる前この秒数だけバリアを点滅させる
HEAD_CLEARANCE_SQ = 30 * 30
SAFE_DISTANCE_SQ = SIZE * SIZE
GRID_SQ = GRID * GRID
MAX_TRIES = 60


# 蛇が触れると、一定時間ブロックを破壊して突破できるようになるアイテム
class ShieldItem:
    def __init__(self, x, y, ttl):
        self.x = x
        self.y = y
        self.ttl = ttl

    def distance_sq(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    # 盾（青い本体＋淡い十字の紋章）を描く
    def draw(self, surface):
        cx, cy = theme.to_screen(self.x, self.y)
        pts = [(cx - 8, cy - 9), (cx + 8, cy - 9), (cx + 8, cy + 1),
               (cx, cy + 10), (cx - 8, cy + 1)]
        pygame.draw.polygon(surface, theme.SHIELD_BODY, pts)
        pygame.draw.polygon(surface, theme.SHIELD_EMBLEM, pts, 2)
        # 十字の紋章
        pygame.draw.line(surface, theme.SHIELD_EMBLEM, (cx, cy - 6), (cx, cy + 5), 2)
        pygame.draw.line(surface, theme.SHIELD_EMBLEM, (cx - 5, cy - 2), (cx + 5, cy - 2), 2)


CAPACITY = 2               # 同時に出現しうるシールドの数（将来ショップで増やす想定）
SPAWN_STAGGER = 4.0        # 各スポナーの初回出現をずらす間隔(秒)


# 1スポナー分の状態（盤面上のシールド1個と、その再出現タイマー）。A/B…は同じこのクラスで動く。
class _Spawner:
    def __init__(self, initial_timer):
        self.item = None
        self.timer = initial_timer


# シールドの出現・寿命・取得・効果（ブロック破壊突破）を管理する。
# CAPACITY 個のスポナーが独立に回る。効果は全体で1つの共有で、どれかを拾うと満タンから
# 再カウントし、所有スポナーだけが効果中は再出現しない。
class ShieldManager:
    def __init__(self, snake, food, obstacles, settings, duration_source=None):
        self.snake = snake
        self.food = food
        self.obstacles = obstacles
        self.settings = settings
        # 効果中に拾うと持続が伸びるアイテム（DurationBoostEffect）。None なら等倍。
        self.duration_source = duration_source
        self.visible = True
        self.capacity = CAPACITY
        self.active_timer = 0.0
        self.active_owner = -1
        self.spawners = []
        self._build_spawners()

    def _build_spawners(self):
        # 初回はマグネットとずらし、さらにスポナー同士もずらす
        self.spawners = [_Spawner(INITIAL_OFFSET + i * SPAWN_STAGGER)
                         for i in range(self.capacity)]
        self.active_timer = 0.0
        self.active_owner = -1

    @property
    def active(self):
        return self.active_timer > 0

    def _next_interval(self):
        return SPAWN_INTERVAL + random.uniform(-SPAWN_JITTER, SPAWN_JITTER)

    def _make_item(self):
        ttl = ITEM_LIFETIME * self.settings.difficulty.item_duration_scale  # EASY長/HARD短
        for _ in range(MAX_TRIES):
            x = random.randrange(-290, 291, GRID)
            y = random.randrange(-290, 291, GRID)
            it = ShieldItem(x, y, ttl)
            if self._placeable(it):
                return it
        return None

    def _placeable(self, it):
        if it.distance_sq(self.snake.head) < HEAD_CLEARANCE_SQ:
            return False
        for segment in self.snake.segments:
            if it.distance_sq(segment) < SAFE_DISTANCE_SQ:
                return False
        for f in self.food.foods:
            if it.distance_sq(f) < GRID_SQ:
                return False
        for block in self.obstacles.blocks:
            if it.distance_sq(block) < GRID_SQ:
                return False
        # 既に出ている他のシールドと被らない
        for sp in self.spawners:
            if sp.item is not None and it.distance_sq(sp.item) < GRID_SQ:
                return False
        return True

    # 拾われた時: 効果を満タンから再発動し、所有権を i へ移す（A効果中にBを拾うと上書き）
    def _pick_up(self, i):
        if 0 <= self.active_owner < len(self.spawners) and self.active_owner != i:
            self.spawners[self.active_owner].timer = self._next_interval()
        # 効果時間3倍アイテムが有効なら持続を伸ばす（拾った瞬間の倍率を反映）
        mult = self.duration_source.duration_multiplier if self.duration_source else 1
        self.active_timer = SHIELD_DURATION * self.settings.difficulty.item_duration_scale * mult
        self.active_owner = i

    def update(self, dt):
        if not self.settings.difficulty.has_shield:
            for sp in self.spawners:
                sp.item = None
            self.active_timer = 0.0
            self.active_owner = -1
            return

        if self.active_timer > 0:
            self.active_timer -= dt
            if self.active_timer <= 0:
                self.active_timer = 0.0
                if 0 <= self.active_owner < len(self.spawners):
                    self.spawners[self.active_owner].timer = self._next_interval()
                self.active_owner = -1

        head = self.snake.head
        for i, sp in enumerate(self.spawners):
            if i == self.active_owner:
                continue
            if sp.item is None:
                sp.timer -= dt
                if sp.timer <= 0:
                    sp.timer = self._next_interval()
                    sp.item = self._make_item()
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
        # 効果中は頭に青いバリア（脈動する円＋リング）を表示。
        # 残り BLINK_LAST 秒は点滅させて終了が近いことを知らせる。
        blink_on = self.active_timer >= BLINK_LAST or (pygame.time.get_ticks() // 180) % 2 == 0
        if self.active and blink_on:
            r = int(SIZE * 1.15)
            pulse = (math.sin(pygame.time.get_ticks() * 0.009) + 1) / 2
            alpha = int(45 + 55 * pulse)
            bubble = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
            c = (r + 3, r + 3)
            pygame.draw.circle(bubble, (*theme.SHIELD_AURA[:3], alpha), c, r)
            pygame.draw.circle(bubble, (*theme.SHIELD_AURA[:3], 220), c, r, 3)
            hx, hy = theme.to_screen(self.snake.head.x, self.snake.head.y)
            surface.blit(bubble, (hx - r - 3, hy - r - 3))
        for sp in self.spawners:
            if sp.item is not None:
                sp.item.draw(surface)
