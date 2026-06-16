import math
from functools import partial
import pygame
from button import Button
from items import draw_item_icon, ITEM_ORDER, ItemBar
from shop_screen import SHOP_ITEMS
from upgrades import UPGRADES, next_price
from snake import GRID, STEP
import theme

SLOT_COUNT = ItemBar.SLOT_COUNT  # 装備できるスロット数（下部HUDと一致させる）


# 恒常強化のアイコン（金色の丸に白い「+」）。専用アイコンが無いアップグレード共通。
def _draw_upgrade_icon(surface, cx, cy, scale=1.0):
    r = int(11 * scale)
    pygame.draw.circle(surface, theme.GOLD, (cx, cy), r)
    pygame.draw.circle(surface, theme.TEXT, (cx, cy), r, max(1, int(2 * scale)))
    w = max(2, int(2.5 * scale))
    pygame.draw.line(surface, theme.TEXT, (cx - r // 2, cy), (cx + r // 2, cy), w)
    pygame.draw.line(surface, theme.TEXT, (cx, cy - r // 2), (cx, cy + r // 2), w)


# ロードアウト/ステータス画面。Minecraft のインベントリ風に、自分のスネークの見た目・
# 装備中アイテム（上段スロット）・所持アイテム（下段グリッド）をアイコンで一覧する。
# 恒常強化（Point Boost 等）の購入もここで行う。
# 共通I/F: show/hide/draw/handle_click/handle_motion
class LoadoutScreen:
    SLOT = 50          # アイテム枠の一辺(px)
    SLOT_GAP = 12

    def __init__(self, on_back, users):
        self.on_back = on_back
        self.users = users
        self.visible = False
        self.warning = ""
        self.buttons = []
        # アイコン枠 [(key, x, y, size)]（世界座標の中心と一辺）。クリック/ホバー判定に使う
        self.equip_slots = []   # 上段: 装備中の4枠
        self.item_slots = []    # 下段: 所持アイテムのグリッド
        self.hover_key = None   # ホバー中のアイテム key（名前ツールチップ表示用）

    def show(self):
        self.visible = True
        self.warning = ""
        self.hover_key = None
        self._build()

    def hide(self):
        self.visible = False
        self.buttons = []
        self.equip_slots = []
        self.item_slots = []

    def _unlocked_items(self):
        best = self.users.best_high_score()
        return [it for it in SHOP_ITEMS if best >= it["unlock_score"]]

    # 現在の実効ロードアウト（保存があればそれ、無ければ自動詰め相当）
    def _equipped(self):
        lo = self.users.loadout()
        if lo:
            return [k for k in lo][:SLOT_COUNT]
        unlocked = {it["key"] for it in self._unlocked_items()}
        return [k for k in ITEM_ORDER if k in unlocked][:SLOT_COUNT]

    def _build(self):
        self.buttons = []
        self.equip_slots = []
        self.item_slots = []
        # アップグレードの BUY ボタン（解放/上限の都合で None の時は出さない）
        y = 120
        for up in UPGRADES:
            level = self.users.upgrade_level(up["key"])
            price = next_price(up, level)
            if price is not None:
                self.buttons.append(
                    Button("BUY", 175, y, partial(self._buy_upgrade, up), width=110, height=46,
                           color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
            y -= 80

        # 装備中スロット（上段4枠）を中央に並べる
        equipped = self._equipped()
        s, gap = self.SLOT, self.SLOT_GAP
        total = SLOT_COUNT * s + (SLOT_COUNT - 1) * gap
        left = -total / 2 + s / 2
        for i in range(SLOT_COUNT):
            key = equipped[i] if i < len(equipped) else None
            self.equip_slots.append((key, left + i * (s + gap), -30, s))

        # 所持（解放済み）アイテムのグリッド（下段）。アイコンのみ＋個数バッジ
        items = self._unlocked_items()
        per_row = 5
        n = len(items)
        first_row = min(n, per_row)
        row_total = first_row * s + (first_row - 1) * gap
        left0 = -row_total / 2 + s / 2
        gy = -135
        for i, it in enumerate(items):
            col = i % per_row
            row = i // per_row
            self.item_slots.append((it["key"], left0 + col * (s + gap), gy - row * (s + gap), s))

        self.buttons.append(Button("BACK", 0, -235, self.on_back,
                                   color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER))

    def _buy_upgrade(self, up):
        level = self.users.upgrade_level(up["key"])
        price = next_price(up, level)
        if price is None:
            self.warning = "Max level"
            return
        if self.users.spend(price):
            self.users.add_upgrade(up["key"])
            self.warning = ""
        else:
            self.warning = "Not enough points"
        self._build()

    def _toggle_equip(self, key):
        equipped = self._equipped()
        if key in equipped:
            equipped = [k for k in equipped if k != key]
        else:
            if len(equipped) >= SLOT_COUNT:
                self.warning = f"Only {SLOT_COUNT} slots"
                return
            equipped = equipped + [key]
        self.users.set_loadout(equipped)
        self.warning = ""
        self._build()

    # --- 描画 ---
    def draw(self, surface):
        if not self.visible:
            return
        theme.draw_text(surface, "LOADOUT", 0, 250, theme.TEXT, theme.FONT_TITLE)
        theme.draw_text(surface, f"{self.users.current}    Points: {self.users.wallet}",
                        0, 205, theme.TEXT_DIM, theme.FONT_NAME_SMALL)
        if self.warning:
            theme.draw_text(surface, self.warning, 175, 200, theme.WARNING, theme.FONT_SCORE)

        self._draw_upgrades(surface)
        self._draw_snake(surface)
        self._draw_gear(surface)
        for button in self.buttons:
            button.draw(surface)

    def _draw_upgrades(self, surface):
        theme.draw_text(surface, "UPGRADES", -200, 162, theme.GOLD, theme.FONT_NAME_SMALL)
        y = 120
        for up in UPGRADES:
            level = self.users.upgrade_level(up["key"])
            price = next_price(up, level)
            cx, cy = theme.to_screen(-215, y)
            _draw_upgrade_icon(surface, int(cx), int(cy), scale=1.2)
            theme.draw_text(surface, f'{up["name"]}   Lv {level}', -55, y + 12,
                            theme.TEXT, theme.FONT_BUTTON)
            desc = up.get("desc", [])
            sub = desc[-1].format(lvl=level) if desc else ""
            theme.draw_text(surface, sub, -55, y - 11, theme.TEXT_DIM, theme.FONT_SCORE)
            label = f"Next: {price} pt" if price is not None else "MAX"
            theme.draw_text(surface, label, 175, y - 30, theme.TEXT_DIM, theme.FONT_SCORE)
            y -= 80

    # プレイヤーのスネークを横向きに小さくプレビュー（本物と同じ縞模様＋目）
    def _draw_snake(self, surface):
        r = 9
        per_band = GRID // STEP
        x0, x1, sy = -70, 70, 70
        points = [(x, sy) for x in range(x0, x1 + 1, STEP)]  # 尾→頭（右向き）
        last = len(points) - 1
        for i in range(last, -1, -1):
            x, y = points[i]
            color = theme.SNAKE_PATTERN if ((last - i) // per_band) % 2 == 1 else theme.SNAKE_COLOR
            cx, cy = theme.to_screen(x, y)
            pygame.draw.circle(surface, color, (cx, cy), r)
        # 目（heading=0＝右向き）
        hx, hy = theme.to_screen(*points[-1])
        fx, fy = 1.0, 0.0
        px, py = -fy, fx
        for side in (1, -1):
            ex = hx + fx * r * 0.45 + px * side * r * 0.40
            ey = hy + fy * r * 0.45 + py * side * r * 0.40
            pygame.draw.circle(surface, theme.TEXT, (int(ex), int(ey)), max(1, int(r * 0.18)))

    def _draw_slot_box(self, surface, key, x, y, size, equipped):
        cx, cy = theme.to_screen(x, y)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(cx), int(cy))
        box = pygame.Surface((size, size), pygame.SRCALPHA)
        # 装備中は淡い金、それ以外は淡い白の凹みセル
        box.fill((*theme.GOLD[:3], 46) if equipped else (255, 255, 255, 28))
        surface.blit(box, rect.topleft)
        border = theme.GOLD if equipped else theme.SECONDARY
        pygame.draw.rect(surface, border, rect, width=3 if equipped else 2, border_radius=8)
        if key is not None:
            count = self.users.item_count(key)
            draw_item_icon(surface, key, rect.centerx, rect.centery + 1, scale=1.0)
            # 個数バッジ（右下）。0個は暗く
            col = theme.HUD_TEXT if count > 0 else theme.TEXT_DIM
            theme.draw_text_screen(surface, f"x{count}", rect.right - 12, rect.bottom - 10,
                                   col, theme.FONT_SCORE)
        return rect

    def _draw_gear(self, surface):
        equipped = self._equipped()
        theme.draw_text(surface, "EQUIPPED", -200, 18, theme.GOLD, theme.FONT_NAME_SMALL)
        for i, (key, x, y, size) in enumerate(self.equip_slots):
            rect = self._draw_slot_box(surface, key, x, y, size, equipped=key is not None)
            theme.draw_text_screen(surface, str(i + 1), rect.left + 7, rect.top + 7,
                                   theme.TEXT_DIM, theme.FONT_SCORE)

        theme.draw_text(surface, "ITEMS", -200, -97, theme.GOLD, theme.FONT_NAME_SMALL)
        for key, x, y, size in self.item_slots:
            self._draw_slot_box(surface, key, x, y, size, equipped=key in equipped)

        # ホバー中のアイテム名をツールチップとして1行表示（クリックで装備/解除）
        if self.hover_key:
            name = self._item_name(self.hover_key)
            tip = f"{name}  —  tap to {'unequip' if self.hover_key in equipped else 'equip'}"
            theme.draw_text(surface, tip, 0, -200, theme.TEXT, theme.FONT_SCORE)

    def _item_name(self, key):
        for it in SHOP_ITEMS:
            if it["key"] == key:
                return it["name"]
        return key

    def _hit(self, slots, x, y):
        for entry in slots:
            key, sx, sy, size = entry
            if key is not None and abs(x - sx) <= size / 2 and abs(y - sy) <= size / 2:
                return key
        return None

    def handle_click(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                button.on_click()
                return
        # 装備中スロットを押したら解除、所持グリッドを押したらトグル
        key = self._hit(self.equip_slots, x, y) or self._hit(self.item_slots, x, y)
        if key is not None:
            self._toggle_equip(key)

    def handle_motion(self, x, y):
        for button in self.buttons:
            button.set_hover(button.contains(x, y))
        self.hover_key = self._hit(self.equip_slots, x, y) or self._hit(self.item_slots, x, y)
