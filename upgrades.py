# 恒常強化（アップグレード）のカタログ。ショップの消耗アイテムと違い、買うと
# ユーザーに永続的なレベルが積まれる（users.json の "upgrades": {key: level}）。
# レベル式・価格高騰: 次のレベルの価格 = base_price + price_step * 現在レベル。
# max_level を超えると購入不可（None なら上限なし）。新しい強化はここに1行足す。
UPGRADES = [
    {
        "key": "point_bonus",
        "name": "Point Boost",
        "base_price": 1000,
        "price_step": 1000,   # 1000 → 2000 → 3000 … と高騰
        "max_level": None,
        # desc は {lvl} を現在レベルで差し替えて表示する
        "desc": ["Permanently adds +1 to every point you earn,",
                 "stacking with potions and bonus orbs.",
                 "Current bonus: +{lvl} per point gain."],
    },
]


# key からカタログ定義を引く（無ければ None）
def find_upgrade(key):
    for up in UPGRADES:
        if up["key"] == key:
            return up
    return None


# 次に買うレベル（現在レベル+1）の価格。max_level 到達済みなら None。
def next_price(upgrade, level):
    max_level = upgrade.get("max_level")
    if max_level is not None and level >= max_level:
        return None
    return upgrade["base_price"] + upgrade["price_step"] * level
