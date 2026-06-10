import math
import pygame
from button import Button
from food import Food, BONUS_MULTIPLIER
from snake import GRID, STEP
from obstacle import Block
from magnet import Magnet
from shield import ShieldItem
from items import draw_item_icon
from shop_screen import SHOP_ITEMS
import theme

ART_Y = 40  # 各ページのイラストを描く中心の世界座標Y


# チュートリアル / How to Play で共用するスライド一式（ページ内容＋イラスト描画）。
# ページ = (タイトル, 本文の行リスト, イラストキー)。
# potion の詳しい説明ページは How to Play 用に pages(users) で後ろに足される
# （チュートリアルでは出さない＝ショップの初回開放演出に委ねる）。
class SlideDeck:
    PAGES = [
        ("Welcome!",
         ["The snake is always moving — it never stops.",
          "Arrow keys don't push it step by step:",
          "they pick the direction it keeps traveling.",
          "Press UP once and it turns and keeps going up!"],
         "steer"),
        ("Eat Orbs",
         ["Orbs make you grow and earn points.",
          "A golden orb appears once in a while —",
          "worth 5x points! Grab it before it fades."],
         "orbs"),
        ("Watch Out!",
         ["Walls, your own tail, and brick blocks",
          "end the game on touch.",
          "Bricks crumble and respawn over time."],
         "bricks"),
        ("Field Items",
         ["Magnet: pulls in orbs from afar for a while.",
          "Shield: smash through bricks for a while.",
          "Just run into them to activate."],
         "items"),
        ("Scoring",
         ["Harder difficulties pay more per orb.",
          "Smashing a brick with a shield scores",
          "even more than an orb. Potions help too!"],
         "score"),
        ("Controls",
         ["Press the S key to start, R to retry,",
          "and Q to quit the game.",
          "Press the 1-4 keys to drink a potion",
          "from the bottom item bar."],
         "keys"),
        ("Settings & Shop",
         ["The gear icon opens settings:",
          "change difficulty or switch players.",
          "Spend your points on potions in the SHOP —",
          "new potions unlock as your best score grows!"],
         "settings"),
        ("One more thing...",
         ["Fill the entire board with your snake",
          "and... something special might happen.",
          "Good luck!"],
         "secret"),
    ]

    def __init__(self):
        # イラストに使う実物（Foodの倍率を固定して通常/ボーナスを描き分ける）
        orb = Food()
        orb.points_multiplier = 1
        bonus = Food()
        bonus.points_multiplier = BONUS_MULTIPLIER
        self._icons = {"orb": orb, "bonus": bonus, "brick": Block(0, 0, 1),
                       "magnet": Magnet(0, 0, 1), "shield": ShieldItem(0, 0, 1)}

    # 表示するページ一覧。users を渡すと、開放済み（seen）のポーションの
    # 説明ページが後ろに足される（How to Play 用）
    def pages(self, users=None):
        result = list(self.PAGES)
        if users is not None:
            for item in SHOP_ITEMS:
                if users.has_seen_item(item["key"]):
                    result.append((item["name"], item["desc"], "potion:" + item["key"]))
        return result

    # 1ページぶんの中身（タイトル・イラスト・本文）を描く。ボタン類は呼び出し側が描く
    def draw_page(self, surface, page):
        title, lines, art = page
        theme.draw_text(surface, title, 0, 195, theme.TEXT, theme.FONT_BIG)
        if art:
            self._draw_art(surface, art)
        y = -50
        for line in lines:
            theme.draw_text(surface, line, 0, y, theme.TEXT, theme.FONT_NAME_SMALL)
            y -= 30

    # --- 各ページのイラスト ---
    def _draw_art(self, surface, key):
        if key == "steer":
            self._draw_steer_art(surface)
        elif key == "keys":
            self._draw_keys_art(surface)
        elif key == "settings":
            self._draw_settings_art(surface)
        elif key == "orbs":
            self._place(surface, "orb", -70, ART_Y)
            self._place(surface, "bonus", 70, ART_Y)
            theme.draw_text(surface, "x1", -70, ART_Y - 35, theme.TEXT_DIM, theme.FONT_SCORE)
            theme.draw_text(surface, "x5!", 70, ART_Y - 35, theme.GOLD, theme.FONT_BUTTON)
        elif key == "bricks":
            for x in (-50, -25, 0, 25, 50):
                self._place(surface, "brick", x, ART_Y)
        elif key == "items":
            self._place(surface, "magnet", -70, ART_Y)
            self._place(surface, "shield", 70, ART_Y)
        elif key == "score":
            # オーブ < レンガ破壊 の得点感を並べて見せる
            self._place(surface, "orb", -90, ART_Y)
            theme.draw_text(surface, "+pts", -90, ART_Y - 35, theme.TEXT_DIM, theme.FONT_SCORE)
            self._place(surface, "shield", 35, ART_Y)
            self._place(surface, "brick", 90, ART_Y)
            theme.draw_text(surface, "+more!", 65, ART_Y - 35, theme.GOLD, theme.FONT_BUTTON)
        elif key == "secret":
            # 盤面が蛇色で埋まったミニボード＋金の「?」で匂わせる
            cx, cy = theme.to_screen(0, ART_Y)
            rect = pygame.Rect(0, 0, 120, 120)
            rect.center = (cx, cy)
            pygame.draw.rect(surface, theme.SNAKE_COLOR, rect, border_radius=10)
            pygame.draw.rect(surface, theme.SNAKE_PATTERN, rect, width=4, border_radius=10)
            theme.draw_text(surface, "?", 0, ART_Y, theme.GOLD, theme.FONT_TITLE)
        elif key.startswith("potion:"):
            cx, cy = theme.to_screen(0, ART_Y + 20)
            draw_item_icon(surface, key.split(":", 1)[1], int(cx), int(cy), scale=2.2)

    def _place(self, surface, key, x, y):
        item = self._icons[key]
        item.x, item.y = x, y
        item.draw(surface)

    # キーキャップ（角丸の四角＋ラベルまたは矢印三角）を描く共通ヘルパ
    def _draw_keycap(self, surface, x, y, label, size=34, highlight=False):
        cx, cy = theme.to_screen(x, y)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        fill = theme.PRIMARY if highlight else theme.SECONDARY
        pygame.draw.rect(surface, fill, rect, border_radius=7)
        if label in ("up", "down", "left", "right"):
            d = size * 0.22  # 矢印三角の大きさ
            pts = {"up":    [(cx, cy - d), (cx - d, cy + d * 0.7), (cx + d, cy + d * 0.7)],
                   "down":  [(cx, cy + d), (cx - d, cy - d * 0.7), (cx + d, cy - d * 0.7)],
                   "left":  [(cx - d, cy), (cx + d * 0.7, cy - d), (cx + d * 0.7, cy + d)],
                   "right": [(cx + d, cy), (cx - d * 0.7, cy - d), (cx - d * 0.7, cy + d)]}
            pygame.draw.polygon(surface, theme.BUTTON_TEXT, pts[label])
        else:
            theme.draw_text(surface, label, x, y, theme.BUTTON_TEXT, theme.FONT_BUTTON)

    # 蛇の胴体を経路に沿って本物と同じ描き方（2px間隔の円・20pxごとの縞バンド）で描く。
    # points は尾→頭の順の座標列。最後の点が頭で、heading の向きに目を付ける
    def _draw_snake_body(self, surface, points, heading):
        r = 10
        per_band = GRID // STEP  # 本物と同じ: 10点で1バンド
        last = len(points) - 1
        for i in range(last, -1, -1):  # 尾→頭の順に描いて頭を一番上にする
            x, y = points[i]
            color = theme.SNAKE_PATTERN if ((last - i) // per_band) % 2 == 1 else theme.SNAKE_COLOR
            cx, cy = theme.to_screen(x, y)
            pygame.draw.circle(surface, color, (cx, cy), r)
        # 目（snake.py の _draw_eyes と同じ配置・サイズ）
        hx, hy = theme.to_screen(*points[-1])
        rad = math.radians(heading)
        fx, fy = math.cos(rad), -math.sin(rad)
        px, py = -fy, fx
        for side in (1, -1):
            ex = hx + fx * r * 0.45 + px * side * r * 0.40
            ey = hy + fy * r * 0.45 + py * side * r * 0.40
            pygame.draw.circle(surface, theme.TEXT, (ex, ey), r * 0.16)

    # 1ページ目: 「矢印は進む向きを決める」の図解。
    # 左に矢印キー（↑だけ強調）、右にL字に曲がって上へ進み続ける蛇＋点線の進路
    def _draw_steer_art(self, surface):
        # 矢印キー（十字配置。↑をハイライト）
        kx, ky = -150, ART_Y - 10
        self._draw_keycap(surface, kx, ky + 38, "up", highlight=True)
        self._draw_keycap(surface, kx - 38, ky, "left")
        self._draw_keycap(surface, kx, ky, "down")
        self._draw_keycap(surface, kx + 38, ky, "right")
        theme.draw_text(surface, "press UP...", kx, ky + 72, theme.PRIMARY, theme.FONT_SCORE)

        # L字の蛇: 右へ進んできて、↑で曲がって上へ進み続けている途中
        y0 = ART_Y - 40   # 水平部分の高さ
        bend_x = 80       # 曲がり角のX
        points = [(x, y0) for x in range(-30, bend_x + 1, 2)]          # 尾→曲がり角
        points += [(bend_x, y) for y in range(y0 + 2, y0 + 81, 2)]     # 曲がり角→頭(上向き)
        self._draw_snake_body(surface, points, heading=90)
        # 頭の先の進路を点線の丸＋矢印で示す（このまま上へ進み続ける）
        hx, hy = theme.to_screen(bend_x, y0 + 80)
        for k in range(1, 4):
            pygame.draw.circle(surface, theme.TEXT_DIM, (hx, hy - 16 * k), 4)
        pygame.draw.polygon(surface, theme.PRIMARY,
                            [(hx, hy - 16 * 4 - 12), (hx - 10, hy - 16 * 4 + 2),
                             (hx + 10, hy - 16 * 4 + 2)])

    # Controls ページ: S/R/Q のキーキャップ＋ポーション用の 1-4 キー
    def _draw_keys_art(self, surface):
        for x, label in ((-120, "S"), (-70, "R"), (-20, "Q")):
            self._draw_keycap(surface, x, ART_Y + 20, label)
        for i in range(4):
            self._draw_keycap(surface, 60 + i * 40, ART_Y + 20, str(i + 1), size=30)
        theme.draw_text(surface, "start / retry / quit", -70, ART_Y - 20,
                        theme.TEXT_DIM, theme.FONT_SCORE)
        theme.draw_text(surface, "potions", 120, ART_Y - 20,
                        theme.TEXT_DIM, theme.FONT_SCORE)

    # Settings & Shop ページ: 本物と同じ歯車アイコン＋ポーション
    def _draw_settings_art(self, surface):
        gear = Button("", -70, ART_Y, None, width=46, height=46,
                      color=theme.SECONDARY, hover_color=theme.SECONDARY, icon="gear")
        gear.draw(surface)
        cx, cy = theme.to_screen(70, ART_Y)
        draw_item_icon(surface, "duration_boost", int(cx), int(cy), scale=1.4)
        theme.draw_text(surface, "settings", -70, ART_Y - 40, theme.TEXT_DIM, theme.FONT_SCORE)
        theme.draw_text(surface, "shop", 70, ART_Y - 40, theme.TEXT_DIM, theme.FONT_SCORE)


# 初回起動の登録直後に1度だけ見せるチュートリアル（スライドショー形式）。
# ポーションの細かい使い方は載せない（ショップの初回開放演出に委ねる）。SKIP は左上。
class TutorialScreen:
    def __init__(self, on_done):
        self.on_done = on_done
        self.visible = False
        self.page = 0
        self.deck = SlideDeck()
        self.pages = self.deck.pages()  # チュートリアルはポーションページなし
        self.buttons = []

    def show(self):
        self.visible = True
        self.page = 0
        self._build()

    def hide(self):
        self.visible = False
        self.buttons = []

    def _build(self):
        last = self.page == len(self.pages) - 1
        self.buttons = []
        if last:
            self.buttons.append(Button("LET'S GO!", 0, -240, self.on_done,
                                       color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
        else:
            self.buttons.append(Button("NEXT >", 150, -240, self._next, width=140,
                                       color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
            # SKIP は左上に小さく（下部の < ボタンと重ならない位置）
            self.buttons.append(Button("SKIP", -240, 250, self.on_done, width=90, height=34,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER,
                                       font=theme.FONT_SCORE))
        if self.page > 0:
            self.buttons.append(Button("<", -150, -240, self._prev, width=70, height=46,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    def _next(self):
        if self.page < len(self.pages) - 1:
            self.page += 1
            self._build()

    def _prev(self):
        if self.page > 0:
            self.page -= 1
            self._build()

    def draw(self, surface):
        if not self.visible:
            return
        theme.draw_text(surface, "Tutorial", 0, 250, theme.TEXT_DIM, theme.FONT_SCORE)
        theme.draw_text(surface, f"{self.page + 1} / {len(self.pages)}", 0, 152,
                        theme.TEXT_DIM, theme.FONT_SCORE)
        self.deck.draw_page(surface, self.pages[self.page])
        for button in self.buttons:
            button.draw(surface)

    def handle_click(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                button.on_click()
                return

    def handle_motion(self, x, y):
        for button in self.buttons:
            button.set_hover(button.contains(x, y))
