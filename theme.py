# 配色・フォント・座標変換を一元管理する（白背景・白黒基調のモダンテーマ）
import os
import sys
from pathlib import Path
import pygame

APP_VERSION = "1.1"  # ウィンドウタイトル・タイトル画面・配布物の名前で使う


# 同梱リソース（assets/ 等）の絶対パス。PyInstallerのfrozen実行では展開先
# (_MEIPASS)から、開発時はこのファイルの隣から読む
def resource_path(relative):
    base = getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parent
    return str(Path(base) / relative)

# プレイ領域(600x600)の上に、スコア表示用のHUD帯を載せる。
# プレイ領域の論理座標(中心原点)は従来どおりで、描画はHUDぶん下にずれる。
PLAY_W = 600
PLAY_H = 600
HUD_HEIGHT = 48          # 上部スコア帯の高さ
HUD_BOTTOM_HEIGHT = 72   # 下部アイテムスロット帯の高さ（プレイ領域の外）
WIDTH = PLAY_W
HEIGHT = HUD_HEIGHT + PLAY_H + HUD_BOTTOM_HEIGHT

# 背景・テキスト（pygame.Color は hex 文字列をそのまま受け取れる）
BG = pygame.Color("#f4f6fb")        # うっすら青みのある明るい背景
TEXT = pygame.Color("#1b1f3b")      # 濃い藍色の主テキスト（緑のスネーク上でも読める）
TEXT_DIM = pygame.Color("#5b6478")  # 補助テキスト(青みグレー)

# ボタン（主操作=ビビッドな藍青、副操作=やや彩度のあるグレー）
PRIMARY = pygame.Color("#3b5bdb")
PRIMARY_HOVER = pygame.Color("#2f49b0")
SECONDARY = pygame.Color("#9aa3c0")
SECONDARY_HOVER = pygame.Color("#7d87a8")
BUTTON_TEXT = pygame.Color("#ffffff")
WARNING = pygame.Color("#e8453c")    # 警告メッセージ（赤）
GOLD = pygame.Color("#ffcf40")       # ハイスコア更新の演出色（金）

# HUD帯（上部のスコアバー）。濃い藍の帯に明るい文字
HUD_BG = pygame.Color("#1b1f3b")
HUD_TEXT = pygame.Color("#ffffff")

# ゲーム要素
SNAKE_COLOR = pygame.Color("#2fb344")   # 鮮やかな緑のスネーク
SNAKE_PATTERN = pygame.Color("#249838")  # 胴体の縞模様(やや濃い緑)
FOOD_COLOR = pygame.Color("#8b3ff0")     # 魔法オーブの本体（紫）
ORB_GLOW = pygame.Color("#b985ff")       # オーブの外側の淡い光
ORB_HIGHLIGHT = pygame.Color("#ede3ff")  # オーブのハイライト（光の点）
BRICK = pygame.Color("#b5512f")          # 障害物レンガの本体（テラコッタ）
BRICK_MORTAR = pygame.Color("#ecdcc4")   # レンガの目地（モルタル）
MAGNET_BODY = pygame.Color("#e2342f")    # マグネット本体（赤）
MAGNET_TIP = pygame.Color("#dfe3ea")     # マグネットの極（シルバー）
MAGNET_AURA = pygame.Color("#ff5a5a")    # 効果中に頭に出すオーラ
SHIELD_BODY = pygame.Color("#2f8fe2")    # シールド本体（青）
SHIELD_EMBLEM = pygame.Color("#dceeff")  # シールドの紋章（淡い水色）
SHIELD_AURA = pygame.Color("#4db5ff")    # 効果中に頭に出すバリア
POTION_GLASS = pygame.Color("#dfe3ea")   # ポーションのガラス瓶（淡いシルバー）
POTION_LIQUID = pygame.Color("#ffcf40")  # ポーションの液体（金＝ポイント二倍）
POTION_LIQUID2 = pygame.Color("#2fd0c0")  # ポーションの液体（青緑＝効果時間3倍）
POTION_CORK = pygame.Color("#b5723f")    # ポーションの栓（コルク茶）
SNAKE_BOOST = pygame.Color("#ffcf40")    # ポイント二倍中のボディ色（金）
SNAKE_BOOST_PATTERN = pygame.Color("#e0a81f")  # 同・縞模様（やや濃い金）

# フォント定義（名前, サイズ, スタイル）。実体は font() で生成する。
# 名前はカンミ区切りで複数指定でき、見つかった順に使われる（macOSのモダンなサンセリフ）
_FAMILY = "Avenir Next,Futura,Helvetica Neue"
FONT_TITLE = (_FAMILY, 48, "bold")
FONT_BIG = (_FAMILY, 42, "bold")
FONT_BUTTON = (_FAMILY, 18, "bold")
FONT_SCORE = (_FAMILY, 16, "normal")

# 日本語を含む名前用フォント。SysFontはグリフ単位のフォールバックをしないので、
# 日本語グリフを持つ実在フォントを直接ロードする（family名 "__JP__" を font() で特別扱い）。
FONT_NAME = ("__JP__", 18, "bold")          # 名前ボタン/ラベル相当
FONT_NAME_SMALL = ("__JP__", 16, "normal")  # HUD/スコア相当
# 候補を上から試し、日本語グリフを持つ実在フォントを選ぶ。
# macOS/Windows/Linux の代表的な日本語フォント名を並べ、見つからなければ下の
# ファイルパス候補も見る。配布時に同梱フォントを使う場合は SNAKEGAME_JP_FONT に指定する。
_JP_CANDIDATES = [
    "hiraginosans", "hiraginokakugothicpro", "hiraginokakugothicpron",
    "applesdgothicneo", "arialunicode",
    "yugothic", "yugothicui", "meiryo", "msgothic", "mspgothic",
    "notosanscjkjp", "notosansjp", "ipagothic", "ipaexgothic",
]
_JP_FONT_FILES = {
    "darwin": [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
        "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ],
    "win32": [
        "meiryo.ttc", "YuGothR.ttc", "YuGothM.ttc", "msgothic.ttc",
        "YuGothB.ttc", "meiryob.ttc",
    ],
    "linux": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf",
    ],
}
_jp_path = None


# プレイ領域の論理座標(中心原点・上が+y) ⇔ pygame画面座標(左上原点・下が+y)。
# プレイ領域はHUD帯(HUD_HEIGHT)のぶん下に置かれる。
def to_screen(x, y):
    return (PLAY_W / 2 + x, HUD_HEIGHT + PLAY_H / 2 - y)


def to_world(sx, sy):
    return (sx - PLAY_W / 2, HUD_HEIGHT + PLAY_H / 2 - sy)


# フォント実体をキャッシュして返す（pygame.font.init 後に呼ぶこと）
_font_cache = {}


# 日本語グリフを持つフォントかを確認する
def _supports_japanese(path):
    try:
        return pygame.font.Font(path, 16).metrics("あ")[0] is not None
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _windows_font_path(filename):
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if not windir:
        return None
    return str(Path(windir) / "Fonts" / filename)


def _iter_jp_file_candidates():
    env_path = os.environ.get("SNAKEGAME_JP_FONT")
    if env_path:
        yield env_path

    platform_key = "darwin" if sys.platform == "darwin" else "win32" if sys.platform.startswith("win") else "linux"
    for candidate in _JP_FONT_FILES.get(platform_key, []):
        if platform_key == "win32" and not os.path.isabs(candidate):
            candidate = _windows_font_path(candidate)
        if candidate:
            yield candidate


# 日本語グリフを持つフォントのパスを解決する（初回のみ）
def _resolve_jp():
    global _jp_path
    if _jp_path is None:
        for name in _JP_CANDIDATES:
            path = pygame.font.match_font(name)
            if path and _supports_japanese(path):
                _jp_path = path
                break
        if _jp_path is None:
            for path in _iter_jp_file_candidates():
                if os.path.exists(path) and _supports_japanese(path):
                    _jp_path = path
                    break
        if _jp_path is None:  # 最後の手段（見つからなければデフォルト）
            _jp_path = pygame.font.match_font("arialunicode") or ""
    return _jp_path


def font(spec):
    if spec not in _font_cache:
        name, size, style = spec
        try:
            if name == "__JP__":
                f = pygame.font.Font(_resolve_jp() or None, size)
                f.set_bold(style == "bold")
            else:
                f = pygame.font.SysFont(name, size, bold=(style == "bold"))
        except (OSError, ValueError, RuntimeError, pygame.error):
            # フォントが見つからない/読めない環境でも落とさず既定フォントで描く
            f = pygame.font.Font(None, size)
            f.set_bold(style == "bold")
        _font_cache[spec] = f
    return _font_cache[spec]


# 世界座標(x, y)を中心にテキストを描く（turtleのalign="center"相当）
def draw_text(surface, text, x, y, color, spec):
    label = font(spec).render(text, True, color)
    rect = label.get_rect(center=to_screen(x, y))
    surface.blit(label, rect)


# 画面の絶対座標(sx, sy)を中心にテキストを描く（HUDなど領域外用）
def draw_text_screen(surface, text, sx, sy, color, spec):
    label = font(spec).render(text, True, color)
    rect = label.get_rect(center=(sx, sy))
    surface.blit(label, rect)
