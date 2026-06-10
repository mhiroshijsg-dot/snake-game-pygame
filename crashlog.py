# 予期しない例外をユーザーデータと同じフォルダの crash.log に記録する。
# 配布版（コンソールの無い .app / .exe）ではトレースバックがどこにも出ないため、
# 「いつ・どのバージョンで・何が起きたか」をファイルに残して原因調査できるようにする。
import sys
import traceback
from datetime import datetime

from users import USERS_FILE
import theme

LOG_FILE = USERS_FILE.with_name("crash.log")


class CrashLogger:
    # sys.excepthook として呼ばれる（未捕捉例外で必ず通る）
    def __call__(self, exc_type, exc, tb):
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} v{theme.APP_VERSION} ---\n")
                f.write("".join(traceback.format_exception(exc_type, exc, tb)))
                f.write("\n")
        except OSError:
            pass  # 書けない環境でも通常のエラー表示は行う
        sys.__excepthook__(exc_type, exc, tb)


def install():
    sys.excepthook = CrashLogger()
