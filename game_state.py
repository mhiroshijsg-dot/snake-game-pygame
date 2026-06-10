from start_screen import StartScreen
from settings_screen import SettingsScreen
from game_over_screen import GameOverScreen
from how_to_screen import HowToScreen
from shop_screen import ShopScreen
from snake import MAX_SCORE


class GameState:
    def __init__(self, snake, food, obstacles, magnets, shields, items,
                 score_counter, settings, users, test_mode=False):
        self.snake = snake
        self.food = food
        self.obstacles = obstacles
        self.magnets = magnets
        self.shields = shields
        self.items = items        # 下部アイテムスロットHUD（効果の更新・リセットも担う）
        self.score_counter = score_counter
        self.settings = settings
        self.users = users
        self.test_mode = test_mode  # Trueなら最大-1の長さで開始（クリア演出の確認用）
        self.is_on = True
        self.is_over = False
        self.is_started = False
        self.is_settings = False
        self.is_howto = False
        self.is_shop = False
        self.is_cleared = False     # 盤面クリア（理論上の最大に到達）
        self._run_difficulty = None  # 今プレイ中の回で使っている難易度
        self._howto_from_settings = False  # 遊び方を閉じた時の戻り先
        self._shop_from_over = False        # ショップを閉じた時の戻り先（True=ゲームオーバー）

        # スタート画面の間はスネーク・food・障害物・アイテムを隠しておく
        self.snake.hide()
        self.food.hide()
        self.obstacles.hide()
        self.magnets.hide()
        self.shields.hide()

        self.start_screen = StartScreen(self.start, self.quit, self.open_settings,
                                        self.open_howto, self.open_shop, users)
        self.settings_screen = SettingsScreen(self.settings, self.close_settings,
                                              self.open_howto, users)
        self.game_over_screen = GameOverScreen(self.retry, self.quit, self.open_settings,
                                               self.open_shop, users)
        self.how_to_screen = HowToScreen(self.close_howto)
        self.shop_screen = ShopScreen(self.close_shop, users)
        self.start_screen.show()

    def start(self):
        # スタート画面にいる時だけ開始（プレイ中・設定中・ゲームオーバー中は無視）
        if self.is_started or self.is_settings:
            return
        self.start_screen.hide()
        self.is_cleared = False
        self._run_difficulty = self.settings.difficulty_key  # この回の難易度を記録
        self.snake.reset()
        self.obstacles.reset()   # food より先（foodがレンガを避けて配置されるため）
        self.food.reset()
        self.magnets.reset()
        self.shields.reset()
        self.items.reset()
        self._apply_test_length()
        self.is_started = True

    # プレイ後に難易度が切り替えられたか（=リトライではなく新規スタート扱いにする）
    def _difficulty_changed(self):
        return self.settings.difficulty_key != self._run_difficulty

    # 's'キー: スタート画面ならSTART。ゲームオーバーでボタンがSTART表示(難易度変更後)なら再開。
    def press_start_key(self):
        if self.is_settings or self.is_howto:
            return
        if self.is_over:
            if self._difficulty_changed():
                self.retry()
        else:
            self.start()

    # 'r'キー: ゲームオーバーでボタンがRETRY表示(難易度そのまま)のときだけ再開。
    def press_retry_key(self):
        if self.is_settings or self.is_howto:
            return
        if self.is_over and not self._difficulty_changed():
            self.retry()

    # テスト用: スネークを「最大-1」の長さにし、スコアも合わせる。
    # 開始直後にオーブを1つ食べればクリア演出に入れる。
    def _apply_test_length(self):
        if not self.test_mode:
            return
        self.snake.increase_segments(MAX_SCORE - 1)
        self.snake.prefill_history()
        self.score_counter.score = MAX_SCORE - 3

    # 設定画面の開閉（スタート画面・ゲームオーバー画面のどちらからでも開ける）
    def open_settings(self):
        if self.is_over:
            # ゲームオーバーの表示を一旦隠す
            self.game_over_screen.hide()
            self.score_counter.clear()
            self.snake.hide()
            self.food.hide()
            self.obstacles.hide()
            self.magnets.hide()
            self.shields.hide()
        else:
            self.start_screen.hide()
        self.settings_screen.show()
        self.is_settings = True

    def close_settings(self):
        self.settings_screen.hide()
        self.is_settings = False
        if self.is_over:
            if self.is_cleared:
                # クリア演出に戻す（盤面はクリア画面側で塗るのでsnake/foodは隠したまま）
                self.score_counter.show_clear()
                self.game_over_screen.show(self._difficulty_changed())
            else:
                # ゲームオーバーの表示を元に戻す
                self.snake.show()
                self.food.show()
                self.obstacles.show()
                self.magnets.show()
                self.shields.show()
                self.score_counter.show_game_over()
                self.game_over_screen.show(self._difficulty_changed())
        else:
            self.start_screen.show()

    # 遊び方ページの開閉（スタート画面・設定画面のどちらからでも開ける）
    def open_howto(self):
        self._howto_from_settings = self.is_settings
        if self.is_settings:
            self.settings_screen.hide()
        else:
            self.start_screen.hide()
        self.how_to_screen.show()
        self.is_howto = True

    def close_howto(self):
        self.how_to_screen.hide()
        self.is_howto = False
        if self._howto_from_settings:
            self.settings_screen.show()
        else:
            self.start_screen.show()

    # ショップの開閉（スタート画面・ゲームオーバー画面のどちらからでも開ける）
    def open_shop(self):
        self._shop_from_over = self.is_over
        if self.is_over:
            # ゲームオーバーの表示を一旦隠す（設定画面と同じ退避）
            self.game_over_screen.hide()
            self.score_counter.clear()
            self.snake.hide()
            self.food.hide()
            self.obstacles.hide()
            self.magnets.hide()
            self.shields.hide()
        else:
            self.start_screen.hide()
        self.shop_screen.show()
        self.is_shop = True

    def close_shop(self):
        self.shop_screen.hide()
        self.is_shop = False
        if self._shop_from_over:
            if self.is_cleared:
                self.score_counter.show_clear()
                self.game_over_screen.show(self._difficulty_changed())
            else:
                self.snake.show()
                self.food.show()
                self.obstacles.show()
                self.magnets.show()
                self.shields.show()
                self.score_counter.show_game_over()
                self.game_over_screen.show(self._difficulty_changed())
        else:
            self.start_screen.show()

    # 数字キーでプレイ中にアイテムスロットを使う（プレイ中のみ反応）
    def use_item(self, index):
        if self.is_started and not self.is_over and not self.is_settings \
                and not self.is_shop and not self.is_howto:
            self.items.use_slot(index)

    def handle_game_over(self):
        self.is_over = True
        self.snake.crashed = True  # 目を驚き顔にする（reset時にFalseへ戻る）
        self.score_counter.finalize_score()  # ベスト更新判定＆保存
        self.score_counter.show_game_over()
        self.game_over_screen.show()

    # 理論上の最大に到達＝盤面クリア（衝突ではなく勝ち）
    def handle_clear(self):
        self.is_over = True
        self.is_cleared = True
        # 盤面はクリア画面側で塗るので、巨大なスネーク・food・障害物は隠す
        self.snake.hide()
        self.food.hide()
        self.obstacles.hide()
        self.magnets.hide()
        self.shields.hide()
        self.score_counter.finalize_score()
        self.score_counter.show_clear()
        self.game_over_screen.show()

    def retry(self):
        if not self.is_over or self.is_settings:
            return
        self.game_over_screen.hide()
        self.is_cleared = False
        self._run_difficulty = self.settings.difficulty_key  # 新しい回の難易度を記録
        self.score_counter.reset()
        self.snake.reset()
        self.obstacles.reset()
        self.food.reset()
        self.magnets.reset()
        self.shields.reset()
        self.items.reset()
        self._apply_test_length()
        self.is_over = False

    def quit(self):
        self.score_counter.save_high_score()
        self.is_on = False

    # 今アクティブな画面を返す（ゲーム中はNone）
    def _active_screen(self):
        if self.is_howto:
            return self.how_to_screen
        if self.is_shop:
            return self.shop_screen
        if self.is_settings:
            return self.settings_screen
        if not self.is_started:
            return self.start_screen
        if self.is_over:
            return self.game_over_screen
        return None

    # 設定画面でユーザー名を入力中か（この間はキー入力をテキストへ回す）
    def wants_text_input(self):
        return self.is_settings and self.settings_screen.mode == "input"

    def handle_text_event(self, event):
        self.settings_screen.handle_text_event(event)

    # 状態に応じてクリックを振り分ける
    def handle_click(self, x, y):
        screen = self._active_screen()
        if screen:
            screen.handle_click(x, y)

    # マウス移動(世界座標)を現在の画面へ振り分け、ボタンのホバーを更新する
    def handle_motion(self, x, y):
        screen = self._active_screen()
        if screen:
            screen.handle_motion(x, y)

    # 現在アクティブな画面(タイトル・ボタン)を描く
    def draw(self, surface):
        screen = self._active_screen()
        if screen:
            screen.draw(surface)
