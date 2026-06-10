import pygame
from snake import Snake, STEP, GRID, MAX_FILL_PX
from food import FoodManager, EAT_DISTANCE
from obstacle import ObstacleManager
from magnet import MagnetManager
from shield import ShieldManager
from items import DoublePointsEffect, DurationBoostEffect, ItemBar
from score import ScoreCounter
from game_state import GameState
from settings import Settings
from users import UserManager
import theme
import crashlog

# TODO: 画面のpx数に応じて拡大縮小できるようにしようを変更する？
# TODO: game over 画面ではquitじゃなくてbackボタンにしたほうがいい。title画面に戻す
# TODO: アイテムの効果時間二倍ポーションを獲得した時点で発動中のmagnet, shieldの効果時間をのばす
# TODO: hardではシールドの出現率を上げる
# TODO: magnet, shield同時発動中、片方が効果切れの点滅というのはUIが少しみにくい
# TODO: 初めてゲームを起動時（user.jsonが空の時）にまずユーザー登録するようにする
# TODO: チュートリアルを導入、easy modeで動きと基本のmagnet, shieldの説明
# TODO: 新たなpotionを獲得したら説明用の画面を初回のみ見せる
# TODO: 一定のスコアを超えたらポイントを消費して最初からスコアと長さを持った状態から始められるようにする？
# TODO: アイテム数を増やす（ショップのカタログに unlock_score 付きで1行足す方式）
# TODO: ポイントの違うオーブを導入
# TODO: マリオの赤コインのようなイベント
# TODO: ボーナスイベントとして全面オーブのステージに転移する
# TODO: 時間を測って耐久モード？

# クリア演出の確認用。Trueにすると最大-1の長さで開始し、オーブ1個でクリアできる
TEST_CLEAR = False

crashlog.install()  # 予期しない例外を crash.log に記録してから落ちる（配布版の調査用）

pygame.init()
# ウィンドウ/タスクバー用アイコン（無くても起動は続ける。set_mode の前に設定する）
try:
    pygame.display.set_icon(pygame.image.load(theme.resource_path("assets/icon_64.png")))
except (OSError, pygame.error):
    pass
surface = pygame.display.set_mode((theme.WIDTH, theme.HEIGHT))
pygame.display.set_caption(f"Snake Game v{theme.APP_VERSION}")
clock = pygame.time.Clock()

settings = Settings()
users = UserManager()
snake = Snake()
obstacles = ObstacleManager(snake, settings)
food = FoodManager(snake, obstacles)
double_effect = DoublePointsEffect(snake, settings)    # ポイント二倍効果
duration_effect = DurationBoostEffect(snake, settings)  # magnet/shield の効果時間3倍
# magnet/shield は効果時間3倍アイテムを参照する（拾った瞬間に持続へ倍率を掛ける）
magnets = MagnetManager(snake, food, obstacles, settings, duration_effect)
shields = ShieldManager(snake, food, obstacles, settings, duration_effect)
items = ItemBar(snake, users, settings, double_effect, duration_effect)  # 下部アイテムスロットHUD
score_counter = ScoreCounter(settings, users)
state = GameState(snake, food, obstacles, magnets, shields, items,
                  score_counter, settings, users, test_mode=TEST_CLEAR)

# 描画は一定のフレームレートで回し、スネークの前進は「経過時間」で進める。
# こうするとフレームレートがブレても移動速度(px/秒)が一定になる（HARDでも安定）。
RENDER_FPS = 120
move_accumulator = 0.0

# プレイ中はカーソルを「完全に透明な形」に差し替える。set_visible(False) だけだと
# ウィンドウ外⇔内を出し入れした時に稀にポインタが残るため、形自体を空にして確実に消す。
CURSOR_BLANK = pygame.cursors.Cursor((0, 0), pygame.Surface((1, 1), pygame.SRCALPHA))
CURSOR_ARROW = pygame.cursors.Cursor(*pygame.cursors.arrow)
cursor_hidden = None  # 直近に設定したカーソル状態（変化時だけ切り替える）

while state.is_on:
    dt = clock.tick(RENDER_FPS) / 1000.0  # 前フレームからの経過秒

    # 入力処理（矢印=方向, q=強制終了, クリック/マウス移動=ボタン）
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            state.quit()
        # ユーザー名入力中は、キー入力をゲーム操作ではなくテキスト欄へ回す
        # （TEXTEDITINGはIMEの変換中＝日本語入力の未確定文字）
        elif state.wants_text_input() and event.type in (pygame.KEYDOWN, pygame.TEXTINPUT, pygame.TEXTEDITING):
            state.handle_text_event(event)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                snake.up()
            elif event.key == pygame.K_DOWN:
                snake.down()
            elif event.key == pygame.K_LEFT:
                snake.left()
            elif event.key == pygame.K_RIGHT:
                snake.right()
            elif event.key == pygame.K_q:
                state.quit()
            elif event.key == pygame.K_s:
                state.press_start_key()  # スタート画面 / 難易度変更後のSTART表示で反応
            elif event.key == pygame.K_r:
                state.press_retry_key()  # RETRY表示（難易度そのまま）のときだけ反応
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                # 数字キーで下部スロットのアイテムを使う（プレイ中のみ反応）
                state.use_item(event.key - pygame.K_1)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            state.handle_click(*theme.to_world(*event.pos))
        elif event.type == pygame.MOUSEMOTION:
            state.handle_motion(*theme.to_world(*event.pos))

    # 実プレイ中だけマウスカーソルを隠す（メニュー・設定・ゲームオーバーは
    # ボタンをクリックするので表示しておく）。状態が変わった時だけ差し替える。
    playing = state.is_started and not state.is_over and not state.is_settings
    if playing != cursor_hidden:
        cursor_hidden = playing
        pygame.mouse.set_cursor(CURSOR_BLANK if playing else CURSOR_ARROW)

    # ゲーム進行: 経過時間を貯めて、STEP px進むのに必要な間隔ごとに1歩動かす。
    # 速いほど1フレームに複数回動く（HARDでも見た目の速度が安定する）。
    if playing:
        # 障害物の寿命・湧き直し・終盤の数調整（実時間ベース）
        obstacles.update(dt, score_counter.score, food)
        # マグネット・シールドの出現・寿命・取得・効果
        magnets.update(dt)
        shields.update(dt)
        items.update(dt)  # アイテム効果（ポイント二倍/効果時間3倍）の残り時間を進める

        move_accumulator += dt
        move_interval = STEP / settings.speed  # STEP px進むのにかかる秒数
        guard = 0  # ラグでdtが跳ねても暴走しないよう保険
        while move_accumulator >= move_interval and guard < 500:
            move_accumulator -= move_interval
            guard += 1
            snake.move()
            if snake.detect_wall() or snake.detect_tail():
                state.handle_game_over()
                break
            if snake.detect_block(obstacles):
                if shields.active:
                    # シールド中は破壊して突破。壊せたらブロック破壊ポイントを加算
                    if obstacles.break_block_at(snake.head):
                        score_counter.count_brick(double_effect.point_multiplier)
                else:
                    state.handle_game_over()
                    break
            # マグネット効果中は food の当たり判定を広げる
            if food.check_eaten(snake.head, EAT_DISTANCE * magnets.eat_multiplier):
                score_counter.count_orb(double_effect.point_multiplier)
                snake.increase_segments()
                # クリア判定はヘビの全長(px)。盤面を埋め尽くしたら勝ち（点数とは無関係）
                if len(snake.segments) * GRID >= MAX_FILL_PX:
                    state.handle_clear()
                    break
    else:
        move_accumulator = 0.0

    # 描画（毎フレーム全消去して描き直す）
    surface.fill(theme.BG)
    pygame.draw.rect(surface, theme.HUD_BG, (0, 0, theme.WIDTH, theme.HUD_HEIGHT))  # 上部のスコア帯
    # 下部のアイテム帯（プレイ領域の外。上部スコア帯と同様に常時表示）
    pygame.draw.rect(surface, theme.HUD_BG,
                     (0, theme.HUD_HEIGHT + theme.PLAY_H, theme.WIDTH, theme.HUD_BOTTOM_HEIGHT))
    obstacles.draw(surface)
    snake.draw(surface)
    food.draw(surface)
    magnets.draw(surface)
    shields.draw(surface)
    # HUDのSCORE表示はプレイ中だけにする（メニューで前回スコアが残らないように）
    score_counter.in_play = playing
    score_counter.draw(surface)
    # 下部アイテム帯のスロットは常時表示。残り時間バーは効果中のみ各スロット上に出る。
    items.draw(surface)
    state.draw(surface)
    pygame.display.flip()

pygame.quit()
