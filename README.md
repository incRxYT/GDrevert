## GDrevert

> Automates the Steam depot method for downgrading Geometry Dash to **v2.2074** — with ACF locking, backups, and Geode detection.

---

## What it does

gdrevert handles every step of the [Steam Guide downgrade method](https://steamcommunity.com/sharedfiles/filedetails/?id=...) so you don't have to do it manually:
> Warning This Will Break Geode If You Do Not Have A Older Version Of Geode!

1. Opens the Steam console and gives you the exact depot command to paste
2. Detects your Steam installation via the Windows registry (works on any drive)
3. Backs up your current `GeometryDash.exe` and `libcocos2d.dll`
4. Copies all v2.2074 depot files into your GD folder
5. Locks `appmanifest_322170.acf` as read-only so Steam can't auto-update GD back
6. Checks for Geode and opens the installer if it's missing

A **Revert** button is included to unlock the manifest whenever you want to update GD again.

---

## Requirements

- **Windows** (uses the Windows registry and `winreg`)
- **Python 3.10+**
- **Steam** installed with Geometry Dash owned
- No external pip packages — stdlib only

---

## Usage

### 1. Clone and run

```bash
git clone https://github.com/incRxYT/gdrevert.git
cd gdrevert
python gd_downgrader.py
```
## or download from releases

### 2. Open the Steam console

Click **① OPEN STEAM CONSOLE** in the tool. This fires `steam://open/console`.

### 3. Run the depot command

In the Steam console, paste and run:

```
download_depot 322170 322171 7678373534998244044
```

Wait for the download to finish. Steam will print a path like:
`Depot download complete : C:\...\steamapps\content\app_322170\depot_322171`

### 4. Check readiness

Click **② CHECK READINESS**. The tool will verify:
- Steam path found in registry
- Depot files downloaded
- Geometry Dash is not running
- Manifest lock status
- Geode presence

### 5. Apply the downgrade

Click **③ APPLY DOWNGRADE** and confirm. The tool will back up your files, copy the depot, and lock the manifest.

---

## Features

| Feature | Details |
|---|---|
| Registry-based Steam detection | Works on `C:`, `D:`, `E:`, any drive |
| Timestamped backups | Saves `GeometryDash.exe` + `libcocos2d.dll` before overwriting |
| ACF lock | Sets `appmanifest_322170.acf` to read-only — prevents auto-updates |
| GD running check | Warns you before touching any files |
| Geode detection | Checks for `Geode.dll` or the `geode/` folder; opens installer if missing |
| Revert button | Unlocks the manifest so you can update GD normally |
| Progress bar + live log | See exactly what's being copied |

---

## Why v2.2074 specifically

Manifest ID `7678373534998244044` maps to GD v2.2074 — the last version fully compatible with the current Geode mod ecosystem. Using the manifest ID guarantees you get exactly that build every time regardless of what Steam has cached.

---

## Geode Compatibility

gdrevert targets the Geode 2.2074 modding environment. If you don't have Geode installed after downgrading, the tool will attempt to redircet to the installer at [geode-sdk.org/install](https://geode-sdk.org/install).

---

## Reverting (re-enabling updates)

Click **REVERT LOCK** at any time. This removes the read-only attribute from the manifest, allowing Steam to update GD back to the latest version on its next launch.

---

## Disclaimer

This tool uses the Steam depot download system for a game you own. It does not distribute or redistribute any game files. Use at your own risk — always keep your Geode mod backups before switching GD versions.

---

## License

The Unlicense
