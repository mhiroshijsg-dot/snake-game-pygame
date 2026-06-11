import math
import random
import pygame
import theme
from snake import GRID


SAFE_DISTANCE = 20  # 蛇の各セグメントからこれ以上離す(px)
FOOD_GAP = 40       # food同士をこれ以上離す(px) ※格子(GRID)の2マス分
RADIUS = 6          # オーブ本体の半径(px)
# 食べたと見なす距離。スネークもfoodも同じGRID格子上にあるので、
# 半マス未満まで近づけば「同じマス＝食べた」と判定できる（難易度非依存）
EAT_DISTANCE = GRID / 2

# ボーナスオーブ（金色・獲得ポイント5倍。蛇の伸びは普通のオーブと同じ）。
# magnet/shield と同じ「時々湧いて寿命で消える」アイテム型。
# 出現頻度は旧実装（オーブ10個中5%が金）と同じくらいの体感になるよう調整してある
BONUS_MULTIPLIER = 5       # 獲得ポイントの倍率
BONUS_SPAWN_MIN = 12.0     # 次が湧くまでの間隔の下限(秒)
BONUS_SPAWN_MAX = 22.0     # 間隔の上限(秒)
BONUS_LIFETIME = 6.0       # 拾われずに残れる寿命(秒)

# 配置判定で繰り返し使うしきい値の二乗（sqrtを避ける。d<t ⇔ d²<t²）
SAFE_DISTANCE_SQ = SAFE_DISTANCE * SAFE_DISTANCE
FOOD_GAP_SQ = FOOD_GAP * FOOD_GAP
GRID_SQ = GRID * GRID


# オーブ外側の光のサーフェス（色ごとに1枚）。pygame.display 初期化後の
# 初回描画時に一度だけ生成してキャッシュする。
_glow_cache = {}


def _glow_surface(color):
    key = tuple(color[:3])
    if key not in _glow_cache:
        glow_r = RADIUS * 2
        surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*key, 90), (glow_r, glow_r), glow_r)
        _glow_cache[key] = surf.convert_alpha()
    return _glow_cache[key]


class Food:
    def __init__(self, snake=None, others=None, obstacles=None, items=None):
        self.x = 0
        self.y = 0
        self.points_multiplier = 1
        self.refresh(snake, others, obstacles, items)

    # 配置先を探す試行回数。終盤は蛇が盤面をほぼ埋めて空きセルが無いことがあるため、
    # 無限ループ（フリーズ）にせず、前半は通常条件・後半は緩和条件で探して必ず抜ける
    MAX_TRIES = 300

    def refresh(self, snake=None, others=None, obstacles=None, items=None):
        # 蛇・他のfood・障害物・盤面アイテム(magnet/shield)に被らない場所を探して置き直す。
        # 頭と同じ格子(OFFSET基準: -290,-270,...,290)に置くので必ず到達して食べられる
        for tries in range(self.MAX_TRIES):
            self.x = random.randrange(-290, 291, GRID)
            self.y = random.randrange(-290, 291, GRID)
            if tries >= self.MAX_TRIES // 2:
                # 緩和: 蛇・他food との間隔条件は捨て、レンガ・アイテムに埋まることだけ避ける
                # （蛇に重なっても即食べられるだけで実害はない。フリーズより良い）
                if not self._overlaps_blocks(obstacles) and not self._overlaps_items(items):
                    return
            elif ((snake is None or not self._overlaps_snake(snake))
                    and not self._overlaps_others(others)
                    and not self._overlaps_blocks(obstacles)
                    and not self._overlaps_items(items)):
                return
        # ここまで来たら空きが見つからないほど盤面が埋まっている。最後の乱数位置で確定

    def distance(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    # 二乗距離。しきい値との大小比較だけならsqrtを省ける
    def distance_sq(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    def _overlaps_snake(self, snake):
        for segment in snake.segments:
            if self.distance_sq(segment) < SAFE_DISTANCE_SQ:
                return True
        return False

    def _overlaps_others(self, others):
        if not others:
            return False
        for food in others:
            if food is not self and self.distance_sq(food) < FOOD_GAP_SQ:
                return True
        return False

    def _overlaps_blocks(self, obstacles):
        if not obstacles:
            return False
        for block in obstacles.blocks:
            if self.distance_sq(block) < GRID_SQ:  # レンガと同じセルは不可
                return True
        return False

    def _overlaps_items(self, items):
        # 盤面に出ている magnet/shield と同じセルは不可
        if not items:
            return False
        for item in items:
            if self.distance_sq(item) < GRID_SQ:
                return True
        return False

    # 魔法のオーブを描く（外側のぼんやりした光＋本体＋ハイライト）。
    # ボーナスオーブ（5倍点）は金色で描いて見分けがつくようにする
    def draw(self, surface):
        cx, cy = theme.to_screen(self.x, self.y)
        bonus = self.points_multiplier > 1
        glow_color = theme.GOLD if bonus else theme.ORB_GLOW
        body_color = theme.GOLD if bonus else theme.FOOD_COLOR
        # 外側の光: 色ごとにサーフェスを一度だけ作って使い回す
        glow = _glow_surface(glow_color)
        glow_r = RADIUS * 2
        surface.blit(glow, (cx - glow_r, cy - glow_r))
        # 本体
        pygame.draw.circle(surface, body_color, (cx, cy), RADIUS)
        # ハイライト（左上の小さな光の点）
        pygame.draw.circle(surface, theme.ORB_HIGHLIGHT,
                           (cx - RADIUS * 0.35, cy - RADIUS * 0.35), RADIUS * 0.32)


# 金色のボーナスオーブ。Food の描画（金色）と距離計算を継承し、寿命(ttl)を持つ
class BonusOrb(Food):
    def __init__(self, ttl):
        self.x = 0
        self.y = 0
        self.points_multiplier = BONUS_MULTIPLIER
        self.ttl = ttl


# 複数の food をまとめて管理する（常に FOOD_COUNT 個を保つ）
FOOD_COUNT = 10


class FoodManager:
    def __init__(self, snake, obstacles=None):
        self.snake = snake
        self.obstacles = obstacles
        # 盤面アイテム(magnet/shield)のマネージャ。snakegame.py で生成後にセットされ、
        # オーブがアイテムと同じセルに湧かないようにする
        self.item_managers = []
        self.visible = True
        # 既に置いたfoodを others として渡し、重ならないように生成する
        self.foods = []
        for _ in range(FOOD_COUNT):
            self.foods.append(Food(snake, self.foods, obstacles))
        # ボーナスオーブ（盤面に同時に最大1個。タイマーで湧き、寿命で消える）
        self.bonus = None
        self.bonus_timer = self._next_bonus_interval()

    def _next_bonus_interval(self):
        return random.uniform(BONUS_SPAWN_MIN, BONUS_SPAWN_MAX)

    # 毎フレーム: ボーナスオーブの出現と寿命を進める（通常オーブは食べられた時だけ動く）
    def update(self, dt):
        if self.bonus is None:
            self.bonus_timer -= dt
            if self.bonus_timer <= 0:
                self.bonus_timer = self._next_bonus_interval()
                bonus = BonusOrb(BONUS_LIFETIME)
                # 通常オーブと同じ配置ロジックで蛇・food・レンガ・アイテムを避ける
                bonus.refresh(self.snake, self.foods, self.obstacles, self._items_on_board())
                self.bonus = bonus
        else:
            self.bonus.ttl -= dt
            if self.bonus.ttl <= 0:
                self.bonus = None

    # 盤面に出ている magnet/shield の一覧（配置の重なりチェック用）
    def _items_on_board(self):
        items = []
        for mgr in self.item_managers:
            items.extend(mgr.items_on_board())
        return items

    # 頭がどれか1つを食べたら、そのオーブの得点倍率(通常1/ボーナス5)を返す。食べていなければ 0。
    # 食べた food は別の場所へ置き直す（数は変わらない）。ボーナスは消えて次のタイマーが始まる
    def check_eaten(self, head, eat_distance=EAT_DISTANCE):
        eat_sq = eat_distance * eat_distance  # sqrtを避けて二乗距離で比較
        if self.bonus is not None and head.distance_sq(self.bonus) < eat_sq:
            self.bonus = None
            self.bonus_timer = self._next_bonus_interval()
            return BONUS_MULTIPLIER
        for food in self.foods:
            if head.distance_sq(food) < eat_sq:
                food.refresh(self.snake, self.foods, self.obstacles, self._items_on_board())
                return 1
        return 0

    # スーパーマグネット用: 盤面の全オーブ（ボーナス含む）を回収し、
    # (x, y, 得点倍率) のリストを返す。通常オーブは別の場所へ置き直し（数は不変）、
    # ボーナスは消えて次の出現タイマーが始まる
    def collect_all(self):
        collected = [(f.x, f.y, 1) for f in self.foods]
        if self.bonus is not None:
            collected.append((self.bonus.x, self.bonus.y, BONUS_MULTIPLIER))
            self.bonus = None
            self.bonus_timer = self._next_bonus_interval()
        items = self._items_on_board()
        for food in self.foods:
            food.refresh(self.snake, self.foods, self.obstacles, items)
        return collected

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    # リトライ時: 全部表示して置き直す（ボーナスは消してタイマーから再スタート）
    def reset(self):
        self.visible = True
        self.bonus = None
        self.bonus_timer = self._next_bonus_interval()
        items = self._items_on_board()
        for food in self.foods:
            food.refresh(self.snake, self.foods, self.obstacles, items)

    def draw(self, surface):
        if not self.visible:
            return
        for food in self.foods:
            food.draw(surface)
        if self.bonus is not None:
            self.bonus.draw(surface)
