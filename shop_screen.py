from functools import partial
from button import Button
from items import draw_item_icon
import theme


# ショップの商品カタログ（拡張可能）。アイテムを増やす時はここに1行足し、
# unlock_score（現在ユーザーの最大ハイスコアがこれ以上で解放）を設定する。
SHOP_ITEMS = [
    {"key": "duration_boost", "name": "Triple Duration Potion", "price": 50, "unlock_score": 50},
    {"key": "double_points", "name": "Double Points Potion", "price": 100, "unlock_score": 100},
]


# ショップ画面。共通I/F（show/hide/draw/handle_click/handle_motion）。
# ハイスコアに応じてアイテムが解放され、ウォレットのポイントで購入する。
class ShopScreen:
    def __init__(self, on_back, users):
        self.on_back = on_back
        self.users = users
        self.visible = False
        self.warning = ""
        self.buttons = []

    def show(self):
        self.visible = True
        self.warning = ""
        self._build()

    def hide(self):
        self.visible = False
        self.buttons = []

    def _unlocked(self, item):
        return self.users.best_high_score() >= item["unlock_score"]

    # 各商品行に BUY ボタン（解放済みのみ）＋ BACK ボタンを並べる
    def _build(self):
        self.buttons = []
        y = 70
        for item in SHOP_ITEMS:
            if self._unlocked(item):
                self.buttons.append(
                    Button("BUY", 150, y, partial(self._buy, item), width=110, height=46,
                           color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
            y -= 90
        self.buttons.append(Button("BACK", 0, -210, self.on_back,
                                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    def _buy(self, item):
        if not self._unlocked(item):
            self.warning = "Locked"
            return
        if self.users.spend(item["price"]):
            self.users.add_item(item["key"], 1)
            self.warning = ""
        else:
            self.warning = "Not enough points"
        self._build()

    def draw(self, surface):
        if not self.visible:
            return
        theme.draw_text(surface, "SHOP", 0, 240, theme.TEXT, theme.FONT_TITLE)
        theme.draw_text(surface, f"Points: {self.users.wallet}", 0, 185,
                        theme.TEXT_DIM, theme.FONT_NAME_SMALL)
        if self.warning:
            theme.draw_text(surface, self.warning, 0, 150, theme.WARNING, theme.FONT_SCORE)

        y = 70
        for item in SHOP_ITEMS:
            owned = self.users.item_count(item["key"])
            unlocked = self._unlocked(item)
            # 左端にアイテムのアイコン（how to play と同様）
            cx, cy = theme.to_screen(-215, y)
            draw_item_icon(surface, item["key"], int(cx), int(cy))
            theme.draw_text(surface, f'{item["name"]}  x{owned}', -45, y + 12,
                            theme.TEXT, theme.FONT_BUTTON)
            if unlocked:
                theme.draw_text(surface, f'{item["price"]} pt', -45, y - 12,
                                theme.TEXT_DIM, theme.FONT_SCORE)
            else:
                theme.draw_text(surface, f'LOCKED — reach {item["unlock_score"]}', -45, y - 12,
                                theme.WARNING, theme.FONT_SCORE)
            y -= 90

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
