from button import Button
import theme


# ゲームオーバー時の RETRY / QUIT ボタン
# ("Game Over" と Score の文字は ScoreCounter が表示する)
class GameOverScreen:
    def __init__(self, on_retry, on_quit, on_settings, on_shop, users):
        self.on_retry = on_retry
        self.on_quit = on_quit
        self.on_settings = on_settings
        self.on_shop = on_shop
        self.users = users
        self.visible = False
        self.buttons = []

    # as_start=True（プレイ後に難易度を変えた等）のときは RETRY ではなく START 表示にする
    def show(self, as_start=False):
        self.visible = True
        self.buttons = [
            Button("START" if as_start else "RETRY", 0, -80, self.on_retry,
                   color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER),
            Button("SHOP", 0, -150, self.on_shop,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
            Button("QUIT", 0, -220, self.on_quit,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
            # スタート画面と同じ右上の設定アイコン（歯車を図形で描く）
            Button("", 250, 250, self.on_settings, width=46, height=46,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER,
                   icon="gear"),
        ]

    def hide(self):
        self.visible = False
        self.buttons = []

    def draw(self, surface):
        if not self.visible:
            return
        # スコア表示(ScoreCounter)とRETRYボタンの間に置く（ボタンと重ならない）
        theme.draw_text(surface, f"Points: {self.users.wallet}", 0, -28,
                        theme.TEXT_DIM, theme.FONT_SCORE)
        for button in self.buttons:
            button.draw(surface)

    def handle_click(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                button.on_click()
                return

    # マウス座標を受け取り、各ボタンのホバー状態を更新する
    def handle_motion(self, x, y):
        for button in self.buttons:
            button.set_hover(button.contains(x, y))
