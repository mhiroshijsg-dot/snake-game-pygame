import math
import pygame
import theme

COLOR = theme.SNAKE_COLOR
SIZE = 20             # セグメント(四角)の一辺(px)
STEP = 2              # 1フレームの移動量(px) ※GRID/SPACINGの約数にすること。
                      # 小さいほどフレーム数が増えて滑らか（速度=fps*STEPは不変）
SPACING = 8           # セグメント間の距離(px) ※四角(20px)より小さくして重ねる
GRID = 20             # この格子点でだけ向きを変えられる(px)。直進は滑らか、角は直角
OFFSET = GRID // 2    # 格子を半マスずらす。これで頭は ±290(=画面端300−胴体半径10)に到達でき、
                      # 胴体が壁スレスレまで行ける（格子を原点基準にすると±280までしか届かない）
INITIAL_LENGTH = 8    # 開始時のセグメント数
WALL = 290            # 壁判定の座標。頭が±290なら胴体の端がちょうど画面端300に接する＝壁スレスレ
TAIL_HIT = SIZE * 0.8  # 尾との衝突と見なす中心間距離(px)。胴体幅(SIZE)基準
TAIL_HIT_SQ = TAIL_HIT * TAIL_HIT  # 二乗距離での比較用（sqrtを避ける。d<t ⇔ d²<t²）

# 位置履歴は STEP px刻みで貯め、各セグメントは SPACING px間隔の点を参照する。
# 1セグメントぶんの履歴点数。move/draw/prefill で繰り返し使うので定数化する。
HIST_PER = SPACING // STEP

# 盤面の格子セル数 = 理論上の最大の長さ(セグメント数)。これに達したらクリア。
MAX_LENGTH = (theme.PLAY_W // GRID) * (theme.PLAY_H // GRID)
MAX_SCORE = MAX_LENGTH - INITIAL_LENGTH  # 食べた数(スコア)の理論上限
# 盤面を幅GRID(20px)で埋め尽くす総延長(px)。クリア判定はこの「ヘビの全長」で行う。
# = MAX_LENGTH(900セル) × GRID(20px) = 18000px（点数とは無関係）
MAX_FILL_PX = MAX_LENGTH * GRID

# 各向き(度)に対応する単位移動ベクトル。cos/sinの誤差を避けて整数で進める
DIRECTIONS = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}


# turtle.Turtle の代わりに使う、位置と向きだけ持つ軽量なセグメント
class Segment:
    def __init__(self, x, y, heading=0.0):
        self.x = x
        self.y = y
        self.heading = heading  # 度。0=右, 90=上 (turtleと同じ向きの取り方)

    def distance(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    # 二乗距離。しきい値との大小比較だけならsqrtを省けるホットパス用
    def distance_sq(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy


class Snake:
    def __init__(self):
        self.segments = []
        self.position_history = []
        self.visible = True
        self.crashed = False  # 衝突したか（目の表情を切り替える）
        self.tint = None      # Noneなら通常色。色が入っていればボディ全体をその色で描く（効果中の表現）
        self.create_snake()
        self.head = self.segments[0]
        self.heading = 0    # 現在進んでいる向き（0/90/180/270）
        self.moves = []      # 次の格子点から順に適用する向きのキュー（先読み2手まで）
        self.head.heading = self.heading
        self.prefill_history()

    # 開始時の向きから「頭が通ってきたであろう座標」を逆算して履歴を埋める
    def prefill_history(self):
        ux, uy = DIRECTIONS[self.heading]
        dx, dy = ux * STEP, uy * STEP
        count = len(self.segments) * HIST_PER
        hx, hy = self.head.x, self.head.y
        # 頭の後ろ向き(-dx, -dy)に STEP 刻みで並べる
        self.position_history = [(hx - dx * j, hy - dy * j) for j in range(count + 1)]

    # DONE 1: create a snake body
    def create_snake(self):
        # 頭は格子点(OFFSET基準)から開始する。STEP=4で進むと OFFSET, OFFSET±20, ... と
        # 格子点に乗れる（原点0始まりだと10刻みの格子に永遠に乗れないため）
        for i in range(INITIAL_LENGTH):
            self.add_segment((OFFSET - SPACING * i, OFFSET))

    def add_segment(self, position):
        self.segments.append(Segment(position[0], position[1]))

    # 頭が格子点(OFFSET基準)に乗っているか
    def _on_grid(self):
        return (self.head.x - OFFSET) % GRID == 0 and (self.head.y - OFFSET) % GRID == 0

    # DONE 2: move the snake
    def move(self):
        # 格子点に着くたびにキューから1手取り出して向きを変える
        if self.moves and self._on_grid():
            d = self.moves.pop(0)
            if (d + 180) % 360 != self.heading:  # 念のため逆走は無視
                self.heading = d
                self.head.heading = self.heading

        ux, uy = DIRECTIONS[self.heading]
        head = self.head
        head.x += ux * STEP
        head.y += uy * STEP

        history = self.position_history
        history.insert(0, (head.x, head.y))

        segments = self.segments
        hist_len = len(segments) * HIST_PER
        if len(history) > hist_len:
            history.pop()

        # 各セグメントを HIST_PER 間隔の履歴点に合わせる（毎回の長さ・属性参照を巻き上げ）
        history_index = HIST_PER
        for segment in segments[1:]:
            if history_index < len(history):
                segment.x, segment.y = history[history_index]
            history_index += HIST_PER

    def increase_segments(self, count=1):
        for _ in range(count):
            last = self.segments[-1]
            self.add_segment((last.x, last.y))

    # 入力をキューに積む。キューの最後（無ければ現在の向き）を基準に、
    # 同方向・逆走は積まない。先読みは2手まで。
    def _queue(self, direction):
        reference = self.moves[-1] if self.moves else self.heading
        if direction == reference or (direction + 180) % 360 == reference:
            return
        if len(self.moves) < 2:
            self.moves.append(direction)

    def up(self):
        self._queue(90)

    def down(self):
        self._queue(270)

    def left(self):
        self._queue(180)

    def right(self):
        self._queue(0)

    # DONE 6: detect collision with wall
    def detect_wall(self):
        return (self.head.x > WALL or self.head.x < -WALL
                or self.head.y > WALL or self.head.y < -WALL)

    # DONE 7: detect collision with tail
    def detect_tail(self):
        # 頭に重なって見える近くのセグメント(四角の幅ぶん)は無視する
        skip = round(SIZE / SPACING)
        head = self.head
        for tail in self.segments[skip + 1:]:
            if head.distance_sq(tail) < TAIL_HIT_SQ:
                return True
        return False

    # 障害物(レンガ)との衝突。obstacles は ObstacleManager（blocks を持つ）
    def detect_block(self, obstacles):
        head = self.head
        for block in obstacles.blocks:
            if head.distance_sq(block) < TAIL_HIT_SQ:
                return True
        return False

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def reset(self):
        self.__init__()

    # 胴体は「当たり判定用のセグメント」ではなく、4px刻みの位置履歴の全点に
    # 丸を打って描く。点が密(STEP=4 < 直径SIZE)なので角も滑らかな丸い直角になり、
    # セグメント間隔(8px)が角で詰まって見えるカクつきが出ない。
    # さらに頭からの距離で色を切り替え、GRIDごとの縞模様をつける。
    def draw(self, surface):
        if not self.visible:
            return
        r = SIZE / 2
        per_band = GRID // STEP  # 1バンド=GRID(20px)ぶんの履歴点数
        hist = self.position_history
        # ホットループ用にグローバル/属性参照と座標変換の定数を巻き上げる
        draw_circle = pygame.draw.circle
        # 効果中(tintあり)はボディ全体を効果色に差し替える（縞模様は維持）
        if self.tint is not None:
            base_color = self.tint
            pattern_color = theme.SNAKE_BOOST_PATTERN
        else:
            base_color = COLOR
            pattern_color = theme.SNAKE_PATTERN
        ox = theme.PLAY_W / 2
        oy = theme.HUD_HEIGHT + theme.PLAY_H / 2
        # 尾→頭の順に描くと頭が一番上に来る
        for i in range(len(hist) - 1, -1, -1):
            x, y = hist[i]
            color = pattern_color if (i // per_band) % 2 == 1 else base_color
            draw_circle(surface, color, (ox + x, oy - y), r)  # to_screen をインライン化
        self._draw_eyes(surface, r)

    # 頭に進行方向を向いた2つの目を描く。
    # 通常は落ち着いた小さな目、衝突時(crashed)は白目を見開いた驚き顔。
    def _draw_eyes(self, surface, r):
        hx, hy = theme.to_screen(self.head.x, self.head.y)
        rad = math.radians(self.head.heading)
        # 画面座標は上下が反転するので y成分を反転して前方ベクトルを作る
        fx, fy = math.cos(rad), -math.sin(rad)
        px, py = -fy, fx  # 前方に対する横方向（左右の目をずらす）
        for side in (1, -1):
            ex = hx + fx * r * 0.45 + px * side * r * 0.40
            ey = hy + fy * r * 0.45 + py * side * r * 0.40
            if self.crashed:
                # 見開いた白目＋瞳
                pygame.draw.circle(surface, theme.BG, (ex, ey), r * 0.30)
                pygame.draw.circle(surface, theme.TEXT, (ex, ey), r * 0.30 * 0.55)
            else:
                # 落ち着いた小さな瞳のみ
                pygame.draw.circle(surface, theme.TEXT, (ex, ey), r * 0.16)
