import math
import random
import pygame
import theme
from snake import GRID, OFFSET, SIZE, DIRECTIONS, MAX_SCORE, TAIL_HIT_SQ

DEBRIS_COUNT = 8           # 破壊時に飛び散る破片の数
DEBRIS_TTL = 0.5           # 破片の寿命(秒)
BLAST_RESPAWN_PAUSE = 3.0  # ボムで全壊した後、レンガの再湧きを止める時間(秒)

SAFE_DISTANCE = SIZE        # 蛇のセグメントからこれ以上離す(px)
SAFE_DISTANCE_SQ = SAFE_DISTANCE * SAFE_DISTANCE
GRID_SQ = GRID * GRID
HEAD_CLEARANCE = 100        # 頭のすぐ近く(全方位)には置かない(px)
HEAD_CLEARANCE_SQ = HEAD_CLEARANCE * HEAD_CLEARANCE
AHEAD_LENGTH = 160          # 頭の進行方向の前方この距離は置かない(px)
AHEAD_WIDTH = 40            # 前方判定の帯の横幅(片側)(px)
LIFETIME_MIN = 8.0          # ブロックの寿命の下限(秒)
LIFETIME_MAX = 14.0          # 寿命の上限(秒)
MAX_TRIES = 60              # 配置先を探す試行回数

# 終盤(理論最大スコアに対する割合)で障害物を減らし、最後はゼロにする
FADE_START_FRAC = 0.5       # ここから減り始め
FADE_END_FRAC = 0.85        # ここで完全に消える（最後は詰まないよう障害物なし）


# 20x20px のレンガ1個。触れると game over。寿命(ttl)を持ち、切れたら作り直される。
class Block:
    def __init__(self, x, y, ttl):
        self.x = x
        self.y = y
        self.ttl = ttl

    def distance(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    # 二乗距離。しきい値との大小比較だけならsqrtを省ける
    def distance_sq(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    # レンガ風（テラコッタの本体＋モルタルの目地）を描く。
    # 2段のれんが積み: 上段は中央に縦目地、下段は端で割る（互い違い＝running bond）
    def draw(self, surface):
        cx, cy = theme.to_screen(self.x, self.y)
        half = SIZE / 2
        rect = pygame.Rect(cx - half, cy - half, SIZE, SIZE)
        m = theme.BRICK_MORTAR
        pygame.draw.rect(surface, theme.BRICK, rect)
        pygame.draw.line(surface, m, (rect.left, cy), (rect.right, cy), 2)        # 中央の横目地
        pygame.draw.line(surface, m, (cx, rect.top), (cx, cy), 2)                 # 上段: 中央の縦目地
        pygame.draw.line(surface, m, (cx - half, cy), (cx - half, rect.bottom), 2)
        pygame.draw.line(surface, m, (cx + half, cy), (cx + half, rect.bottom), 2)  # 下段: 端の縦目地
        pygame.draw.rect(surface, m, rect, 2)                                     # 外枠の目地


# 障害物（レンガ）をまとめて管理する。時間で湧き直し、終盤は数が減って消える。
class ObstacleManager:
    def __init__(self, snake, settings):
        self.snake = snake
        self.settings = settings
        # 盤面アイテム(magnet/shield)のマネージャ。snakegame.py で生成後にセットされ、
        # レンガがアイテムと同じセルに湧かないようにする
        self.item_managers = []
        self.visible = True
        self.blocks = []
        self.debris = []   # 破壊エフェクトの破片
        self.respawn_pause = 0.0  # ボム後の再湧き停止の残り時間
        self._populate()

    # --- 配置 ---
    def _make_block(self, food=None):
        for _ in range(MAX_TRIES):
            x = random.randrange(-290, 291, GRID)
            y = random.randrange(-290, 291, GRID)
            b = Block(x, y, random.uniform(LIFETIME_MIN, LIFETIME_MAX))
            if self._placeable(b, food):
                return b
        return None  # 空きが見つからない（盤面が混んでいる）

    def _placeable(self, b, food):
        hx, hy = self.snake.head.x, self.snake.head.y
        # 頭のすぐ近く（全方位）は不可（二乗距離で比較してsqrtを省く）
        dx, dy = b.x - hx, b.y - hy
        if dx * dx + dy * dy < HEAD_CLEARANCE_SQ:
            return False
        # 頭の進行方向の前方の帯は不可（避けようがない位置に湧かせない）
        ux, uy = DIRECTIONS[self.snake.heading]
        forward = dx * ux + dy * uy          # 前方成分
        lateral = abs(dx * -uy + dy * ux)    # 横方向の距離
        if 0 < forward < AHEAD_LENGTH and lateral < AHEAD_WIDTH:
            return False
        # 蛇の体
        for segment in self.snake.segments:
            if b.distance_sq(segment) < SAFE_DISTANCE_SQ:
                return False
        # food（ボーナスオーブ含む。同じセル不可）
        if food:
            for f in food.foods:
                if b.distance_sq(f) < GRID_SQ:
                    return False
            if food.bonus is not None and b.distance_sq(food.bonus) < GRID_SQ:
                return False
        # 他のレンガ（同じセル不可、隣接は許容）
        for other in self.blocks:
            if other.distance_sq(b) < GRID_SQ:
                return False
        # 盤面に出ている magnet/shield（同じセル不可）
        for mgr in self.item_managers:
            for item in mgr.items_on_board():
                if b.distance_sq(item) < GRID_SQ:
                    return False
        return True

    def _populate(self, food=None):
        self.blocks = []
        for _ in range(self.settings.difficulty.obstacle_count):
            b = self._make_block(food)
            if b:
                self.blocks.append(b)

    # 終盤で減らすための目標数（スコアが理論最大に近づくほど減り、最後は0）
    def _target_count(self, score):
        base = self.settings.difficulty.obstacle_count
        frac = score / MAX_SCORE
        if frac <= FADE_START_FRAC:
            return base
        if frac >= FADE_END_FRAC:
            return 0
        t = (FADE_END_FRAC - frac) / (FADE_END_FRAC - FADE_START_FRAC)
        return round(base * t)

    # 頭に重なるブロックをシールドで破壊する（破片エフェクト付き）。壊したら True
    def break_block_at(self, head):
        for block in self.blocks:
            if head.distance_sq(block) < TAIL_HIT_SQ:
                self.blocks.remove(block)
                self._spawn_debris(block.x, block.y)
                return True
        return False

    # ボム用: 全レンガを破壊して個数を返す（破片エフェクト付き）。
    # 直後に湧き直すと爽快感が無いので、しばらく再湧きを止める
    def blast_all(self):
        count = len(self.blocks)
        for block in self.blocks:
            self._spawn_debris(block.x, block.y)
        self.blocks = []
        if count:
            self.respawn_pause = BLAST_RESPAWN_PAUSE
        return count

    def _spawn_debris(self, x, y):
        for _ in range(DEBRIS_COUNT):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(60, 200)
            self.debris.append({
                "x": x, "y": y,
                "vx": math.cos(ang) * spd, "vy": math.sin(ang) * spd,
                "ttl": DEBRIS_TTL, "size": random.randint(3, 6),
            })

    # 毎フレーム: 寿命を減らし、切れたものは消し、目標数に合わせて作り直す
    def update(self, dt, score, food):
        target = self._target_count(score)
        for block in self.blocks:
            block.ttl -= dt
        # 寿命切れを除去（あとで目標数まで新しい場所に作り直される）
        self.blocks = [b for b in self.blocks if b.ttl > 0]
        # 多すぎるぶんは古い順に消す
        while len(self.blocks) > target:
            self.blocks.pop(0)
        # 足りないぶんは新しい場所に湧かせる（ボム直後の停止時間中は湧かせない）
        if self.respawn_pause > 0:
            self.respawn_pause = max(0.0, self.respawn_pause - dt)
        else:
            while len(self.blocks) < target:
                b = self._make_block(food)
                if b is None:
                    break
                self.blocks.append(b)
        # 破片を進める
        for p in self.debris:
            p["ttl"] -= dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
        self.debris = [p for p in self.debris if p["ttl"] > 0]

    # --- 表示 ---
    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    # リトライ・難易度変更後の開始時に置き直す（現在の難易度の数で）
    def reset(self):
        self.visible = True
        self.debris = []
        self.respawn_pause = 0.0
        self._populate()

    def draw(self, surface):
        if not self.visible:
            return
        for block in self.blocks:
            block.draw(surface)
        # 破壊の破片（縮みながら消える）
        for p in self.debris:
            s = max(1, int(p["size"] * (p["ttl"] / DEBRIS_TTL)))
            cx, cy = theme.to_screen(p["x"], p["y"])
            pygame.draw.rect(surface, theme.BRICK, (cx - s / 2, cy - s / 2, s, s))
