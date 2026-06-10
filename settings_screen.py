from functools import partial
import pygame
from button import Button
from settings import DIFFICULTY_ORDER
import theme

PLAYERS_PER_PAGE = 4  # プレイヤー選択ページに一度に表示する人数
MAX_NAME_LEN = 12     # 名前の長さ上限（ボタン・入力欄の幅に収まり、描画も安全な範囲）


# 設定画面。ページ(モード)を切り替えて表示する:
#  "menu"       … プレイヤー選択ページ／難易度選択ページへの入口 + 戻る
#  "players"    … プレイヤーの選択・削除・新規登録の入口
#  "difficulty" … 難易度の選択
#  "input"      … 新規ユーザー名のテキスト入力
class SettingsScreen:
    def __init__(self, settings, on_back, on_howto, users):
        self.settings = settings
        self.on_back = on_back  # メニューの BACK（タイトル等へ戻る）
        self.on_howto = on_howto
        self.users = users
        self.visible = False
        self.mode = "menu"
        self.input_text = ""
        self.composing_text = ""    # IMEの未確定文字（日本語入力中の下線部分）
        self.warning = ""
        self.pending_delete = None  # 削除確認中のユーザー名
        self.players_page = 0       # プレイヤー選択ページの現在ページ
        self._player_pages = 1      # 総ページ数（draw のインジケータ用）
        self.buttons = []

    def show(self):
        self.visible = True
        self.mode = "menu"
        self.input_text = ""
        self.warning = ""
        self._build()

    def hide(self):
        self.visible = False
        self.buttons = []

    # 現在のモードに応じてボタン一式を組み立てる
    def _build(self):
        if self.mode == "players":
            self._build_players()
        elif self.mode == "difficulty":
            self._build_difficulty()
        elif self.mode == "input":
            self.buttons = [Button("CANCEL", 0, -190, self._cancel_input,
                                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER)]
        elif self.mode == "confirm":
            self.buttons = [
                Button("DELETE", 0, -20, self._confirm_delete,
                       color=theme.WARNING, hover_color=theme.WARNING),
                Button("CANCEL", 0, -100, self._cancel_delete,
                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
            ]
        else:
            self._build_menu()

    def _build_menu(self):
        self.buttons = [
            Button(f"PLAYER: {self.users.current}", 0, 110, self._open_players, width=320,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER, font=theme.FONT_NAME),
            Button(f"DIFFICULTY: {self.settings.difficulty_key}", 0, 30, self._open_difficulty, width=320,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
            Button("BACK", 0, -120, self.on_back,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER),
            # 左下の小さな「遊び方」ボタン
            Button("? How to Play", -205, -255, self.on_howto, width=150, height=34,
                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER,
                   font=theme.FONT_SCORE),
        ]

    def _build_players(self):
        self.buttons = []
        names = self.users.names()
        # ページ数を出してページ番号をクランプ（削除でページが減っても安全）
        self._player_pages = max(1, (len(names) + PLAYERS_PER_PAGE - 1) // PLAYERS_PER_PAGE)
        self.players_page = max(0, min(self.players_page, self._player_pages - 1))
        start = self.players_page * PLAYERS_PER_PAGE
        # このページに表示する名前を固定位置に並べる（人数が増えても見切れない）
        y = 150
        for name in names[start:start + PLAYERS_PER_PAGE]:
            selected = (name == self.users.current)
            self.buttons.append(Button(name, -25, y, partial(self._choose_user, name), width=230,
                                       color=theme.PRIMARY if selected else theme.SECONDARY,
                                       hover_color=theme.PRIMARY_HOVER if selected else theme.SECONDARY_HOVER,
                                       font=theme.FONT_NAME))
            self.buttons.append(Button("X", 125, y, partial(self._delete_user, name),
                                       width=46, height=46,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER,
                                       text_color=theme.WARNING))
            y -= 58
        # ページ切替（複数ページある時だけ）
        if self._player_pages > 1:
            self.buttons.append(Button("<", -110, -78, self._prev_page, width=56, height=44,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))
            self.buttons.append(Button(">", 110, -78, self._next_page, width=56, height=44,
                                       color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))
        # NEW USER と BACK は常に同じ位置（見切れない）
        self.buttons.append(Button("NEW USER", 0, -140, self._start_input,
                                   color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
        self.buttons.append(Button("BACK", 0, -205, self._back_to_menu,
                                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    def _prev_page(self):
        self.players_page = max(0, self.players_page - 1)
        self._build()

    def _next_page(self):
        self.players_page += 1  # 上限は _build_players でクランプされる
        self._build()

    def _build_difficulty(self):
        self.buttons = []
        y = 120
        for key in DIFFICULTY_ORDER:
            selected = (key == self.settings.difficulty_key)
            self.buttons.append(Button(key, 0, y, partial(self.select, key),
                                       color=theme.PRIMARY if selected else theme.SECONDARY,
                                       hover_color=theme.PRIMARY_HOVER if selected else theme.SECONDARY_HOVER))
            y -= 62
        self.buttons.append(Button("BACK", 0, y - 6, self._back_to_menu,
                                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    # --- ページ遷移・操作 ---
    def _open_players(self):
        self.mode = "players"
        self.warning = ""
        self.players_page = 0
        self._build()

    def _open_difficulty(self):
        self.mode = "difficulty"
        self._build()

    def _back_to_menu(self):
        self.mode = "menu"
        self.warning = ""
        self._build()

    def _choose_user(self, name):
        # 選んでもページに留まる（選択の強調表示だけ更新）
        self.users.set_current(name)
        self._build()

    # 削除ボタン: 最後の1人なら警告、そうでなければ確認画面へ
    def _delete_user(self, name):
        if len(self.users.names()) <= 1:
            self.warning = "Cannot delete the only user"
            self._build()
            return
        self.pending_delete = name
        self.mode = "confirm"
        self._build()

    def _confirm_delete(self):
        self.users.delete_user(self.pending_delete)
        self.pending_delete = None
        self._open_players()

    def _cancel_delete(self):
        self.pending_delete = None
        self._open_players()

    def _start_input(self):
        self.mode = "input"
        self.input_text = ""
        self.composing_text = ""
        self.warning = ""
        self._build()

    # 入力を抜けてプレイヤー選択ページに戻る
    def _cancel_input(self):
        self.mode = "players"
        self.input_text = ""
        self.composing_text = ""
        self.warning = ""
        self._build()

    # 名前を確定。空・重複なら警告を出して入力継続
    def _confirm_new_user(self):
        name = self.input_text.strip()
        if not name:
            self.warning = "Please enter a name"
            return
        if self.users.exists(name):
            self.warning = "That name is taken. Try another."
            return
        self.users.add_user(name)
        self._cancel_input()

    # 難易度を選んでもページに留まる（選択の強調表示だけ更新）
    def select(self, key):
        self.settings.set_difficulty(key)
        self._build()

    # --- 入力イベント（snakegame のループから input モード時だけ渡される）---
    # 日本語入力(IME): 変換中は TEXTEDITING で未確定文字、確定で TEXTINPUT が来る。
    def handle_text_event(self, event):
        if event.type == pygame.TEXTINPUT:
            # 上限を超えるぶんは捨てる（無制限だと描画サーフェスが巨大化しうる）
            self.input_text = (self.input_text + event.text)[:MAX_NAME_LEN]
            self.composing_text = ""  # 確定したので未確定をクリア
        elif event.type == pygame.TEXTEDITING:
            self.composing_text = event.text  # 変換中の下線部分
        elif event.type == pygame.KEYDOWN:
            # IMEで変換中(composing)はキーをIMEに任せ、こちらでは処理しない
            if self.composing_text:
                return
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_new_user()
            elif event.key == pygame.K_ESCAPE:
                self._cancel_input()

    # --- 描画 ---
    def draw(self, surface):
        if not self.visible:
            return
        if self.mode == "input":
            theme.draw_text(surface, "New User", 0, 130, theme.TEXT, theme.FONT_BIG)
            self._draw_input_box(surface)
            if self.warning:
                theme.draw_text(surface, self.warning, 0, -40, theme.WARNING, theme.FONT_SCORE)
            theme.draw_text(surface, "Enter: OK     Esc: Cancel", 0, -95,
                            theme.TEXT_DIM, theme.FONT_SCORE)
        elif self.mode == "players":
            theme.draw_text(surface, "Select Player", 0, 210, theme.TEXT, theme.FONT_BIG)
            if self.warning:
                theme.draw_text(surface, self.warning, 0, 180, theme.WARNING, theme.FONT_SCORE)
            if self._player_pages > 1:  # ページ番号（< 1/3 >）
                theme.draw_text(surface, f"{self.players_page + 1} / {self._player_pages}",
                                0, -78, theme.TEXT_DIM, theme.FONT_SCORE)
        elif self.mode == "difficulty":
            theme.draw_text(surface, "Difficulty", 0, 200, theme.TEXT, theme.FONT_BIG)
        elif self.mode == "confirm":
            theme.draw_text(surface, "Delete this player?", 0, 130, theme.TEXT, theme.FONT_BIG)
            theme.draw_text(surface, f'"{self.pending_delete}"', 0, 80, theme.WARNING, theme.FONT_NAME)
            theme.draw_text(surface, "This cannot be undone.", 0, 45,
                            theme.TEXT_DIM, theme.FONT_SCORE)
        else:
            theme.draw_text(surface, "Settings", 0, 200, theme.TEXT, theme.FONT_TITLE)

        for button in self.buttons:
            button.draw(surface)

    def _draw_input_box(self, surface):
        cx, cy = theme.to_screen(0, 50)
        rect = pygame.Rect(0, 0, 300, 56)
        rect.center = (cx, cy)
        pygame.draw.rect(surface, theme.BG, rect, border_radius=12)
        pygame.draw.rect(surface, theme.PRIMARY, rect, width=2, border_radius=12)
        # 確定済み + IME未確定 + カーソル。日本語が出るので JP フォントで描く
        text = self.input_text + self.composing_text + "|"
        theme.draw_text(surface, text, 0, 50, theme.TEXT, theme.FONT_NAME)

    # --- 入力 ---
    def handle_click(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                button.on_click()
                return

    def handle_motion(self, x, y):
        for button in self.buttons:
            button.set_hover(button.contains(x, y))
