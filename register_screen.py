import pygame
from button import Button
import theme
from settings_screen import MAX_NAME_LEN


# 初回起動（ユーザーが1人もいない）時に最初に表示する登録画面。
# 名前を確定すると on_done() が呼ばれる。キャンセルは無し＝必ず登録してから進む。
# テキスト入力のIME対応は settings_screen の input モードと同じ方式。
class RegisterScreen:
    def __init__(self, users, on_done):
        self.users = users
        self.on_done = on_done
        self.visible = False
        self.input_text = ""
        self.composing_text = ""   # IMEの未確定文字（日本語入力中の下線部分）
        self.warning = ""
        self.buttons = []

    def show(self):
        self.visible = True
        self.input_text = ""
        self.composing_text = ""
        self.warning = ""
        self.buttons = [Button("OK", 0, -150, self._confirm,
                               color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER)]

    def hide(self):
        self.visible = False
        self.buttons = []

    def _confirm(self):
        name = self.input_text.strip()
        if not name:
            self.warning = "Please enter a name"
            return
        if self.users.exists(name):
            # TEST_FIRST_RUN で既存データのまま表示した時など。そのまま選択して進む
            self.users.set_current(name)
        else:
            self.users.add_user(name)
        self.on_done()

    def handle_text_event(self, event):
        if event.type == pygame.TEXTINPUT:
            # 上限を超えるぶんは捨てる（無制限だと描画サーフェスが巨大化しうる）
            self.input_text = (self.input_text + event.text)[:MAX_NAME_LEN]
            self.composing_text = ""
        elif event.type == pygame.TEXTEDITING:
            self.composing_text = event.text
        elif event.type == pygame.KEYDOWN:
            # IMEで変換中はキーをIMEに任せる
            if self.composing_text:
                return
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm()

    def draw(self, surface):
        if not self.visible:
            return
        theme.draw_text(surface, "Welcome!", 0, 180, theme.TEXT, theme.FONT_TITLE)
        theme.draw_text(surface, "Enter your player name to get started",
                        0, 120, theme.TEXT_DIM, theme.FONT_NAME_SMALL)
        # 入力欄（settings の input と同じ見た目）
        cx, cy = theme.to_screen(0, 50)
        rect = pygame.Rect(0, 0, 300, 56)
        rect.center = (cx, cy)
        pygame.draw.rect(surface, theme.BG, rect, border_radius=12)
        pygame.draw.rect(surface, theme.PRIMARY, rect, width=2, border_radius=12)
        text = self.input_text + self.composing_text + "|"
        theme.draw_text(surface, text, 0, 50, theme.TEXT, theme.FONT_NAME)
        if self.warning:
            theme.draw_text(surface, self.warning, 0, -30, theme.WARNING, theme.FONT_SCORE)
        theme.draw_text(surface, "Press Enter or click OK", 0, -80,
                        theme.TEXT_DIM, theme.FONT_SCORE)
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
