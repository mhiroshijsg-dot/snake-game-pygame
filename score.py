import math
import random
import pygame
import theme

# クリア演出のコンフェッティ（紙吹雪）。起動時に一度だけ配置を決める
_CONFETTI_COLORS = ["#ff4d4d", "#ffcf40", "#4dd2ff", "#ff7ad9", "#7cff6b", "#b07cff"]
_CONFETTI = [
    {
        "x": random.uniform(0, theme.PLAY_W),
        "speed": random.uniform(80, 220),     # px/秒
        "phase": random.uniform(0, theme.PLAY_H),
        "size": random.randint(5, 11),
        "color": pygame.Color(random.choice(_CONFETTI_COLORS)),
        "sway": random.uniform(8, 24),         # 横揺れ幅
    }
    for _ in range(70)
]


# TODO 5: create scoreboard
# ハイスコアの保存は UserManager（ユーザー×難易度ごと）に委譲する
class ScoreCounter:
    def __init__(self, settings, users):
        self.settings = settings  # 現在の難易度を知るため
        self.users = users        # 現在のユーザーのハイスコアを読み書きするため
        self.score = 0
        self.visible = True
        self.mode = "bar"  # "bar"=上部HUDのスコア表示 / "over"=中央のゲームオーバー表示
        self.new_record = False  # 今回の結果が自己ベスト更新か
        self.in_play = False     # 実プレイ中か（HUDに現在スコアを出すのはこの時だけ）

    # 現在のユーザー×現在の難易度のハイスコア
    @property
    def high_score(self):
        return self.users.high_score(self.settings.difficulty_key)

    # オーブを1個食べた時の加点（難易度別 orb_points × 効果倍率）
    def count_orb(self, multiplier=1):
        self.score += self.settings.difficulty.orb_points * multiplier

    # ブロックを1個破壊した時の加点（難易度別 brick_points × 効果倍率）
    def count_brick(self, multiplier=1):
        self.score += self.settings.difficulty.brick_points * multiplier

    # ゲームオーバー/クリア時に呼ぶ。ベスト更新を判定して保存し、
    # この回の獲得点をウォレット（累計ポイント）へ積み立てる。
    def finalize_score(self):
        self.new_record = self.score > self.high_score
        self.save_high_score()
        self.users.add_to_wallet(self.score)

    def show_game_over(self):
        self.mode = "over"
        self.visible = True

    def show_clear(self):
        self.mode = "clear"
        self.visible = True

    # 設定画面を開くときなどに表示を消す
    def clear(self):
        self.visible = False

    def show(self):
        self.visible = True

    # 現在のユーザー×難易度のハイスコアを更新して保存する
    def save_high_score(self):
        self.users.update_high_score(self.settings.difficulty_key, self.score)

    def reset(self):
        # ベストはゲームオーバー時の finalize_score() で既に保存済み。
        # ここで保存すると、難易度を切り替えた後のリスタートで前の難易度のスコアが
        # 新しい難易度のベストに混入してしまうため、保存しない。
        self.score = 0
        self.mode = "bar"
        self.visible = True
        self.new_record = False

    def draw(self, surface):
        if not self.visible:
            return
        if self.mode == "over":
            self._draw_game_over(surface)
        elif self.mode == "clear":
            self._draw_clear(surface)
        else:
            self._draw_hud(surface)

    # 上部HUD帯にプレイヤー・難易度・スコア・ベストを1行で表示
    def _draw_hud(self, surface):
        player = self.users.current or ""  # 初回登録が済むまでは空欄
        mode = self.settings.difficulty_key
        # メニュー等（非プレイ中）は現在スコアを出さない（前回の値が残って見えるのを防ぐ）
        if self.in_play:
            text = f"{player}    {mode}    SCORE: {self.score}    BEST: {self.high_score}"
        else:
            text = f"{player}    {mode}    BEST: {self.high_score}"
        theme.draw_text_screen(
            surface, text,
            theme.WIDTH / 2, theme.HUD_HEIGHT / 2, theme.HUD_TEXT, theme.FONT_NAME_SMALL)

    def _draw_game_over(self, surface):
        player = self.users.current
        mode = self.settings.difficulty_key
        theme.draw_text(surface, "Game Over", 0, 82, theme.TEXT, theme.FONT_BIG)
        theme.draw_text(surface, f"{player}  ·  {mode}", 0, 44, theme.TEXT_DIM, theme.FONT_NAME_SMALL)
        theme.draw_text(surface, f"Score  {self.score}     Best  {self.high_score}",
                        0, 16, theme.TEXT_DIM, theme.FONT_SCORE)
        if self.new_record:
            self._draw_new_record(surface)

    # 理論上の最大に到達＝盤面クリアの派手な演出（時間ベースでループし続ける）
    def _draw_clear(self, surface):
        t = pygame.time.get_ticks()
        sec = t / 1000.0
        # 盤面を埋めた風に、プレイ領域を蛇色で塗りつぶす
        play = pygame.Rect(0, theme.HUD_HEIGHT, theme.PLAY_W, theme.PLAY_H)
        surface.fill(theme.SNAKE_COLOR, play)
        cx, cy = theme.to_screen(0, 0)

        # 中心から広がる金色のリング（4本を位相ずらしでループ）
        for k in range(4):
            phase = (sec * 0.6 + k / 4.0) % 1.0
            radius = int(phase * 380)
            if radius > 3:
                alpha = max(0, int(220 * (1 - phase)))
                ring = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(ring, (*theme.GOLD[:3], alpha),
                                   (radius + 4, radius + 4), radius, 7)
                surface.blit(ring, (cx - radius - 4, cy - radius - 4))

        # コンフェッティ（紙吹雪）が降り続ける
        for c in _CONFETTI:
            y = (c["phase"] + c["speed"] * sec) % (theme.PLAY_H + 40)
            sx = c["x"] + math.sin(sec * 2 + c["phase"]) * c["sway"]
            sy = theme.HUD_HEIGHT + y - 20
            rect = pygame.Rect(0, 0, c["size"], c["size"])
            rect.center = (sx, sy)
            pygame.draw.rect(surface, c["color"], rect, border_radius=2)

        # 「PERFECT!」を虹色＋拡縮＋上下バウンドで（大袈裟に）
        pulse = (math.sin(sec * 6) + 1) / 2
        bob = math.sin(sec * 3) * 14
        color = pygame.Color(0)
        color.hsva = ((t * 0.12) % 360, 90, 100, 100)
        label = theme.font(theme.FONT_TITLE).render("PERFECT!", True, color)
        scale = 1.0 + 0.3 * pulse
        w, h = label.get_size()
        label = pygame.transform.smoothscale(label, (int(w * scale), int(h * scale)))
        rect = label.get_rect(center=theme.to_screen(0, 60 + bob))
        # 白フチで縁取り風に少しずらして重ねる
        surface.blit(label, rect)

        theme.draw_text(surface, "BOARD CLEARED!", 0, 0, theme.BUTTON_TEXT, theme.FONT_BIG)
        theme.draw_text(surface, f"{self.users.current}   ·   {self.settings.difficulty_key}   ·   Score {self.score}",
                        0, -40, theme.BUTTON_TEXT, theme.FONT_NAME_SMALL)

    # 「NEW HIGH SCORE!」を金色で脈動＋拡縮させる演出
    def _draw_new_record(self, surface):
        pulse = (math.sin(pygame.time.get_ticks() * 0.006) + 1) / 2  # 0..1
        color = theme.GOLD.lerp(theme.BUTTON_TEXT, pulse * 0.5)
        label = theme.font(theme.FONT_BUTTON).render("NEW HIGH SCORE!", True, color)
        scale = 1.0 + 0.12 * pulse
        w, h = label.get_size()
        label = pygame.transform.smoothscale(label, (int(w * scale), int(h * scale)))
        rect = label.get_rect(center=theme.to_screen(0, -18))
        surface.blit(label, rect)
