import math
import random
import pygame
import theme
from snake import GRID, SIZE, TAIL_HIT_SQ, WALL, DIRECTIONS

SPAWN_INTERVAL = 9.0       # フレイムが湧くまでの基本間隔(秒)
SPAWN_JITTER = 4.0         # 間隔のばらつき(±秒)。他アイテムと出現タイミングをずらす
INITIAL_OFFSET = 6.5       # 初回は magnet/shield と初手をずらして同時出現を避ける
ITEM_LIFETIME = 8.0        # 拾われずに残れる寿命(秒)
FLAME_DURATION = 12.0      # 効果の持続時間(秒) ※シールドと同じ長さ
BLINK_LAST = 3.0           # 効果が切れる前この秒数だけ体の赤みを点滅させる（他アイテムと同仕様）

# ★射撃インターバル: 効果中はこの秒数ごとに前方へ弾を1発撃つ。ここを変えて調節する。
FIRE_INTERVAL = 0.3

# ★弾の速さ: スネークの速度に対する倍率。1.0で蛇と同速、大きいほど速い。
BULLET_SPEED_FACTOR = 2.6
BULLET_RADIUS = 5          # 弾の描画半径(px)

HEAD_CLEARANCE_SQ = 30 * 30
SAFE_DISTANCE_SQ = SIZE * SIZE
GRID_SQ = GRID * GRID
MAX_TRIES = 60

CAPACITY = 3               # 同時に出現しうるフレイムの数（将来ショップで増やす想定）
SPAWN_STAGGER = 4.0        # 各スポナーの初回出現をずらす間隔(秒)


# 炎のアイコン形状を (cx, cy) 中心に描く共通ヘルパ（盤面アイテム・弾で共用）。
# 外炎(濃オレンジ)→中炎(オレンジ)→芯(黄)の3層を重ね、揺らぎのある炎らしい形にする。
def _draw_flame(surface, cx, cy, s):
    # 外炎: 左右非対称に揺れる炎の輪郭（下がふくらみ上が尖る）
    outer = [
        (cx, cy - 12 * s),
        (cx + 4 * s, cy - 5 * s),
        (cx + 8 * s, cy + 2 * s),
        (cx + 6 * s, cy + 8 * s),
        (cx, cy + 11 * s),
        (cx - 6 * s, cy + 8 * s),
        (cx - 8 * s, cy + 1 * s),
        (cx - 3 * s, cy - 4 * s),
    ]
    pygame.draw.polygon(surface, theme.FLAME_ICON, outer)
    # 中炎: ひとまわり内側のオレンジ
    mid = [
        (cx + 1 * s, cy - 6 * s),
        (cx + 5 * s, cy + 2 * s),
        (cx + 3 * s, cy + 7 * s),
        (cx - 2 * s, cy + 8 * s),
        (cx - 5 * s, cy + 2 * s),
        (cx - 1 * s, cy - 2 * s),
    ]
    pygame.draw.polygon(surface, theme.FLAME_MID, mid)
    # 芯: 明るい黄の炎（下寄りの雫形）
    core = [(cx, cy - 1 * s), (cx + 3 * s, cy + 4 * s), (cx, cy + 8 * s), (cx - 3 * s, cy + 4 * s)]
    pygame.draw.polygon(surface, theme.FLAME_ICON_CORE, core)


# 蛇が触れると、一定時間 前方へ火の弾を撃ち続けてレンガを破壊するアイテム
class FlameItem:
    def __init__(self, x, y, ttl):
        self.x = x
        self.y = y
        self.ttl = ttl

    def distance_sq(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    def draw(self, surface):
        cx, cy = theme.to_screen(self.x, self.y)
        _draw_flame(surface, cx, cy, 1.0)


# 1スポナー分の状態（盤面上のフレイム1個と、その再出現タイマー）。
class _Spawner:
    def __init__(self, initial_timer):
        self.item = None
        self.timer = initial_timer


# フレイムの出現・寿命・取得・効果（前方へ火の弾を撃つ）を管理する。
# 構造は ShieldManager と同じ: CAPACITY 個のスポナーが独立に回り、効果は全体で1つの共有。
# 効果中は FIRE_INTERVAL ごとに頭の前方へ弾を発射。弾は蛇より少し速く飛び、最初に当たった
# レンガ1個を壊して消える（貫通しない）。壊したレンガぶんの得点を加える。
class FlameManager:
    def __init__(self, snake, food, obstacles, settings, score_counter,
                 double_source, duration_source=None):
        self.snake = snake
        self.food = food
        self.obstacles = obstacles
        self.settings = settings
        self.score_counter = score_counter
        self.double_source = double_source      # ポイント二倍効果（得点倍率の供給元）
        # 効果中に拾うと持続が伸びるアイテム（DurationBoostEffect）。None なら等倍。
        self.duration_source = duration_source
        self.visible = True
        self.capacity = CAPACITY
        # 重なり禁止の相手マネージャ（magnet/shield）。snakegame.py で生成後にセットされる
        self.peers = []
        self.active_timer = 0.0
        self.active_owner = -1
        self.fire_timer = 0.0
        self.bullets = []   # 飛翔中の弾 [{x, y, ux, uy}]
        self.spawners = []
        self._build_spawners()

    def _build_spawners(self):
        self.spawners = [_Spawner(INITIAL_OFFSET + i * SPAWN_STAGGER)
                         for i in range(self.capacity)]
        self.active_timer = 0.0
        self.active_owner = -1
        self.fire_timer = 0.0
        self.bullets = []

    @property
    def active(self):
        return self.active_timer > 0

    # 効果時間3倍ポーションを発動中に飲んだ時: 残り時間を伸ばす
    def extend_active(self, mult):
        if self.active_timer > 0:
            self.active_timer *= mult

    def _next_interval(self):
        return SPAWN_INTERVAL + random.uniform(-SPAWN_JITTER, SPAWN_JITTER)

    def _make_item(self):
        ttl = ITEM_LIFETIME * self.settings.difficulty.item_duration_scale  # EASY長/HARD短
        for _ in range(MAX_TRIES):
            x = random.randrange(-290, 291, GRID)
            y = random.randrange(-290, 291, GRID)
            it = FlameItem(x, y, ttl)
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
        if self.food.bonus is not None and it.distance_sq(self.food.bonus) < GRID_SQ:
            return False
        for block in self.obstacles.blocks:
            if it.distance_sq(block) < GRID_SQ:
                return False
        # 既に出ている他のフレイムと被らない
        for sp in self.spawners:
            if sp.item is not None and it.distance_sq(sp.item) < GRID_SQ:
                return False
        # 盤面に出ている他種アイテム（magnet/shield）とも被らない
        for mgr in self.peers:
            for other in mgr.items_on_board():
                if it.distance_sq(other) < GRID_SQ:
                    return False
        return True

    # 盤面に出ているフレイムの一覧（他マネージャの重なりチェック用）
    def items_on_board(self):
        return [sp.item for sp in self.spawners if sp.item is not None]

    # 拾われた時: 効果を満タンから再発動し、所有権を i へ移す
    def _pick_up(self, i):
        if 0 <= self.active_owner < len(self.spawners) and self.active_owner != i:
            self.spawners[self.active_owner].timer = self._next_interval()
        mult = self.duration_source.duration_multiplier if self.duration_source else 1
        self.active_timer = FLAME_DURATION * self.settings.difficulty.item_duration_scale * mult
        self.active_owner = i
        self.fire_timer = 0.0  # 拾った直後に最初の一発

    # 前方へ弾を1発撃つ（頭の現在位置・向きから発射）
    def _fire(self):
        head = self.snake.head
        ux, uy = DIRECTIONS[self.snake.heading]
        self.bullets.append({"x": head.x, "y": head.y, "ux": ux, "uy": uy})

    # 弾を前進させ、レンガ命中・場外で消す。命中時は得点を加える。
    # 速い弾がフレーム間にレンガをすり抜けないよう、1フレームの移動を細かく分割して判定する。
    def _update_bullets(self, dt):
        speed = self.settings.speed * BULLET_SPEED_FACTOR
        travel = speed * dt
        if travel <= 0:
            return
        steps = max(1, int(travel / (GRID / 2)) + 1)
        sub = travel / steps
        alive = []
        for b in self.bullets:
            hit = False
            for _ in range(steps):
                b["x"] += b["ux"] * sub
                b["y"] += b["uy"] * sub
                if abs(b["x"]) > WALL or abs(b["y"]) > WALL:  # 壁の外に出たら消滅
                    hit = True
                    break
                block = self.obstacles.block_at(b["x"], b["y"])
                if block is not None:  # 最初に当たったレンガ1個を壊して消滅（貫通しない）
                    self.obstacles.destroy_block(block)
                    self.score_counter.count_brick(self.double_source.point_multiplier)
                    hit = True
                    break
            if not hit:
                alive.append(b)
        self.bullets = alive

    def update(self, dt):
        if not self.settings.difficulty.has_flame:
            self.bullets = []
            for sp in self.spawners:
                sp.item = None
            self.active_timer = 0.0
            self.active_owner = -1
            self.snake.heat = 0.0
            return

        # 飛翔中の弾を先に進める（効果が切れても残弾は飛び切る）
        self._update_bullets(dt)

        if self.active_timer > 0:
            self.active_timer -= dt
            # 効果中は一定間隔で撃ち続ける（1フレームで複数回来ても取りこぼさない）
            self.fire_timer -= dt
            while self.fire_timer <= 0:
                self.fire_timer += FIRE_INTERVAL
                self._fire()
            if self.active_timer <= 0:
                self.active_timer = 0.0
                if 0 <= self.active_owner < len(self.spawners):
                    self.spawners[self.active_owner].timer = self._next_interval()
                self.active_owner = -1

        # 頭周りのボディの赤み。残り BLINK_LAST 秒は点滅させて終了が近いことを知らせる。
        if self.active:
            blink_on = self.active_timer >= BLINK_LAST or (pygame.time.get_ticks() // 180) % 2 == 0
            self.snake.heat = 1.0 if blink_on else 0.0
        else:
            self.snake.heat = 0.0

        head = self.snake.head
        for i, sp in enumerate(self.spawners):
            if i == self.active_owner:
                continue
            if sp.item is None:
                # レンガがもう生成されない終盤は、壊す対象が無いので新規には出さない
                if not self.obstacles.generating:
                    continue
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
        self.snake.heat = 0.0
        self._build_spawners()

    def draw(self, surface):
        if not self.visible:
            return
        # 飛翔中の弾（火の玉＝オレンジの外縁＋黄の芯、後方に短い炎の尾）
        for b in self.bullets:
            cx, cy = theme.to_screen(b["x"], b["y"])
            # 尾（進行方向の後ろへ伸びる）
            tx, ty = theme.to_screen(b["x"] - b["ux"] * 10, b["y"] - b["uy"] * 10)
            pygame.draw.line(surface, theme.FLAME_MID, (tx, ty), (cx, cy), BULLET_RADIUS)
            pygame.draw.circle(surface, theme.FLAME_ICON, (cx, cy), BULLET_RADIUS)
            pygame.draw.circle(surface, theme.FLAME_ICON_CORE, (cx, cy), max(1, BULLET_RADIUS - 2))
        # 効果中は頭に小さな炎（銃口の火）を出して撃っていることを示す
        if self.active:
            flick = 0.85 + 0.3 * math.sin(pygame.time.get_ticks() * 0.03)
            hx, hy = theme.to_screen(self.snake.head.x, self.snake.head.y)
            _draw_flame(surface, hx, hy, 0.55 * flick)
        for sp in self.spawners:
            if sp.item is not None:
                sp.item.draw(surface)
