# 難易度ごとの設定値をまとめて持つ
# 障害物やアイテムなど将来の項目はここにフィールドを足すだけで拡張できる
class Difficulty:
    def __init__(self, name, speed, obstacle_count, has_magnet=True, has_shield=True,
                 item_duration_scale=1.0, orb_points=1, brick_points=1):
        self.name = name
        self.speed = speed                  # スネークのスピード(px/秒)
        self.obstacle_count = obstacle_count  # レンガ障害物の数
        self.has_magnet = has_magnet        # マグネットアイテムを出すか
        self.has_shield = has_shield        # シールドアイテムを出すか
        self.item_duration_scale = item_duration_scale  # アイテム効果時間の倍率(EASY長/HARD短)
        self.orb_points = orb_points        # オーブ1個で得る点数
        self.brick_points = brick_points    # ブロック1個破壊で得る点数（CLASSICは障害物なしで未使用）
        # 例: 将来ここに item_rate などを追加していく
        # （foodの当たり判定は格子化により難易度非依存になったので持たない）


# 難易度の定義。CLASSIC は障害物もマグネットも無し（純粋なスネーク）、速度300。
# 配点: 難しいほど高得点（orb/brick）。CLASSIC はブロックが無いので brick=0。
DIFFICULTIES = {
    "EASY":    Difficulty("EASY", speed=100, obstacle_count=5, item_duration_scale=1.5,
                          orb_points=1, brick_points=1),
    "NORMAL":  Difficulty("NORMAL", speed=200, obstacle_count=10, item_duration_scale=1.0,
                          orb_points=2, brick_points=3),
    "HARD":    Difficulty("HARD", speed=400, obstacle_count=18, item_duration_scale=0.6,
                          orb_points=4, brick_points=6),
    "CLASSIC": Difficulty("CLASSIC", speed=230, obstacle_count=0, has_magnet=False, has_shield=False,
                          orb_points=2, brick_points=0),
}

# 設定画面に並べる順番
DIFFICULTY_ORDER = ["EASY", "NORMAL", "HARD", "CLASSIC"]


# 現在の設定状態を保持する
class Settings:
    def __init__(self):
        self.difficulty_key = "NORMAL"

    @property
    def difficulty(self):
        return DIFFICULTIES[self.difficulty_key]

    @property
    def speed(self):
        return self.difficulty.speed

    def set_difficulty(self, key):
        self.difficulty_key = key
