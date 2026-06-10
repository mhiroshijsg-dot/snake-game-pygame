from button import Button
from food import Food
from obstacle import Block
from magnet import Magnet
from shield import ShieldItem
from items import draw_item_icon, ITEM_COLORS
import theme

ICON_X = -185  # アイコンを置く左側の世界座標X


# 遊び方を説明する画面。スタート画面・設定画面の「How to Play」ボタンから開く。
# 説明が多いのでページ制にし、< > で切り替える。各行の左に実物アイコンを描く。
class HowToScreen:
    # 各ページ = (説明文, 補足, アイコンキー or None) の行。1ページ4行までを目安にする。
    PAGES = [
        [
            ("Arrow keys", "move the snake", None),
            ("Eat the orbs", "to grow longer", "orb"),
            ("Avoid", "walls, your tail, and brick blocks", "brick"),
            ("S / R / Q", "start / restart / quit", None),
        ],
        [
            ("Grab the magnet", "to widen your reach for a while", "magnet"),
            ("Grab the shield", "to smash through bricks for a while", "shield"),
            ("Points", "orbs & bricks score — more on harder modes", None),
            ("Settings", "change difficulty & players", None),
        ],
        [
            ("Shop", "spend points; items unlock by best score", None),
            ("Item slots", "press 1-4 to use items in the bottom bar", None),
            ("Double Potion", "doubles points earned for a short time", "double_points"),
            ("Triple Potion", "x3 magnet/shield duration while active", "duration_boost"),
        ],
    ]

    def __init__(self, on_back):
        self.on_back = on_back
        self.visible = False
        self.page = 0
        self.buttons = []
        # 実際のゲーム素材をアイコンとして描くためのインスタンス（位置は draw でセット）
        self._icons = {"orb": Food(), "brick": Block(0, 0, 1),
                       "magnet": Magnet(0, 0, 1), "shield": ShieldItem(0, 0, 1)}

    def show(self):
        self.visible = True
        self.page = 0
        self._build()

    def hide(self):
        self.visible = False
        self.buttons = []

    # 現在ページに応じてナビゲーション（< BACK >）を組み立てる
    def _build(self):
        self.buttons = [
            Button("BACK", 0, -240, self.on_back,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
        ]
        if self.page > 0:
            self.buttons.append(Button("<", -150, -240, self._prev, width=70, height=46,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))
        if self.page < len(self.PAGES) - 1:
            self.buttons.append(Button(">", 150, -240, self._next, width=70, height=46,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    def _prev(self):
        if self.page > 0:
            self.page -= 1
            self._build()

    def _next(self):
        if self.page < len(self.PAGES) - 1:
            self.page += 1
            self._build()

    def draw(self, surface):
        if not self.visible:
            return
        theme.draw_text(surface, "How to Play", 0, 230, theme.TEXT, theme.FONT_BIG)
        theme.draw_text(surface, f"{self.page + 1} / {len(self.PAGES)}", 0, 186,
                        theme.TEXT_DIM, theme.FONT_SCORE)
        y = 130
        for head, desc, icon in self.PAGES[self.page]:
            theme.draw_text(surface, head, 0, y, theme.TEXT, theme.FONT_BUTTON)
            theme.draw_text(surface, desc, 0, y - 22, theme.TEXT_DIM, theme.FONT_SCORE)
            if icon in ITEM_COLORS:
                cx, cy = theme.to_screen(ICON_X, y - 8)
                draw_item_icon(surface, icon, int(cx), int(cy), scale=0.9)
            elif icon:
                item = self._icons[icon]
                item.x, item.y = ICON_X, y - 8  # テキスト行の左に実物アイコンを描く
                item.draw(surface)
            y -= 70
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
