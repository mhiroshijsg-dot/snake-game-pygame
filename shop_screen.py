from functools import partial
from button import Button
from items import draw_item_icon
import theme


# ショップの商品カタログ（拡張可能）。アイテムを増やす時はここに1行足し、
# unlock_score（現在ユーザーの最大ハイスコアがこれ以上で解放）と
# desc（初回開放時に表示する説明文の行リスト）を設定する。
SHOP_ITEMS = [
    {"key": "duration_boost", "name": "Triple Duration Potion", "price": 50, "unlock_score": 50,
     "desc": ["Makes magnets and shields last 3x longer —",
              "both the one already active when you drink it",
              "and any you pick up while the potion lasts.",
              "Use it from the bottom item bar (keys 1-4)."]},
    {"key": "double_points", "name": "Double Points Potion", "price": 100, "unlock_score": 100,
     "desc": ["Doubles every point you earn for a while.",
              "Your snake turns gold while it's active.",
              "Use it from the bottom item bar (keys 1-4)."]},
]


# 解放済みなのにまだ「開放」演出を見ていないポーション一覧。
# タイトル・ゲームオーバー画面が SHOP ボタンのハイライト判定に使う。
def new_potions(users):
    best = users.best_high_score()
    return [item for item in SHOP_ITEMS
            if best >= item["unlock_score"] and not users.has_seen_item(item["key"])]


# ショップ画面。共通I/F（show/hide/draw/handle_click/handle_motion）。
# ハイスコアに応じてアイテムが解放され、ウォレットのポイントで購入する。
class ShopScreen:
    def __init__(self, on_back, users, test_reveal=False):
        self.on_back = on_back
        self.users = users
        # True なら開放演出を何度でも確認できる（seen を無視し、記録もしない）
        self.test_reveal = test_reveal
        self.visible = False
        self.warning = ""
        self.reveal = None   # 「開放」演出で説明を表示中のアイテム（Noneなら通常表示）
        self.buttons = []

    def show(self):
        self.visible = True
        self.warning = ""
        self.reveal = None
        self._build()

    def hide(self):
        self.visible = False
        self.buttons = []

    def _unlocked(self, item):
        return self.users.best_high_score() >= item["unlock_score"]

    # 開放演出を見た扱いにするか（テストモード中は常に「未見」として UNLOCK を出す）
    def _seen(self, item):
        return not self.test_reveal and self.users.has_seen_item(item["key"])

    # 各商品行にボタンを並べる。解放済みでも初回は UNLOCK（押すと説明表示→以後 BUY）
    def _build(self):
        if self.reveal:
            # 説明表示中は OK だけ
            self.buttons = [Button("OK", 0, -210, self._close_reveal,
                                   color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER)]
            return
        self.buttons = []
        y = 70
        for item in SHOP_ITEMS:
            if self._unlocked(item):
                if self._seen(item):
                    self.buttons.append(
                        Button("BUY", 150, y, partial(self._buy, item), width=110, height=46,
                               color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
                else:
                    self.buttons.append(
                        Button("UNLOCK", 150, y, partial(self._unlock, item), width=110, height=46,
                               color=theme.GOLD, hover_color=theme.GOLD,
                               text_color=theme.TEXT))
            y -= 90
        self.buttons.append(Button("BACK", 0, -210, self.on_back,
                                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    # 初回開放: 見た記録を保存し、説明表示モードへ。OK の後は通常の BUY に変わる
    # （テストモード中は記録しないので、何度でも UNLOCK を試せる）
    def _unlock(self, item):
        if not self.test_reveal:
            self.users.mark_item_seen(item["key"])
        self.reveal = item
        self.warning = ""
        self._build()

    def _close_reveal(self):
        self.reveal = None
        self._build()

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
        if self.reveal:
            self._draw_reveal(surface)
            for button in self.buttons:
                button.draw(surface)
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
            if not unlocked:
                theme.draw_text(surface, f'LOCKED — reach {item["unlock_score"]}', -45, y - 12,
                                theme.WARNING, theme.FONT_SCORE)
            elif not self._seen(item):
                theme.draw_text(surface, "NEW POTION!", -45, y - 12,
                                theme.GOLD, theme.FONT_BUTTON)
            else:
                theme.draw_text(surface, f'{item["price"]} pt', -45, y - 12,
                                theme.TEXT_DIM, theme.FONT_SCORE)
            y -= 90

        for button in self.buttons:
            button.draw(surface)

    # 初回開放の説明ページ（大きいアイコン＋名前＋効果の説明）。
    # 将来カタログに desc/price を書き忘れても落とさない（.get で既定値に落とす）
    def _draw_reveal(self, surface):
        item = self.reveal
        theme.draw_text(surface, "NEW POTION UNLOCKED!", 0, 220, theme.GOLD, theme.FONT_BIG)
        cx, cy = theme.to_screen(0, 120)
        draw_item_icon(surface, item["key"], int(cx), int(cy), scale=2.2)
        theme.draw_text(surface, item.get("name", item["key"]), 0, 40, theme.TEXT, theme.FONT_BUTTON)
        y = -10
        for line in item.get("desc", []):
            theme.draw_text(surface, line, 0, y, theme.TEXT_DIM, theme.FONT_SCORE)
            y -= 28
        theme.draw_text(surface, f'Price: {item.get("price", 0)} pt', 0, y - 12,
                        theme.TEXT, theme.FONT_SCORE)

    def handle_click(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                button.on_click()
                return

    def handle_motion(self, x, y):
        for button in self.buttons:
            button.set_hover(button.contains(x, y))
