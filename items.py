import pygame
import theme

# 使用可能なアイテム種別の表示順（所持アイテムをこの順でスロットへ詰める）。
# 将来アイテムを増やしたらここに key を足す（ショップのカタログと対応）。
ITEM_ORDER = ["double_points", "duration_boost"]

# アイテムごとのポーション液体色（スロット/ショップのアイコン・残り時間バーで共用）
ITEM_COLORS = {
    "double_points": theme.POTION_LIQUID,
    "duration_boost": theme.POTION_LIQUID2,
}


# ポーション(フラスコ)を中心(cx, cy)に描く共通ヘルパ。液体色はアイテム別。
def draw_potion(surface, cx, cy, scale=1.0, liquid=theme.POTION_LIQUID):
    s = scale
    pygame.draw.circle(surface, theme.POTION_GLASS, (cx, cy + int(4 * s)), int(9 * s))   # 瓶本体
    pygame.draw.circle(surface, liquid, (cx, cy + int(5 * s)), int(6 * s))               # 液体
    neck = pygame.Rect(0, 0, int(7 * s), int(8 * s))                                     # 首
    neck.center = (cx, cy - int(7 * s))
    pygame.draw.rect(surface, theme.POTION_GLASS, neck, border_radius=int(2 * s))
    cork = pygame.Rect(0, 0, int(8 * s), int(4 * s))                                     # 栓
    cork.center = (cx, cy - int(11 * s))
    pygame.draw.rect(surface, theme.POTION_CORK, cork, border_radius=int(2 * s))


# item_key に応じたアイコン（ポーション）を描く（ItemBar / ショップで共用）
def draw_item_icon(surface, key, cx, cy, scale=1.0):
    draw_potion(surface, cx, cy, scale=scale, liquid=ITEM_COLORS.get(key, theme.POTION_LIQUID))


# 効果の共通土台: 発動で満タンから数え直し（上書き）、update でカウントダウン。
# 残り時間バーは ItemBar が各スロットの上に色付きで描く（複数効果を区別するため）。
class _TimedEffect:
    DURATION = 10.0   # 効果時間(秒) ※難易度の item_duration_scale を掛ける

    def __init__(self, snake, settings):
        self.snake = snake
        self.settings = settings
        self.active_timer = 0.0
        self.max_timer = self.DURATION

    @property
    def active(self):
        return self.active_timer > 0

    def activate(self):
        self.max_timer = self.DURATION * self.settings.difficulty.item_duration_scale
        self.active_timer = self.max_timer
        self._on_change(True)
        return True

    def update(self, dt):
        if self.active_timer > 0:
            self.active_timer -= dt
            if self.active_timer <= 0:
                self.active_timer = 0.0
        self._on_change(self.active)

    def reset(self):
        self.active_timer = 0.0
        self._on_change(False)

    # 効果のON/OFFが変わるたびに呼ばれる（サブクラスで見た目や状態を反映）
    def _on_change(self, on):
        pass


# 一定時間、獲得ポイントを2倍にする効果。効果中はヘビのボディ全体を金色に染める
# （頭オーラだと magnet/shield と視覚的に衝突するため）。
class DoublePointsEffect(_TimedEffect):
    DURATION = 10.0
    POINT_MULTIPLIER = 2

    # 点数に掛ける倍率（snakegame が count_orb/count_brick へ渡す）
    @property
    def point_multiplier(self):
        return self.POINT_MULTIPLIER if self.active else 1

    def _on_change(self, on):
        self.snake.tint = theme.SNAKE_BOOST if on else None


# 一定時間、効果中に拾った magnet/shield の効果持続を3倍にする。
# 効果時間は長め。拾った物・回数を問わず、効果中の取得はすべて3倍になる
# （magnet/shield 側が _pick_up 時に duration_multiplier を掛ける）。
class DurationBoostEffect(_TimedEffect):
    DURATION = 30.0
    MULTIPLIER = 3

    @property
    def duration_multiplier(self):
        return self.MULTIPLIER if self.active else 1


# プレイ画面下部のアイテムスロットHUD（4枠）。所持しているアイテムを
# ITEM_ORDER の順にスロットへ並べ、数字キー(1..4)で消費する。
# 効果の更新・リセット・残り時間バー描画もここでまとめて行う。
class ItemBar:
    SLOT_COUNT = 4
    SLOT_SIZE = 44
    SLOT_GAP = 10

    def __init__(self, snake, users, settings, double_points_effect, duration_boost_effect):
        self.snake = snake
        self.users = users
        self.settings = settings
        # item_key -> 対応する効果オブジェクト（拡張時はここに追加）
        self.effects = {
            "double_points": double_points_effect,
            "duration_boost": duration_boost_effect,
        }

    def update(self, dt):
        for effect in self.effects.values():
            effect.update(dt)

    def reset(self):
        for effect in self.effects.values():
            effect.reset()

    # 現在のスロット割り当て（所持アイテムを ITEM_ORDER 順に詰める）。
    # 長さ SLOT_COUNT のリストで、空きは None。
    def _slot_keys(self):
        owned = []
        for key in ITEM_ORDER:
            effect = self.effects.get(key)
            if self.users.item_count(key) > 0 or (effect is not None and effect.active):
                owned.append(key)
        slots = owned[:self.SLOT_COUNT]
        slots += [None] * (self.SLOT_COUNT - len(slots))
        return slots

    # 数字キー(index=0..3)でスロットのアイテムを使う。
    # 在庫が1個以上あれば消費して効果を発動（効果中でも上書き＝満タンから数え直す）。
    def use_slot(self, index):
        if index < 0 or index >= self.SLOT_COUNT:
            return
        key = self._slot_keys()[index]
        if key is None:
            return
        effect = self.effects.get(key)
        if effect is None or self.users.item_count(key) <= 0:
            return
        if effect.activate():
            self.users.use_item(key)

    def draw(self, surface):
        slots = self._slot_keys()
        total = self.SLOT_COUNT * self.SLOT_SIZE + (self.SLOT_COUNT - 1) * self.SLOT_GAP
        start_x = (theme.WIDTH - total) // 2
        # 下部アイテム帯の中にスロット行を置く（バーぶん下げる）
        band_top = theme.HUD_HEIGHT + theme.PLAY_H
        cy = band_top + 22 + self.SLOT_SIZE // 2
        for i, key in enumerate(slots):
            left = start_x + i * (self.SLOT_SIZE + self.SLOT_GAP)
            rect = pygame.Rect(left, cy - self.SLOT_SIZE // 2, self.SLOT_SIZE, self.SLOT_SIZE)
            # 下部帯（濃色）の上に、少し明るい凹みセルとして描く
            box = pygame.Surface((self.SLOT_SIZE, self.SLOT_SIZE), pygame.SRCALPHA)
            box.fill((255, 255, 255, 28))
            surface.blit(box, rect.topleft)
            pygame.draw.rect(surface, theme.SECONDARY, rect, width=2, border_radius=8)
            # キー番号（左上）
            theme.draw_text_screen(surface, str(i + 1), rect.left + 9, rect.top + 9,
                                   theme.HUD_TEXT, theme.FONT_SCORE)
            if key is None:
                continue
            draw_item_icon(surface, key, rect.centerx, rect.centery + 2, scale=0.95)
            # 所持数（右下）
            n = self.users.item_count(key)
            theme.draw_text_screen(surface, f"x{n}", rect.right - 13, rect.bottom - 9,
                                   theme.HUD_TEXT, theme.FONT_SCORE)
            # 効果中なら、そのスロットの真上に色付きの残り時間バー
            effect = self.effects.get(key)
            if effect is not None and effect.active and effect.max_timer > 0:
                frac = max(0.0, min(1.0, effect.active_timer / effect.max_timer))
                bx, by, bh = rect.left, rect.top - 9, 5
                pygame.draw.rect(surface, theme.TEXT_DIM, (bx, by, self.SLOT_SIZE, bh), border_radius=2)
                pygame.draw.rect(surface, ITEM_COLORS.get(key, theme.GOLD),
                                 (bx, by, int(self.SLOT_SIZE * frac), bh), border_radius=2)
