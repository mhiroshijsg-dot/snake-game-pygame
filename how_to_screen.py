from button import Button
from tutorial_screen import SlideDeck
import theme


# 遊び方を説明する画面。スタート画面・設定画面の「How to Play」ボタンから開く。
# 中身はチュートリアル（SlideDeck）と同じスライドで、ショップで開放済み（seen）の
# ポーションの説明ページが後ろに足される。タイトルだけ "How to Play"。
class HowToScreen:
    def __init__(self, on_back, users):
        self.on_back = on_back
        self.users = users
        self.visible = False
        self.page = 0
        self.deck = SlideDeck()
        self.pages = []
        self.buttons = []

    def show(self):
        self.visible = True
        self.page = 0
        # 開くたびに組み直す（直前にポーションを開放していれば、そのページが増える）
        self.pages = self.deck.pages(self.users)
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
        if self.page < len(self.pages) - 1:
            self.buttons.append(Button(">", 150, -240, self._next, width=70, height=46,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    def _prev(self):
        if self.page > 0:
            self.page -= 1
            self._build()

    def _next(self):
        if self.page < len(self.pages) - 1:
            self.page += 1
            self._build()

    def draw(self, surface):
        if not self.visible:
            return
        theme.draw_text(surface, "How to Play", 0, 250, theme.TEXT_DIM, theme.FONT_SCORE)
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
