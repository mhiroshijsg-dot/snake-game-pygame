from functools import partial
import pygame
from button import Button
from items import draw_item_icon, ITEM_ORDER, ItemBar
from shop_screen import SHOP_ITEMS
from upgrades import UPGRADES, next_price
from snake import GRID, STEP
import theme

SLOT_COUNT = ItemBar.SLOT_COUNT  # 装備できるスロット数（下部HUDと一致させる）
HEADER_COLOR = theme.PRIMARY     # セクション見出しの色（金色は眩しすぎたので青系に）


# 恒常強化のアイコン（金色の丸に白い「+」）。専用アイコンが無いアップグレード共通。
def _draw_upgrade_icon(surface, cx, cy, scale=1.0):
    r = int(11 * scale)
    pygame.draw.circle(surface, theme.GOLD, (cx, cy), r)
    pygame.draw.circle(surface, theme.TEXT, (cx, cy), r, max(1, int(2 * scale)))
    w = max(2, int(2.5 * scale))
    pygame.draw.line(surface, theme.TEXT, (cx - r // 2, cy), (cx + r // 2, cy), w)
    pygame.draw.line(surface, theme.TEXT, (cx, cy - r // 2), (cx, cy + r // 2), w)


# ロードアウト/ステータス画面。Minecraft のインベントリ風に、自分のスネークの見た目・
# 装備中スロット（上段4枠）・持ち物グリッド（下段＝空きスロットも並べる）をアイコンで一覧。
# ・装備中スロットはタップで解除、ドラッグで別スロットと中身を入れ替え（並べ替え）
# ・持ち物のアイテムをクリックで装備/解除
# ・恒常強化（Point Boost 等）の購入もここで行う
# 共通I/F: show/hide/draw/handle_click/handle_motion
class LoadoutScreen:
    EQUIP_SLOT = 46
    INV_SLOT = 40
    SLOT_GAP = 10
    EQUIP_Y = -8       # 装備スロット行の中心Y（世界座標）
    INV_Y = -100       # 持ち物グリッド最上段の中心Y
    INV_COLS = 5
    INV_ROWS = 2       # 空きスロットも含めて並べる（後で増えるアイテム用の置き場）
    DRAG_THRESHOLD = 6 # これ以上動いたらタップではなくドラッグ扱い（世界座標の距離）

    def __init__(self, on_back, users):
        self.on_back = on_back
        self.users = users
        self.visible = False
        self.warning = ""
        self.buttons = []
        self.equip_slots = []   # 上段: 装備中の4枠 [(key, x, y, size)]（key は None もあり）
        self.item_slots = []    # 下段: 持ち物グリッド [(key, x, y, size)]（空きは key=None）
        self.hover_key = None   # ホバー中のアイテム key（名前ツールチップ用）
        self.drag_from = None   # ドラッグ中の装備スロット index（None=ドラッグしていない）
        self.drag_key = None    # ドラッグ中のアイテム key（カーソル追従アイコン用）
        self.drag_pos = None    # ドラッグ中のカーソル位置（世界座標）
        self.drag_start = None  # 押した位置（タップ/ドラッグの判別用）
        self.drag_moved = False # 押してから閾値以上動いたか（一度動けば戻してもドラッグ扱い）

    def show(self):
        self.visible = True
        self.warning = ""
        self.hover_key = None
        self._cancel_drag()
        self._build()

    def _cancel_drag(self):
        self.drag_from = None
        self.drag_key = None
        self.drag_pos = None
        self.drag_start = None
        self.drag_moved = False

    def hide(self):
        self.visible = False
        self.buttons = []
        self.equip_slots = []
        self.item_slots = []

    def _unlocked_items(self):
        best = self.users.best_high_score()
        return [it for it in SHOP_ITEMS if best >= it["unlock_score"]]

    # 現在の実効ロードアウト（編集済みならそれ＝空も尊重、未編集なら自動詰め相当）
    def _equipped(self):
        if self.users.loadout_is_set():
            return self.users.loadout()[:SLOT_COUNT]
        unlocked = {it["key"] for it in self._unlocked_items()}
        return [k for k in ITEM_ORDER if k in unlocked][:SLOT_COUNT]

    # 装備スロットを長さ SLOT_COUNT に揃えた並び（空きは None）。入れ替え操作の作業用。
    def _padded(self):
        eq = self._equipped()
        return (eq + [None] * SLOT_COUNT)[:SLOT_COUNT]

    def _build(self):
        self.buttons = []
        self.equip_slots = []
        self.item_slots = []
        gap = self.SLOT_GAP

        # アップグレードの BUY ボタン
        y = 120
        for up in UPGRADES:
            level = self.users.upgrade_level(up["key"])
            price = next_price(up, level)
            if price is not None:
                self.buttons.append(
                    Button("BUY", 175, y, partial(self._buy_upgrade, up), width=110, height=46,
                           color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER))
            y -= 80

        # 装備中スロット（上段4枠・固定位置）
        padded = self._padded()
        s = self.EQUIP_SLOT
        total = SLOT_COUNT * s + (SLOT_COUNT - 1) * gap
        left = -total / 2 + s / 2
        for i in range(SLOT_COUNT):
            self.equip_slots.append((padded[i], left + i * (s + gap), self.EQUIP_Y, s))

        # 持ち物グリッド（下段・空きスロットも並べる）
        items = self._unlocked_items()
        s2 = self.INV_SLOT
        total2 = self.INV_COLS * s2 + (self.INV_COLS - 1) * gap
        left0 = -total2 / 2 + s2 / 2
        for idx in range(self.INV_COLS * self.INV_ROWS):
            col = idx % self.INV_COLS
            row = idx // self.INV_COLS
            key = items[idx]["key"] if idx < len(items) else None
            x = left0 + col * (s2 + gap)
            yy = self.INV_Y - row * (s2 + gap)
            self.item_slots.append((key, x, yy, s2))

        self.buttons.append(Button("BACK", 0, -238, self.on_back,
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

    # 持ち物のアイテムをクリック: 装備/解除をトグル。
    # 解除はそのスロットを空き(None)にするだけ＝他のアイテムは詰めない（位置を保持）。
    def _toggle_equip(self, key):
        p = self._padded()
        if key in p:
            p = [None if k == key else k for k in p]
        else:
            if None not in p:
                self.warning = f"Only {SLOT_COUNT} slots"
                return
            p[p.index(None)] = key
        self.users.set_loadout(p)   # 空きはそのまま保存（左詰めしない）
        self.warning = ""

    # 装備スロット i と j の中身を入れ替える（並べ替え。空き同士・空きとの交換もそのまま）
    def _swap_slots(self, i, j):
        p = self._padded()
        p[i], p[j] = p[j], p[i]
        self.users.set_loadout(p)

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
        theme.draw_text(surface, "UPGRADES", -200, 162, HEADER_COLOR, theme.FONT_NAME_SMALL)
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
        hx, hy = theme.to_screen(*points[-1])
        fx, fy = 1.0, 0.0
        px, py = -fy, fx
        for side in (1, -1):
            ex = hx + fx * r * 0.45 + px * side * r * 0.40
            ey = hy + fy * r * 0.45 + py * side * r * 0.40
            pygame.draw.circle(surface, theme.TEXT, (int(ex), int(ey)), max(1, int(r * 0.18)))

    # 1スロットを描く。equipped=金枠, highlight=青の太枠（ドラッグ元/落下先）。
    # hide_icon=True ならアイコンを描かない（ドラッグ中の元スロットを空に見せる）。
    def _draw_slot_box(self, surface, key, x, y, size, equipped=False, highlight=False,
                       hide_icon=False):
        cx, cy = theme.to_screen(x, y)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(cx), int(cy))
        box = pygame.Surface((size, size), pygame.SRCALPHA)
        box.fill((*theme.GOLD[:3], 46) if equipped else (255, 255, 255, 28))
        surface.blit(box, rect.topleft)
        if highlight:
            pygame.draw.rect(surface, theme.PRIMARY, rect, width=4, border_radius=8)
        else:
            border = theme.GOLD if equipped else theme.SECONDARY
            pygame.draw.rect(surface, border, rect, width=3 if equipped else 2, border_radius=8)
        if key is not None and not hide_icon:
            count = self.users.item_count(key)
            draw_item_icon(surface, key, rect.centerx, rect.centery + 1, scale=1.0)
            # 個数バッジ（右下）。読みやすいよう濃色で描く
            col = theme.TEXT if count > 0 else theme.TEXT_DIM
            theme.draw_text_screen(surface, f"x{count}", rect.right - 12, rect.bottom - 10,
                                   col, theme.FONT_SCORE)
        return rect

    def _draw_gear(self, surface):
        # ドラッグ中なら、落下先になる装備スロットを求めてハイライトする
        drop_target = None
        if self.drag_from is not None and self.drag_pos is not None:
            drop_target = self._hit_index(self.equip_slots, *self.drag_pos)

        theme.draw_text(surface, "EQUIPPED", -200, 30, HEADER_COLOR, theme.FONT_NAME_SMALL)
        for i, (key, x, y, size) in enumerate(self.equip_slots):
            highlight = i == drop_target or i == self.drag_from
            rect = self._draw_slot_box(surface, key, x, y, size,
                                       equipped=key is not None, highlight=highlight,
                                       hide_icon=(i == self.drag_from))
            theme.draw_text_screen(surface, str(i + 1), rect.left + 7, rect.top + 7,
                                   theme.TEXT_DIM, theme.FONT_SCORE)

        theme.draw_text(surface, "ITEMS", -200, -55, HEADER_COLOR, theme.FONT_NAME_SMALL)
        equipped = self._equipped()
        for key, x, y, size in self.item_slots:
            self._draw_slot_box(surface, key, x, y, size, equipped=key in equipped if key else False)

        # 下部の案内 / ツールチップ
        if self.drag_from is not None:
            theme.draw_text(surface, "Drop onto a slot to rearrange", 0, -198,
                            theme.PRIMARY, theme.FONT_SCORE)
        elif self.hover_key:
            name = self._item_name(self.hover_key)
            action = "unequip" if self.hover_key in equipped else "equip"
            theme.draw_text(surface, f"{name}  —  tap to {action}", 0, -198,
                            theme.TEXT, theme.FONT_SCORE)
        else:
            theme.draw_text(surface, "Tap to equip / unequip · drag a slot to rearrange",
                            0, -198, theme.TEXT_DIM, theme.FONT_SCORE)

        # ドラッグ中のアイコンをカーソルに追従させて描く（最前面）
        if self.drag_key is not None and self.drag_pos is not None:
            cx, cy = theme.to_screen(*self.drag_pos)
            draw_item_icon(surface, self.drag_key, int(cx), int(cy), scale=1.1)

    def _item_name(self, key):
        for it in SHOP_ITEMS:
            if it["key"] == key:
                return it["name"]
        return key

    # クリック位置にあるアイテム key（空き/無しは None）
    def _hit(self, slots, x, y):
        for key, sx, sy, size in slots:
            if key is not None and abs(x - sx) <= size / 2 and abs(y - sy) <= size / 2:
                return key
        return None

    # クリック位置の装備スロット index（空きでも index は返す＝入れ替え先になる）
    def _hit_index(self, slots, x, y):
        for idx, (key, sx, sy, size) in enumerate(slots):
            if abs(x - sx) <= size / 2 and abs(y - sy) <= size / 2:
                return idx
        return None

    # マウス押下: ボタン → 装備スロット（ドラッグ開始）→ 持ち物（装備トグル）の順で判定
    def handle_click(self, x, y):
        for button in self.buttons:
            if button.contains(x, y):
                button.on_click()
                return
        i = self._hit_index(self.equip_slots, x, y)
        if i is not None:
            padded = self._padded()
            if padded[i] is not None:  # 中身のあるスロットだけ掴める
                self.drag_from = i
                self.drag_key = padded[i]
                self.drag_pos = (x, y)
                self.drag_start = (x, y)
                self.drag_moved = False
            return
        key = self._hit(self.item_slots, x, y)
        if key is not None:
            self._toggle_equip(key)
            self._build()

    def handle_motion(self, x, y):
        for button in self.buttons:
            button.set_hover(button.contains(x, y))
        if self.drag_from is not None:
            self.drag_pos = (x, y)   # ドラッグ中はカーソル位置を更新
            self._note_movement(x, y)
        self.hover_key = self._hit(self.equip_slots, x, y) or self._hit(self.item_slots, x, y)

    # 押した位置から閾値以上離れたらドラッグ確定（手ぶれ程度ならタップのまま）
    def _note_movement(self, x, y):
        sx, sy = self.drag_start
        if (x - sx) ** 2 + (y - sy) ** 2 >= self.DRAG_THRESHOLD ** 2:
            self.drag_moved = True

    # マウスを離した: 動かしていなければタップ＝解除、
    # ドラッグして別の装備スロットの上なら入れ替え、それ以外はキャンセル
    def handle_release(self, x, y):
        if self.drag_from is None:
            return
        self._note_movement(x, y)
        if self.drag_moved:
            j = self._hit_index(self.equip_slots, x, y)
            if j is not None and j != self.drag_from:
                self._swap_slots(self.drag_from, j)
        else:
            self._toggle_equip(self.drag_key)
        self._cancel_drag()
        self._build()
        # 解除/入れ替えで中身が変わるので、案内文を今のスロットに合わせ直す
        self.hover_key = self._hit(self.equip_slots, x, y) or self._hit(self.item_slots, x, y)
