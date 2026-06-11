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

# TODO: 毎回開発元が信用できないと言われてアプデのたびに承認する必要があるのが非常に面倒、どうにかならないものか
# TODO: アイテム数を増やす（ショップのカタログに unlock_score 付きで1行足す方式）
# TODO: マリオの赤コインのようなイベント
# TODO: ボーナスイベントとして全面オーブのステージに転移する

# クリア演出の確認用。Trueにすると最大-1の長さで開始し、オーブ1個でクリアできる
TEST_CLEAR = False
# 初回起動フロー（ユーザー登録→チュートリアル）の確認用。Trueにすると users.json に
# ユーザーがいても登録画面から始まる（既存の名前を入れればそのまま選択されて進む）
TEST_FIRST_RUN = False
# ショップの開放演出の確認用。Trueにすると開放済みポーションが常に UNLOCK 表示になり、
# 何度でも演出を確認できる（seen の記録もしないので実データに影響しない）
TEST_SHOP_REVEAL = False
# 新機能紹介(What's New)の確認用。"1.1" のようにバージョン文字列を入れると、
# そのバージョンから更新した体で紹介スライドが出る（記録しないので何度でも確認できる）。
# 普段は None
TEST_WHATS_NEW = None

crashlog.install()  # 予期しない例外を crash.log に記録してから落ちる（配布版の調査用）

pygame.init()
# ウィンドウ/タスクバー用アイコン（無くても起動は続ける。set_mode の前に設定する）
try:
    pygame.display.set_icon(pygame.image.load(theme.resource_path("assets/icon_64.png")))
except (OSError, pygame.error):
    pass

# ウィンドウは自由にリサイズでき、Fキーで全画面と切り替えられる。
# ゲームは常に 600x720 の論理キャンバスへ描き、表示時にウィンドウへ等比で縮小拡大
# 転送する（余りはレターボックス）ので、座標系・速度・当たり判定などのゲーム性は
# 一切変わらない。初期サイズはモニターに収まる倍率（小型ディスプレイでは小さく開く）。
INITIAL_SCALE = theme.display_scale()
WINDOWED_SIZE = (int(theme.WIDTH * INITIAL_SCALE), int(theme.HEIGHT * INITIAL_SCALE))
window = pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)
surface = pygame.Surface((theme.WIDTH, theme.HEIGHT))  # 論理キャンバス
is_fullscreen = False

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
# 効果時間3倍ポーションは、飲んだ瞬間に発動中だった magnet/shield の残り時間も伸ばす
duration_effect.targets = [magnets, shields]
items = ItemBar(snake, users, settings, double_effect, duration_effect)  # 下部アイテムスロットHUD
# オーブ・レンガ・magnet・shield が互いに同じセルへ湧かないよう、相互参照を張る
magnets.peers = [shields]
shields.peers = [magnets]
food.item_managers = [magnets, shields]
obstacles.item_managers = [magnets, shields]
score_counter = ScoreCounter(settings, users)
state = GameState(snake, food, obstacles, magnets, shields, items,
                  score_counter, settings, users, test_mode=TEST_CLEAR,
                  test_first_run=TEST_FIRST_RUN, test_shop_reveal=TEST_SHOP_REVEAL,
                  test_whats_new=TEST_WHATS_NEW)

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
            elif event.key == pygame.K_f:
                # 全画面 ⇔ ウィンドウの切り替え
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    window = pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)
        # マウスはウィンドウ座標で来るので、レターボックス余白を引いて倍率で割り戻す
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
            s, ox, oy = theme.fit_scale(*window.get_size())
            wx, wy = theme.to_world((event.pos[0] - ox) / s, (event.pos[1] - oy) / s)
            if event.type == pygame.MOUSEBUTTONDOWN:
                state.handle_click(wx, wy)
            else:
                state.handle_motion(wx, wy)

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
        # ボーナスオーブの出現・寿命
        food.update(dt)
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
            # マグネット効果中は food の当たり判定を広げる。
            # 戻り値はオーブの得点倍率（通常1・金色のボーナスオーブは5、食べていなければ0）。
            # 伸びる長さはどのオーブでも同じ1セグメント。
            orb_multiplier = food.check_eaten(snake.head, EAT_DISTANCE * magnets.eat_multiplier)
            if orb_multiplier:
                score_counter.count_orb(double_effect.point_multiplier * orb_multiplier)
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
    # 論理キャンバスをウィンドウへ等比転送（余りはHUD色のレターボックス）
    win_size = window.get_size()
    if win_size == (theme.WIDTH, theme.HEIGHT):
        window.blit(surface, (0, 0))  # 等倍ならそのまま（転送コスト最小）
    else:
        s, ox, oy = theme.fit_scale(*win_size)
        scaled = pygame.transform.smoothscale(
            surface, (int(theme.WIDTH * s), int(theme.HEIGHT * s)))
        window.fill(theme.HUD_BG)
        window.blit(scaled, (ox, oy))
    pygame.display.flip()

pygame.quit()
