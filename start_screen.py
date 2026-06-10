from button import Button
import theme


class StartScreen:
    def __init__(self, on_start, on_quit, on_settings, on_howto, on_shop, users):
        self.on_start = on_start
        self.on_quit = on_quit
        self.on_settings = on_settings
        self.on_howto = on_howto
        self.on_shop = on_shop
        self.users = users  # 現在のプレイヤー名・ウォレットを表示するため
        self.visible = False
        self.buttons = []

    def show(self):
        self.visible = True
        self.buttons = [
            Button("START", 0, 20, self.on_start,
                   color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER),
            Button("SHOP", 0, -56, self.on_shop,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
            Button("QUIT", 0, -132, self.on_quit,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
            # 右上の設定アイコン（歯車を図形で描く小さな丸ボタン）
            Button("", 250, 250, self.on_settings, width=46, height=46,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER,
                   icon="gear"),
            # 左下の小さな「遊び方」ボタン
            Button("? How to Play", -205, -255, self.on_howto, width=150, height=34,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER,
                   font=theme.FONT_SCORE),
        ]

    def hide(self):
        self.visible = False
        self.buttons = []

    def draw(self, surface):
        if not self.visible:
            return
        theme.draw_text(surface, "Snake", 0, 130, theme.TEXT, theme.FONT_TITLE)
        # 今誰がプレイ中か＋所持ポイントを表示（STARTボタンと重ならない高さに）
        theme.draw_text(surface, f"Player: {self.users.current}", 0, 92,
                        theme.TEXT_DIM, theme.FONT_NAME_SMALL)
        theme.draw_text(surface, f"Points: {self.users.wallet}", 0, 70,
                        theme.TEXT_DIM, theme.FONT_SCORE)
        # 右下にバージョン表示（配布物の識別用）
        theme.draw_text(surface, f"v{theme.APP_VERSION}", 255, -260,
                        theme.TEXT_DIM, theme.FONT_SCORE)
        for button in self.buttons:
            button.draw(surface)

    # クリック座標を受け取り、当たったボタンのコールバックを呼ぶ
    def handle_click(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                button.on_click()
                return

    # マウス座標を受け取り、各ボタンのホバー状態を更新する
    def handle_motion(self, x, y):
        for button in self.buttons:
            button.set_hover(button.contains(x, y))
