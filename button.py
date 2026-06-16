import math
import pygame
import theme


# ピル型(角丸)の塗りつぶしボタン + ラベル（または icon="gear" で歯車アイコン）
# クリック判定は世界座標(x, y)が contains() に入るかで行う
# ホバー中(hovered)は色を変えて描画する
class Button:
    def __init__(self, label, x, y, on_click, width=200, height=56,
                 color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER, text_color=theme.BUTTON_TEXT,
                 font=theme.FONT_BUTTON, label_offset=(0, 0), icon=None):
        self.label = label
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.on_click = on_click
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = font
        self.label_dx, self.label_dy = label_offset
        self.icon = icon  # None ならラベル、"gear" なら歯車を描く
        self.hovered = False

    def draw(self, surface):
        fill = self.hover_color if self.hovered else self.color
        cx, cy = theme.to_screen(self.x, self.y)
        rect = pygame.Rect(0, 0, self.width, self.height)
        rect.center = (cx, cy)
        # 角丸の半径=高さの半分 でピル型にする
        pygame.draw.rect(surface, fill, rect, border_radius=self.height // 2)
        if self.icon == "gear":
            self._draw_gear(surface, cx, cy, self.height * 0.32, self.text_color, fill)
        else:
            # ラベルを中央に描く（label_offset は世界座標の向き＝上が+y）
            theme.draw_text(surface, self.label,
                            self.x + self.label_dx, self.y + self.label_dy,
                            self.text_color, self.font)
            # ラベル付きボタンの左内側に小さなアイコンを添える（shop / loadout）
            if self.icon in ("shop", "loadout"):
                ix = cx - self.width / 2 + self.height * 0.55
                r = self.height * 0.26
                if self.icon == "shop":
                    self._draw_shop_icon(surface, ix, cy, r, self.text_color)
                else:
                    self._draw_loadout_icon(surface, ix, cy, r, self.text_color)

    # 歯車(コグ)を多角形で描く。color=歯車色, hole_color=中央の穴(=ボタン地色)
    def _draw_gear(self, surface, cx, cy, r, color, hole_color):
        teeth = 8
        r_out = r * 1.35   # 歯の先端
        r_in = r           # 歯の谷
        step = 2 * math.pi / teeth
        points = []
        for i in range(teeth):
            a = i * step
            # 1歯ぶん: 先端(平ら)→谷(平ら) を角で結ぶ
            points.append((a, r_out))
            points.append((a + step * 0.30, r_out))
            points.append((a + step * 0.50, r_in))
            points.append((a + step, r_in))
        coords = [(cx + math.cos(a) * rad, cy + math.sin(a) * rad) for a, rad in points]
        pygame.draw.polygon(surface, color, coords)
        # 中央の穴をボタン地色でくり抜く
        pygame.draw.circle(surface, hole_color, (cx, cy), r * 0.45)

    # ショッピングバッグのアイコン（本体＋上部の取っ手の弧）
    def _draw_shop_icon(self, surface, cx, cy, r, color):
        w = max(2, int(r * 0.22))
        body = pygame.Rect(0, 0, int(r * 1.6), int(r * 1.5))
        body.center = (int(cx), int(cy + r * 0.35))
        pygame.draw.rect(surface, color, body, width=w, border_radius=int(r * 0.22))
        # 取っ手（半円の弧）
        hr = pygame.Rect(int(cx - r * 0.5), int(cy - r * 0.7), int(r), int(r))
        pygame.draw.arc(surface, color, hr, 0.15, math.pi - 0.15, w)

    # ロードアウト（持ち物）のアイコン: 2x2 のスロット格子
    def _draw_loadout_icon(self, surface, cx, cy, r, color):
        s = r * 0.8
        gap = r * 0.28
        w = max(2, int(r * 0.16))
        for ox in (-1, 1):
            for oy in (-1, 1):
                rect = pygame.Rect(0, 0, int(s), int(s))
                rect.center = (int(cx + ox * (s / 2 + gap / 2)),
                               int(cy + oy * (s / 2 + gap / 2)))
                pygame.draw.rect(surface, color, rect, width=w, border_radius=int(r * 0.18))

    # クリック座標(x, y)がこのボタンの範囲内か（世界座標）
    def contains(self, x, y):
        return (self.x - self.width / 2 <= x <= self.x + self.width / 2
                and self.y - self.height / 2 <= y <= self.y + self.height / 2)

    def set_hover(self, value):
        self.hovered = value
