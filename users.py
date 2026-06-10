import json
import os
import sys
from pathlib import Path
from settings import DIFFICULTY_ORDER

APP_NAME = "SnakeGame"


# 保存先フォルダ。開発時はこのファイルの隣、配布版(frozen)はOS標準のユーザーデータ領域
# （Windows: %APPDATA%\SnakeGame / macOS: ~/Library/Application Support/SnakeGame）。
# .app や .exe の中は書き込めないことがあるため、frozen時に相対パスは使わない。
def _data_dir():
    if getattr(sys, "frozen", False):
        if sys.platform.startswith("win"):
            return Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        return Path.home() / f".{APP_NAME.lower()}"
    return Path(__file__).resolve().parent


def _users_file():
    base = _data_dir()
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # 作れなくても起動は続ける（保存時にも握りつぶす）
    return base / "users.json"


USERS_FILE = _users_file()


# 保存データの数値は壊れている可能性がある（手で編集された等）。失敗したら既定値に落とす
def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ユーザー登録と、ユーザー×難易度ごとのハイスコアを管理する
class UserManager:
    def __init__(self):
        self.users = {}      # 名前 -> {難易度キー: ハイスコア}
        self.current = None  # 現在選択中のユーザー名
        # チュートリアルを見たか（ファイル全体で1つ。新規インストールは登録後に、
        # 旧バージョンからの更新者は初回起動時に1度だけチュートリアルが出る）
        self.tutorial_done = False
        self._load()
        # ユーザーが1人もいない（=初回起動）場合はここでは作らない。
        # GameState が登録画面（RegisterScreen）を出して最初のユーザーを作らせる。

    def _blank_scores(self):
        return {key: 0 for key in DIFFICULTY_ORDER}

    # 1ユーザー分の新スキーマ: {scores, wallet, inventory, seen_items}
    def _blank_record(self):
        return {"scores": self._blank_scores(), "wallet": 0, "inventory": {},
                "seen_items": []}

    # 読み込んだ1ユーザー分を新スキーマに正規化する。
    # 旧フラット形式（値が難易度→intの辞書）も読めるようにする（名簿を失わないため）。
    def _normalize(self, raw):
        rec = self._blank_record()
        if isinstance(raw, dict) and "scores" in raw:
            # 新スキーマ。値が数値でない壊れたデータは0として読む（起動を止めない）
            scores = raw.get("scores", {})
            if isinstance(scores, dict):
                rec["scores"].update({k: _to_int(v) for k, v in scores.items()})
            rec["wallet"] = _to_int(raw.get("wallet", 0))
            inventory = raw.get("inventory", {})
            if isinstance(inventory, dict):
                rec["inventory"] = {k: _to_int(v) for k, v in inventory.items()}
            seen = raw.get("seen_items", [])
            if isinstance(seen, list):
                rec["seen_items"] = [str(s) for s in seen]
        elif isinstance(raw, dict):
            # 旧フラット形式: {難易度: スコア}
            rec["scores"].update({k: _to_int(v) for k, v in raw.items()})
        return rec

    def _load(self):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("users.json: top level must be a dict")
            users = data.get("users", {})
            if not isinstance(users, dict):
                raise ValueError("users.json: 'users' must be a dict")
            self.users = {
                str(name): self._normalize(raw)
                for name, raw in users.items()
            }
            self.current = data.get("current")
            if self.current not in self.users:
                self.current = next(iter(self.users), None)
            # v1.1以前のファイルにはこのキーが無い → False（=初回起動時に1度見せる）
            self.tutorial_done = bool(data.get("tutorial_done", False))
        except FileNotFoundError:
            self.users = {}
            self.current = None
        except (OSError, ValueError, TypeError, AttributeError):
            # 壊れたファイルは .bak に退避してから初期化する
            # （次の save() で上書きして記録を完全に失わないため）
            self.users = {}
            self.current = None
            self._backup_corrupt()

    # 読めなかった users.json を users.json.bak へ退避する（失敗しても続行）
    def _backup_corrupt(self):
        try:
            os.replace(USERS_FILE, USERS_FILE.with_suffix(".json.bak"))
        except OSError:
            pass

    def names(self):
        return list(self.users.keys())

    def exists(self, name):
        return name in self.users

    # 新規登録（重複なら False を返して登録しない）
    def add_user(self, name):
        if name in self.users:
            return False
        self.users[name] = self._blank_record()
        self.current = name
        self.save()
        return True

    # ユーザー削除（最後の1人は消せない。消したのが現在ユーザーなら別の人へ切替）
    def delete_user(self, name):
        if name not in self.users or len(self.users) <= 1:
            return False
        del self.users[name]
        if self.current == name:
            self.current = next(iter(self.users))
        self.save()
        return True

    def set_current(self, name):
        if name in self.users:
            self.current = name
            self.save()

    def _record(self):
        return self.users.setdefault(self.current, self._blank_record())

    def high_score(self, difficulty):
        return self.users.get(self.current, {}).get("scores", {}).get(difficulty, 0)

    def update_high_score(self, difficulty, score):
        scores = self._record()["scores"]
        if score > scores.get(difficulty, 0):
            scores[difficulty] = score
            self.save()

    # 現在ユーザーの全難易度の最大ハイスコア（ショップのアイテム解放判定用）
    def best_high_score(self):
        scores = self.users.get(self.current, {}).get("scores", {})
        return max(scores.values(), default=0)

    # --- ウォレット（ユーザー単位で1つ累計のポイント残高）---
    @property
    def wallet(self):
        return self.users.get(self.current, {}).get("wallet", 0)

    def add_to_wallet(self, n):
        if n <= 0:
            return
        self._record()["wallet"] += n
        self.save()

    # 残高が足りれば消費して True。足りなければ False（残高は変えない）
    def spend(self, n):
        rec = self._record()
        if rec["wallet"] < n:
            return False
        rec["wallet"] -= n
        self.save()
        return True

    # --- 在庫（所持アイテム: item_key -> 個数）---
    def item_count(self, key):
        return self.users.get(self.current, {}).get("inventory", {}).get(key, 0)

    def add_item(self, key, n=1):
        inv = self._record()["inventory"]
        inv[key] = inv.get(key, 0) + n
        self.save()

    # チュートリアルを見終わった（SKIP含む）。以後は起動時に出さない
    def mark_tutorial_done(self):
        if not self.tutorial_done:
            self.tutorial_done = True
            self.save()

    # --- ショップで「開放」演出を見たポーションの記録（ユーザー単位）---
    def has_seen_item(self, key):
        return key in self.users.get(self.current, {}).get("seen_items", [])

    def mark_item_seen(self, key):
        seen = self._record().setdefault("seen_items", [])
        if key not in seen:
            seen.append(key)
            self.save()

    # 在庫が1個以上あれば1個消費して True。無ければ False
    def use_item(self, key):
        inv = self._record()["inventory"]
        if inv.get(key, 0) <= 0:
            return False
        inv[key] -= 1
        self.save()
        return True

    def save(self):
        # 一時ファイルに書き切ってから os.replace で置き換える（アトミック）。
        # 書き込み途中でクラッシュ・電源断しても users.json 本体は壊れない。
        # 保存できない環境（読み取り専用ディスク等）でもゲームは続行する。
        tmp = USERS_FILE.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"current": self.current, "tutorial_done": self.tutorial_done,
                           "users": self.users},
                          f, ensure_ascii=False, indent=2)
            os.replace(tmp, USERS_FILE)
        except OSError:
            pass
