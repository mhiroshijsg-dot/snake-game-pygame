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

# 配置判定で繰り返し使うしきい値の二乗（sqrtを避ける。d<t ⇔ d²<t²）
SAFE_DISTANCE_SQ = SAFE_DISTANCE * SAFE_DISTANCE
FOOD_GAP_SQ = FOOD_GAP * FOOD_GAP
GRID_SQ = GRID * GRID


# オーブ外側の光のサーフェス（全オーブ共通）。pygame.display 初期化後の
# 初回描画時に一度だけ生成してキャッシュする。
_glow_cache = None


def _glow_surface():
    global _glow_cache
    if _glow_cache is None:
        glow_r = RADIUS * 2
        surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*theme.ORB_GLOW[:3], 90), (glow_r, glow_r), glow_r)
        _glow_cache = surf.convert_alpha()
    return _glow_cache


class Food:
    def __init__(self, snake=None, others=None, obstacles=None):
        self.x = 0
        self.y = 0
        self.refresh(snake, others, obstacles)

    # 配置先を探す試行回数。終盤は蛇が盤面をほぼ埋めて空きセルが無いことがあるため、
    # 無限ループ（フリーズ）にせず、前半は通常条件・後半は緩和条件で探して必ず抜ける
    MAX_TRIES = 300

    def refresh(self, snake=None, others=None, obstacles=None):
        # 蛇・他のfood・障害物に被らない場所を探して置き直す。
        # 頭と同じ格子(OFFSET基準: -290,-270,...,290)に置くので必ず到達して食べられる
        for tries in range(self.MAX_TRIES):
            self.x = random.randrange(-290, 291, GRID)
            self.y = random.randrange(-290, 291, GRID)
            if tries >= self.MAX_TRIES // 2:
                # 緩和: 蛇・他food との間隔条件は捨て、レンガの下に埋まることだけ避ける
                # （蛇に重なっても即食べられるだけで実害はない。フリーズより良い）
                if not self._overlaps_blocks(obstacles):
                    return
            elif ((snake is None or not self._overlaps_snake(snake))
                    and not self._overlaps_others(others)
                    and not self._overlaps_blocks(obstacles)):
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

    # 魔法のオーブを描く（外側のぼんやりした光＋紫の本体＋ハイライト）
    def draw(self, surface):
        cx, cy = theme.to_screen(self.x, self.y)
        # 外側の光: 全オーブで同一なのでサーフェスは一度だけ作って使い回す
        glow = _glow_surface()
        glow_r = RADIUS * 2
        surface.blit(glow, (cx - glow_r, cy - glow_r))
        # 本体
        pygame.draw.circle(surface, theme.FOOD_COLOR, (cx, cy), RADIUS)
        # ハイライト（左上の小さな光の点）
        pygame.draw.circle(surface, theme.ORB_HIGHLIGHT,
                           (cx - RADIUS * 0.35, cy - RADIUS * 0.35), RADIUS * 0.32)


# 複数の food をまとめて管理する（常に FOOD_COUNT 個を保つ）
FOOD_COUNT = 10


class FoodManager:
    def __init__(self, snake, obstacles=None):
        self.snake = snake
        self.obstacles = obstacles
        self.visible = True
        # 既に置いたfoodを others として渡し、重ならないように生成する
        self.foods = []
        for _ in range(FOOD_COUNT):
            self.foods.append(Food(snake, self.foods, obstacles))

    # 頭がどれか1つを食べたら True。食べた food は別の場所へ置き直す（数は変わらない）
    def check_eaten(self, head, eat_distance=EAT_DISTANCE):
        eat_sq = eat_distance * eat_distance  # sqrtを避けて二乗距離で比較
        for food in self.foods:
            if head.distance_sq(food) < eat_sq:
                food.refresh(self.snake, self.foods, self.obstacles)
                return True
        return False

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    # リトライ時: 全部表示して置き直す
    def reset(self):
        self.visible = True
        for food in self.foods:
            food.refresh(self.snake, self.foods, self.obstacles)

    def draw(self, surface):
        if not self.visible:
            return
        for food in self.foods:
            food.draw(surface)
