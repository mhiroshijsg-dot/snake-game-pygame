import pygame
from button import Button
from shop_screen import new_potions
import theme


# ゲームオーバー時の RETRY / BACK ボタン
# ("Game Over" と Score の文字は ScoreCounter が表示する)
class GameOverScreen:
    def __init__(self, on_retry, on_back, on_settings, on_shop, users):
        self.on_retry = on_retry
        self.on_back = on_back
        self.on_settings = on_settings
        self.on_shop = on_shop
        self.users = users
        self.visible = False
        self.buttons = []

    # as_start=True（プレイ後に難易度を変えた等）のときは RETRY ではなく START 表示にする
    def show(self, as_start=False):
        self.visible = True
        # 今回のスコアで新ポーションが開放されていたら SHOP ボタンを金色にして誘導する
        shop_new = bool(new_potions(self.users))
        self.buttons = [
            Button("START" if as_start else "RETRY", 0, -80, self.on_retry,
                   color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER),
            Button("SHOP", 0, -150, self.on_shop,
                   color=theme.GOLD if shop_new else theme.SECONDARY,
                   hover_color=theme.GOLD if shop_new else theme.SECONDARY_HOVER,
                   text_color=theme.TEXT if shop_new else theme.BUTTON_TEXT),
            Button("BACK", 0, -220, self.on_back,
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
        # 未開放の新ポーションがあれば SHOP ボタン横で「NEW POTION!」を点滅させる
        if new_potions(self.users) and (pygame.time.get_ticks() // 400) % 2 == 0:
            theme.draw_text(surface, "NEW POTION!", 195, -150, theme.GOLD, theme.FONT_BUTTON)
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
