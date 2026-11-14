# Snake Game

A Snake game remake built with pygame, expanded with obstacles, field items, a shop, and permanent upgrades.

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

Click **START** on the title screen. Steer the snake and eat the purple orbs to grow longer.  
A golden bonus orb appears once in a while — grab it before it fades for 5× points.  
Hit a wall, your own body, or a brick and it's game over.  
Fill the entire board to trigger the PERFECT! clear.

A short tutorial walks you through everything on first launch, and you can reopen it any time from **? How to Play**. After an update, a What's New slideshow introduces the new features.

| Key | Action |
|-----|--------|
| `↑ ↓ ← →` or `W A S D` | Steer (up to 2 moves can be queued ahead) |
| `1` `2` `3` `4` or `J` `K` `L` `;` | Use the item in that slot of the bottom item bar |
| `R` | Retry (on the game-over screen) |
| `F` | Toggle fullscreen |
| `Q` | Quit |

**Control style** — In Settings you can switch between two control styles:

- **4-WAY** (default) — the snake turns to face the direction you press.
- **TURN L/R** — `←`/`A` turns 90° left and `→`/`D` turns 90° right, relative to the way the snake is heading. Up/down are ignored.

Difficulty and control style reset to NORMAL / 4-WAY each time the game starts.

---

## Difficulty

| | EASY | NORMAL | HARD | CLASSIC |
|-|------|--------|------|---------|
| Speed | Slow | Medium | Fast | Medium |
| Bricks | Few | Some | Many | None |
| Field items | ✓ | ✓ | ✓ | — |
| Item duration | Longer | Normal | Shorter | — |
| Points per orb | 1 | 2 | 4 | 2 |

CLASSIC is plain Snake: no bricks and no field items.

---

## Field items

These appear on the board from time to time. Just run into one to activate it.

- **Magnet** — greatly widens the orb pickup radius for a while
- **Shield** — smash through bricks for a while (each smashed brick scores more than an orb)
- **Flame** — fires fireballs straight ahead at regular intervals for a while; each one breaks the first brick it hits
- **Golden Orb** — rare, short-lived, worth 5× points

---

## Shop

Spend the points you earn in-game on items. New items unlock as your best score passes each threshold.

| Item | Effect |
|------|--------|
| **Triple Duration Potion** | Magnets and shields last 3× longer, including one already active |
| **Double Points Potion** | ×2 score multiplier for a while (the snake turns gold) |
| **Super Magnet** (pack of 3) | Instantly collects every orb on the board, with points and growth |
| **Bomb** (pack of 3) | Blows up every brick on the board and turns them into score |
| **Pocket Watch** | Slows down time itself — the snake, item effects, spawns, everything |

---

## Loadout

Open **LOADOUT** from the title or game-over screen.

- **Equip** — click an item in your inventory to equip it to one of the 4 slots of the bottom item bar (click again to unequip). Drag an equipped slot onto another to swap them, and tap an equipped slot to unequip it.
- **Upgrades** — buy permanent upgrades. **Point Boost** adds +1 to every point you earn, stacking with potions and bonus orbs. Each level costs more than the last.

---

## Players

Add, switch, and delete players from the Settings screen (the gear icon).  
High scores are tracked per player and per difficulty. Points, items, and upgrades also belong to each player.

---

## Under the hood

This is a fully open-source Python project. There is **no network access, no telemetry, and no external dependencies beyond pygame**. Here is a plain-language summary of what the code does.

**Dependencies**

| Library | Purpose |
|---------|---------|
| [pygame-ce](https://pyga.me/) | Window, rendering, input, clock |
| Python stdlib only (`json`, `os`, `sys`, `math`, `random`, `pathlib`, …) | Everything else |

**Save data**

Player profiles, high scores, wallet balance, item inventory, loadout, and upgrades are stored in a single `users.json` file in your OS app-data folder (listed above under Download). The file is plain JSON — you can open it in any text editor. Saves are written atomically (temp file → rename) so a crash mid-save cannot corrupt your data. If the file is unreadable for any reason, the game backs it up as `users.json.bak` and starts fresh.

Older save files are upgraded automatically when a newer version loads them. Going back to an older version after that is not supported.

**Crash log**

If the game crashes unexpectedly, a `crash.log` file is written to the same folder as `users.json`. It contains a Python traceback and the game version. Nothing is sent anywhere — the log is purely local.

**Code structure**

```
snakegame.py        Main loop — reads input, advances game state, draws each frame
game_state.py       Screen manager — routes between title, play, game over, shop, etc.
snake.py            Snake position history, grid-locked movement, collision checks
food.py             Orb spawning (avoids snake, bricks, other orbs) + golden bonus orb
obstacle.py         Brick obstacles — per-block lifetime, respawn, end-game fade-out
magnet.py           Magnet field item — spawn, pickup, pickup-radius boost timer
shield.py           Shield field item — spawn, pickup, brick smashing on collision
flame.py            Flame field item — spawn, pickup, fireballs that break bricks
items.py            Shop item effects (potions, Super Magnet, Bomb, Pocket Watch) + item bar
upgrades.py         Permanent upgrade catalog and pricing
score.py            Score counter, high-score display, PERFECT! clear animation
start_screen.py     Title screen
game_over_screen.py Game-over screen
shop_screen.py      Shop UI — item catalog, unlock thresholds, wallet spend
loadout_screen.py   Loadout UI — equip slots, inventory, upgrade purchases
settings_screen.py  Settings UI — difficulty, control style, players
register_screen.py  First-launch player registration
tutorial_screen.py  Tutorial slideshow (shared with the How to Play screen)
how_to_screen.py    How to Play screen
whatsnew.py         What's New slideshow shown after an update
button.py           Shared button widget
users.py            JSON load/save, per-player scores, wallet, inventory, loadout, upgrades
settings.py         Difficulty presets (speed, brick count, item flags, point values) + control styles
theme.py            Colors, fonts, coordinate helpers, app version
crashlog.py         Hooks sys.excepthook to append tracebacks to crash.log
assets/             App icons only (png / icns / ico) — no audio or data files
packaging/          PyInstaller spec for the macOS build
```
