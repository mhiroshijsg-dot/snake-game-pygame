# Snake Game

A Snake game remake built with pygame, expanded with obstacles, items, and a shop.

---

## Download

Grab the zip for your OS from [Releases](../../releases).

- **macOS** — Unzip and drag to Applications. The app is not notarized, so macOS will warn you on first launch of each version:
  - **macOS 15 Sequoia and later**: open System Settings → Privacy & Security, scroll down and click **Open Anyway**.
  - **macOS 14 and earlier**: right-click the app → **Open**.
  - Or skip the dialog entirely by running `xattr -cr /Applications/SnakeGame.app` once in Terminal.
- **Windows** — Unzip and run `SnakeGame.exe`. If SmartScreen warns you, click *More info → Run anyway*.

Save data is stored in `~/Library/Application Support/SnakeGame/` (macOS) or `%APPDATA%\SnakeGame\` (Windows).

The window is freely resizable and `F` toggles fullscreen; on small displays it opens scaled down to fit. Gameplay is unaffected either way.

---

## How to play

Use the arrow keys to steer the snake and eat the purple orbs to grow longer.  
A golden bonus orb appears once in a while — grab it before it fades for 5x points.  
Hit a wall, your own body, or a brick obstacle and it's game over.  
Fill the entire board to trigger the PERFECT! clear.

A short tutorial walks you through everything on first launch.

| Key | Action |
|-----|--------|
| `↑ ↓ ← →` | Steer (up to 2 moves can be queued ahead) |
| `S` | Start |
| `R` | Retry |
| `1` `2` `3` `4` | Use item in slot |
| `F` | Toggle fullscreen |
| `Q` | Quit |

---

## Difficulty

| | EASY | NORMAL | HARD | CLASSIC |
|-|------|--------|------|---------|
| Speed | Slow | Medium | Fast | Medium |
| Obstacles | Few | Some | Many | None |
| Items | ✓ | ✓ | ✓ | — |
| Points | Low | Normal | High | Normal |

---

## Items

- **Magnet** — greatly widens the orb pickup radius for a short time
- **Shield** — smash through bricks for a short time (each smash scores more than an orb)
- **Golden Orb** — rare, short-lived, worth 5× points
- **Double Points Potion** — ×2 score multiplier for 10 s (snake turns gold)
- **Triple Duration Potion** — magnets and shields last 3× longer, including one already active

---

## Shop

Spend the points you earn in-game to buy potions.  
New items unlock once your high score passes the threshold.

---

## Players

Add and switch players from the Settings screen.  
High scores are tracked per player and per difficulty.

---

## Under the hood

This is a fully open-source Python project. There is **no network access, no telemetry, and no external dependencies beyond pygame**. Here is a plain-language summary of what the code does.

**Dependencies**

| Library | Purpose |
|---------|---------|
| [pygame-ce](https://pyga.me/) | Window, rendering, input, clock |
| Python stdlib only (`json`, `os`, `sys`, `math`, `random`) | Everything else |

**Save data**

Player profiles, high scores, wallet balance, and item inventory are stored in a single `users.json` file in your OS app-data folder (listed above under Download). The file is plain JSON — you can open it in any text editor. Saves are written atomically (temp file → rename) so a crash mid-save cannot corrupt your data. If the file is unreadable for any reason, the game backs it up as `users.json.bak` and starts fresh.

**Crash log**

If the game crashes unexpectedly, a `crash.log` file is written to the same folder as `users.json`. It contains a Python traceback and the game version. Nothing is sent anywhere — the log is purely local.

**Code structure**

```
snakegame.py      Main loop — reads input, advances game state, draws each frame
game_state.py     Screen manager — routes between title, play, game over, shop, etc.
snake.py          Snake position history, grid-locked movement, collision checks
food.py           Orb spawning (avoids snake, bricks, other orbs) + golden bonus orb
register_screen.py  First-launch player registration
tutorial_screen.py  Tutorial slideshow (shared with the How to Play screen)
obstacle.py       Brick obstacles — per-block lifetime, respawn, end-game fade-out
magnet.py         Magnet item logic — spawn pool, pickup, food-radius boost timer
shield.py         Shield item logic — spawn pool, pickup, block-destroy on collision
items.py          Potion effects (double points, triple duration) + HUD slot bar
score.py          Score counter, high-score display, PERFECT! clear animation
shop_screen.py    Shop UI — item catalog, unlock thresholds, wallet spend
users.py          JSON load/save, per-user scores, wallet, inventory
settings.py       Difficulty presets (speed, obstacle count, item flags, point values)
theme.py          All colors, fonts, coordinate helpers — one place to change the look
crashlog.py       Hooks sys.excepthook to append tracebacks to crash.log
assets/           App icons only (png / icns / ico) — no audio or data files
```
