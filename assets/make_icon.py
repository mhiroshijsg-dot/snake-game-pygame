# アプリアイコンの生成スクリプト（手動実行用）。
# ゲームと同じ配色のスネークを pygame で描き、以下を assets/ に出力する:
#   icon_1024.png … 大元（各サイズはここから縮小）
#   icon_64.png   … 実行時のウィンドウアイコン用（snakegame.py が読む）
#   icon.ico      … Windows用（PNG圧縮エントリを自前でパック）
#   icon.iconset/ … macOS用の中間フォルダ（iconutil -c icns で icon.icns にする）
# 実行: .venv/bin/python assets/make_icon.py
import math
import struct
from pathlib import Path

import pygame

HERE = Path(__file__).resolve().parent
S = 1024  # 大元のキャンバス一辺

# ゲーム本体 theme.py と同じ配色
BG = pygame.Color("#1b1f3b")          # HUDと同じ濃い藍
SNAKE = pygame.Color("#2fb344")
SNAKE_PATTERN = pygame.Color("#249838")
ORB = pygame.Color("#8b3ff0")
ORB_GLOW = pygame.Color("#b985ff")
ORB_HIGHLIGHT = pygame.Color("#ede3ff")
EYE_WHITE = pygame.Color("#f4f6fb")
EYE_PUPIL = pygame.Color("#1b1f3b")
TONGUE = pygame.Color("#e8453c")


def draw_icon():
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    # macOS風: 少し内側に角丸スクエアの背景（外周は透過マージン）
    margin = int(S * 0.05)
    rect = pygame.Rect(margin, margin, S - margin * 2, S - margin * 2)
    pygame.draw.rect(surf, BG, rect, border_radius=int(S * 0.22))

    # 蛇の通るS字カーブ（左下の尾 → 右上の頭）。点を密に打って太い体を描く
    n = 240
    body_r = S * 0.085
    pts = []
    for i in range(n + 1):
        t = i / n
        x = S * (0.18 + 0.56 * t)
        y = S * 0.52 + math.sin(t * math.pi * 2.2 + math.pi * 0.9) * S * 0.215
        pts.append((x, y))

    # 尾→頭の順に描いて頭を最前面に。GRID相当の間隔で2色の縞にする
    band = max(1, n // 11)
    for i in range(n, -1, -1):
        color = SNAKE_PATTERN if (i // band) % 2 == 1 else SNAKE
        r = body_r * (0.55 + 0.45 * min(1.0, (n - i) / (n * 0.25)))  # 尾はやや細く
        pygame.draw.circle(surf, color, pts[i], r)

    # 頭（最後の点を少し大きく）＋目＋舌
    hx, hy = pts[-1]
    head_r = body_r * 1.25
    pygame.draw.circle(surf, SNAKE, (hx, hy), head_r)
    # 進行方向（カーブの接線方向）
    dx = pts[-1][0] - pts[-3][0]
    dy = pts[-1][1] - pts[-3][1]
    d = math.hypot(dx, dy) or 1.0
    fx, fy = dx / d, dy / d
    px, py = -fy, fx
    for side in (1, -1):
        ex = hx + fx * head_r * 0.40 + px * side * head_r * 0.42
        ey = hy + fy * head_r * 0.40 + py * side * head_r * 0.42
        pygame.draw.circle(surf, EYE_WHITE, (ex, ey), head_r * 0.30)
        pygame.draw.circle(surf, EYE_PUPIL, (ex + fx * head_r * 0.08, ey + fy * head_r * 0.08),
                           head_r * 0.16)
    # 舌（先が二股）
    t0 = (hx + fx * head_r * 0.95, hy + fy * head_r * 0.95)
    t1 = (hx + fx * head_r * 1.55, hy + fy * head_r * 1.55)
    pygame.draw.line(surf, TONGUE, t0, t1, int(S * 0.012))
    for side in (1, -1):
        tip = (t1[0] + (fx + px * side * 0.7) * head_r * 0.30,
               t1[1] + (fy + py * side * 0.7) * head_r * 0.30)
        pygame.draw.line(surf, TONGUE, t1, tip, int(S * 0.010))

    # 頭の先に魔法のオーブ（ゲームのfoodと同じ三層: 光・本体・ハイライト）
    # 角丸背景からはみ出さないようにオーブの中心をクランプする
    ox = hx + fx * head_r * 2.6
    oy = hy + fy * head_r * 2.6
    lim = S - margin - S * 0.16
    ox, oy = min(ox, lim), max(oy, S - lim)
    orb_r = S * 0.062
    glow = pygame.Surface((int(orb_r * 4), int(orb_r * 4)), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*ORB_GLOW[:3], 90), (int(orb_r * 2), int(orb_r * 2)), int(orb_r * 2))
    surf.blit(glow, (ox - orb_r * 2, oy - orb_r * 2))
    pygame.draw.circle(surf, ORB, (ox, oy), orb_r)
    pygame.draw.circle(surf, ORB_HIGHLIGHT,
                       (ox - orb_r * 0.35, oy - orb_r * 0.35), orb_r * 0.32)
    return surf


def save_png(surf, size, path):
    scaled = pygame.transform.smoothscale(surf, (size, size))
    pygame.image.save(scaled, str(path))
    return path


# PNG圧縮エントリのICO(Vista以降対応)を自前でパックする
def write_ico(png_paths, out_path):
    images = [(size, p.read_bytes()) for size, p in png_paths]
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    offset = 6 + 16 * len(images)
    body = b""
    for size, data in images:
        w = h = 0 if size >= 256 else size  # 256は0と書く決まり
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        body += data
        offset += len(data)
    out_path.write_bytes(header + entries + body)


def main():
    pygame.init()
    surf = draw_icon()

    save_png(surf, 1024, HERE / "icon_1024.png")
    save_png(surf, 64, HERE / "icon_64.png")

    # Windows .ico（16〜256の代表サイズ）
    tmp = HERE / "_ico_tmp"
    tmp.mkdir(exist_ok=True)
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    write_ico([(s, save_png(surf, s, tmp / f"{s}.png")) for s in ico_sizes],
              HERE / "icon.ico")
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()

    # macOS .icns 用の iconset（この後 iconutil -c icns assets/icon.iconset を実行）
    iconset = HERE / "icon.iconset"
    iconset.mkdir(exist_ok=True)
    for s in [16, 32, 128, 256, 512]:
        save_png(surf, s, iconset / f"icon_{s}x{s}.png")
        save_png(surf, s * 2, iconset / f"icon_{s}x{s}@2x.png")
    print("done")


if __name__ == "__main__":
    main()
