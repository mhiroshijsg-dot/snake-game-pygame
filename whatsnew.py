from button import Button
from tutorial_screen import SlideDeck
import theme

# バージョンごとの新機能スライド（古い順）。ページ形式は SlideDeck と同じ
# (タイトル, 本文の行リスト, イラストキー or None)。
# 【リリース手順】新バージョンを出すたびに、ここへ ("X.Y", [ページ...]) を1エントリ足す。
# 起動時に「最後に見たバージョン < 現在」なら、その間の全エントリがまとめて表示される。
CHANGELOG = [
    ("1.2", [
        ("Golden Bonus Orb",
         ["A golden orb now appears once in a while.",
          "Grab it before it fades for 5x points!"],
         "orbs"),
        ("Shop Unlocks",
         ["New potions unlock as your best score grows.",
          "Watch for the golden SHOP button!"],
         "shop"),
    ]),
    ("1.3", [
        ("Resize & Fullscreen",
         ["Drag the window to any size you like,",
          "or press F to toggle fullscreen.",
          "Small displays are supported too."],
         None),
        ("Clearer Effects",
         ["The magnet aura is calmer, and the",
          "shield barrier shines brighter — easier",
          "to tell apart when both are active."],
         "items"),
    ]),
    # 現在バージョンより新しいエントリは表示されない（次のリリースで自動的に有効になる）
    ("1.4", [
        ("New Shop Items!",
         ["Super Magnet: sucks in every orb on the board.",
          "Bomb: blasts every brick into score!",
          "Both unlock at best score 150 —",
          "and come in packs of 3."],
         "shop"),
    ]),
]


# "1.2" → (1, 2) のように比較可能なタプルへ。壊れた値は (0,)（=最古扱い）に落とす
def parse_version(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except (TypeError, ValueError):
        return (0,)


# last_seen より後のバージョンの新機能ページをまとめて返す（古い順）。
# 各バージョンの先頭にはバージョン見出しを付ける
def pages_since(last_seen):
    seen = parse_version(last_seen)
    current = parse_version(theme.APP_VERSION)
    pages = []
    for version, version_pages in CHANGELOG:
        v = parse_version(version)
        if seen < v <= current:
            pages.extend(version_pages)
    return pages


# アップデート後の初回起動で新機能を紹介する画面（チュートリアルと同じスライド形式）。
# 表示するページは show() 時に pages_since() で決まる。閉じると on_done() が呼ばれ、
# GameState 側が last_seen_version を現在バージョンへ更新する。
class WhatsNewScreen:
    def __init__(self, on_done):
        self.on_done = on_done
        self.visible = False
        self.page = 0
        self.deck = SlideDeck()
        self.pages = []
        self.buttons = []

    def show(self, last_seen):
        self.pages = pages_since(last_seen)
        if not self.pages:  # 表示するものが無ければ即終了（呼び出し側の保険）
            self.on_done()
            return
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
            self.buttons.append(Button("GOT IT!", 0, -240, self.on_done,
                                       color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
        else:
            self.buttons.append(Button("NEXT >", 150, -240, self._next, width=140,
                                       color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
            # SKIP は左上に小さく（チュートリアルと同じ配置）
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
        theme.draw_text(surface, f"What's New in v{theme.APP_VERSION}!",
                        0, 250, theme.GOLD, theme.FONT_BUTTON)
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
