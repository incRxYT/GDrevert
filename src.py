"""
GD Downgrader — Geometry Dash 2.2074 Downgrade Tool
Automates the Steam depot method for downgrading GD to 2.2074.
Author: incRX | Requires: Windows + Steam
"""

import os
import sys
import stat
import shutil
import winreg
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

# ─── Constants ────────────────────────────────────────────────────────────────

APP_ID       = "322170"
DEPOT_ID     = "322171"
MANIFEST_ID  = "7678373534998244044"
DEPOT_CMD    = f"download_depot {APP_ID} {DEPOT_ID} {MANIFEST_ID}"

GEODE_DLL      = "Geode.dll"
GEODE_FOLDER   = "geode"
GEODE_VERSION  = "v4.10.2"
# v4.10.2 is the final Geode release for GD 2.2074
GEODE_URL      = "https://github.com/geode-sdk/geode/releases/tag/v4.10.2"
GEODE_DL_WIN   = "https://github.com/geode-sdk/geode/releases/download/v4.10.2/geode-installer-win.exe"
ACF_FILE       = f"appmanifest_{APP_ID}.acf"

GD_EXE       = "GeometryDash.exe"
COCOS_DLL    = "libcocos2d.dll"

COLORS = {
    "bg":        "#0d0d0d",
    "panel":     "#141414",
    "border":    "#2a2a2a",
    "gold":      "#f5c842",
    "gold_dim":  "#a88520",
    "green":     "#4caf50",
    "red":       "#e05252",
    "blue":      "#5b9cf6",
    "text":      "#e8e8e8",
    "subtext":   "#888888",
    "input_bg":  "#1a1a1a",
}

FONT_TITLE  = ("Courier New", 22, "bold")
FONT_LABEL  = ("Courier New", 10)
FONT_MONO   = ("Courier New", 9)
FONT_BTN    = ("Courier New", 11, "bold")
FONT_STATUS = ("Courier New", 8)

# ─── Steam Helpers ────────────────────────────────────────────────────────────

def get_steam_path() -> Path | None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        value, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        p = Path(value)
        return p if p.exists() else None
    except Exception:
        return None


def get_source_path(steam: Path) -> Path:
    return steam / "steamapps" / "content" / f"app_{APP_ID}" / f"depot_{DEPOT_ID}"


def get_dest_path(steam: Path) -> Path:
    return steam / "steamapps" / "common" / "Geometry Dash"


def get_acf_path(steam: Path) -> Path:
    return steam / "steamapps" / ACF_FILE


def is_depot_ready(source: Path) -> bool:
    return source.exists() and any(source.iterdir())


def is_gd_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {GD_EXE}"],
            capture_output=True, text=True
        )
        return GD_EXE.lower() in result.stdout.lower()
    except Exception:
        return False


def get_geode_installed_version(dest: Path):
    """
    Try to read the installed Geode version from its on-disk metadata.
    Returns a bare version string like '4.10.2', or None if unreadable.
    """
    import json

    candidates = [
        dest / "geode" / "about.json",
        dest / "geode" / "config" / "geode.json",
        dest / "geode" / "geode.json",
        dest / "geode" / "resources" / "geode.loader" / "about.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key in ("version", "geode", "loader_version"):
                    if key in data:
                        ver = str(data[key]).lstrip("v")
                        if ver:
                            return ver
            except Exception:
                continue

    # Fallback: read DLL file version via Windows API
    dll_path = dest / GEODE_DLL
    if dll_path.exists():
        try:
            import ctypes
            size = ctypes.windll.version.GetFileVersionInfoSizeW(str(dll_path), None)
            if size:
                buf = ctypes.create_string_buffer(size)
                ctypes.windll.version.GetFileVersionInfoW(str(dll_path), 0, size, buf)
                verinfo = ctypes.c_void_p()
                verlen  = ctypes.c_uint()
                ctypes.windll.version.VerQueryValueW(
                    buf, "\\", ctypes.byref(verinfo), ctypes.byref(verlen)
                )
                class VS_FIXEDFILEINFO(ctypes.Structure):
                    _fields_ = [
                        ("dwSignature",        ctypes.c_uint32),
                        ("dwStrucVersion",     ctypes.c_uint32),
                        ("dwFileVersionMS",    ctypes.c_uint32),
                        ("dwFileVersionLS",    ctypes.c_uint32),
                        ("dwProductVersionMS", ctypes.c_uint32),
                        ("dwProductVersionLS", ctypes.c_uint32),
                        ("dwFileFlagsMask",    ctypes.c_uint32),
                        ("dwFileFlags",        ctypes.c_uint32),
                        ("dwFileOS",           ctypes.c_uint32),
                        ("dwFileType",         ctypes.c_uint32),
                        ("dwFileSubtype",      ctypes.c_uint32),
                        ("dwFileDateMS",       ctypes.c_uint32),
                        ("dwFileDateLS",       ctypes.c_uint32),
                    ]
                info = ctypes.cast(verinfo, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
                ms   = info.dwFileVersionMS
                ls   = info.dwFileVersionLS
                major = (ms >> 16) & 0xFFFF
                minor = ms & 0xFFFF
                patch = (ls >> 16) & 0xFFFF
                if major > 0:
                    return f"{major}.{minor}.{patch}"
        except Exception:
            pass

    return None


def check_geode(dest: Path):
    """
    Returns (is_correct_version: bool, status_message: str, installed_version: str|None).
    Correct means Geode is present AND exactly GEODE_VERSION (v4.10.2).
    """
    has_dll    = (dest / GEODE_DLL).exists()
    has_folder = (dest / GEODE_FOLDER).exists()

    if not has_dll and not has_folder:
        return False, "Not installed", None

    installed = get_geode_installed_version(dest)

    if installed is None:
        return False, "Installed (version unreadable - may be wrong!)", None

    target = GEODE_VERSION.lstrip("v")  # "4.10.2"

    if installed == target:
        return True, f"v{installed} (correct) ✓", installed

    return False, f"Wrong version: v{installed}  (need {GEODE_VERSION})", installed


def is_acf_readonly(acf: Path) -> bool:
    if not acf.exists():
        return False
    return not os.access(acf, os.W_OK)


# ─── Core Operations ──────────────────────────────────────────────────────────

def open_steam_console():
    os.startfile("steam://open/console")


def backup_files(dest: Path, log) -> bool:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = dest / f"_gd_backup_{ts}"
    backup_dir.mkdir(exist_ok=True)
    backed_up = []
    for fname in [GD_EXE, COCOS_DLL]:
        src = dest / fname
        if src.exists():
            shutil.copy2(src, backup_dir / fname)
            backed_up.append(fname)
    if backed_up:
        log(f"Backed up: {', '.join(backed_up)} → {backup_dir.name}")
    else:
        log("No existing files to back up.")
    return True


def sync_depot(source: Path, dest: Path, log, progress_cb=None) -> bool:
    files = list(source.rglob("*"))
    total = len([f for f in files if f.is_file()])
    done  = 0
    for item in files:
        rel = item.relative_to(source)
        target = dest / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            done += 1
            log(f"Copied: {rel}")
            if progress_cb:
                progress_cb(int(done / max(total, 1) * 100))
    return True


def lock_acf(acf: Path, log) -> bool:
    if not acf.exists():
        log(f"ACF not found: {acf}")
        return False
    current = stat.S_IMODE(os.stat(acf).st_mode)
    os.chmod(acf, current & ~stat.S_IWRITE)
    log(f"Locked (read-only): {acf.name}")
    return True


def unlock_acf(acf: Path, log) -> bool:
    if not acf.exists():
        log(f"ACF not found: {acf}")
        return False
    current = stat.S_IMODE(os.stat(acf).st_mode)
    os.chmod(acf, current | stat.S_IWRITE)
    log(f"Unlocked (writable): {acf.name}")
    return True


# ─── GUI ──────────────────────────────────────────────────────────────────────

class GDDowngrader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GD Downgrader  //  v2.2074")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])

        self._steam_path: Path | None = None
        self._source:     Path | None = None
        self._dest:       Path | None = None
        self._acf:        Path | None = None

        self._build_ui()
        self._refresh_state()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        C = COLORS

        # ── Title bar ──
        title_frame = tk.Frame(self, bg=C["bg"], pady=14)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame, text="◈  GD DOWNGRADER",
            font=FONT_TITLE, fg=C["gold"], bg=C["bg"]
        ).pack(side="left")

        tk.Label(
            title_frame, text="target: 2.2074",
            font=FONT_MONO, fg=C["subtext"], bg=C["bg"]
        ).pack(side="right", padx=4)

        # ── Separator ──
        tk.Frame(self, bg=C["gold"], height=1).pack(fill="x", padx=20)

        # ── Status panel ──
        status_outer = tk.Frame(self, bg=C["panel"], padx=16, pady=12)
        status_outer.pack(fill="x", padx=20, pady=(14, 0))

        self._status_rows: dict[str, tk.Label] = {}
        items = [
            ("steam",  "Steam Path"),
            ("depot",  "Depot Download"),
            ("gd",     "GD Running"),
            ("acf",    "Manifest Lock"),
            ("geode",  "Geode v4.10.2"),
        ]
        for key, label in items:
            row = tk.Frame(status_outer, bg=C["panel"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label:<18}", font=FONT_MONO,
                     fg=C["subtext"], bg=C["panel"]).pack(side="left")
            val = tk.Label(row, text="—", font=FONT_MONO,
                           fg=C["text"], bg=C["panel"])
            val.pack(side="left")
            self._status_rows[key] = val

        # ── Depot command copy box ──
        cmd_frame = tk.Frame(self, bg=C["panel"], padx=16, pady=10)
        cmd_frame.pack(fill="x", padx=20, pady=(10, 0))

        tk.Label(cmd_frame, text="Steam Console Command:", font=FONT_MONO,
                 fg=C["subtext"], bg=C["panel"]).pack(anchor="w")

        cmd_inner = tk.Frame(cmd_frame, bg=C["input_bg"], padx=8, pady=6,
                             highlightthickness=1, highlightbackground=C["border"])
        cmd_inner.pack(fill="x", pady=(4, 0))

        self._cmd_var = tk.StringVar(value=DEPOT_CMD)
        cmd_entry = tk.Entry(
            cmd_inner, textvariable=self._cmd_var,
            font=FONT_MONO, fg=C["gold"], bg=C["input_bg"],
            readonlybackground=C["input_bg"], relief="flat",
            state="readonly", width=56
        )
        cmd_entry.pack(side="left", fill="x", expand=True)

        tk.Button(
            cmd_inner, text="COPY", font=FONT_STATUS,
            fg=C["bg"], bg=C["gold"], relief="flat", cursor="hand2",
            command=self._copy_cmd, padx=6
        ).pack(side="right")

        # ── Progress ──
        prog_frame = tk.Frame(self, bg=C["bg"], padx=20, pady=8)
        prog_frame.pack(fill="x")

        self._progress = ttk.Progressbar(prog_frame, length=460, mode="determinate")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar",
                        troughcolor=C["panel"],
                        bordercolor=C["border"],
                        background=C["gold"],
                        lightcolor=C["gold"],
                        darkcolor=C["gold"])
        self._progress.pack(fill="x")

        # ── Log ──
        log_frame = tk.Frame(self, bg=C["panel"], padx=0, pady=0)
        log_frame.pack(fill="both", padx=20, pady=(0, 6))

        tk.Frame(log_frame, bg=C["border"], height=1).pack(fill="x")

        self._log_text = tk.Text(
            log_frame, height=8, font=FONT_STATUS,
            bg=C["panel"], fg=C["subtext"], relief="flat",
            state="disabled", wrap="word",
            insertbackground=C["text"], padx=10, pady=8
        )
        self._log_text.pack(fill="both")
        sb = tk.Scrollbar(log_frame, command=self._log_text.yview,
                          bg=C["border"], troughcolor=C["panel"])
        sb.pack(side="right", fill="y")
        self._log_text.configure(yscrollcommand=sb.set)

        # ── Buttons ──
        btn_frame = tk.Frame(self, bg=C["bg"], pady=12)
        btn_frame.pack(fill="x", padx=20)

        self._btn_console = self._make_btn(
            btn_frame, "① OPEN STEAM CONSOLE", self._do_open_console,
            C["blue"], C["bg"]
        )
        self._btn_console.pack(side="left", padx=(0, 6))

        self._btn_check = self._make_btn(
            btn_frame, "② CHECK READINESS", self._do_check,
            C["gold_dim"], C["bg"]
        )
        self._btn_check.pack(side="left", padx=6)

        self._btn_apply = self._make_btn(
            btn_frame, "③ APPLY DOWNGRADE", self._do_apply,
            C["gold"], C["bg"]
        )
        self._btn_apply.pack(side="left", padx=6)

        self._btn_revert = self._make_btn(
            btn_frame, "REVERT LOCK", self._do_revert,
            C["red"], C["bg"]
        )
        self._btn_revert.pack(side="right")

        # ── Footer ──
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", padx=20)
        tk.Label(
            self, text="depot 322171  //  manifest 7678373534998244044  //  incRX",
            font=FONT_STATUS, fg=C["border"], bg=C["bg"]
        ).pack(pady=6)

    def _make_btn(self, parent, text, cmd, bg, fg):
        return tk.Button(
            parent, text=text, command=cmd,
            font=FONT_BTN, fg=fg, bg=bg,
            activebackground=bg, activeforeground=fg,
            relief="flat", cursor="hand2", padx=12, pady=7
        )

    # ── State ─────────────────────────────────────────────────────────────────

    def _refresh_state(self):
        C = COLORS
        R = self._status_rows

        steam = get_steam_path()
        self._steam_path = steam

        if steam:
            self._source = get_source_path(steam)
            self._dest   = get_dest_path(steam)
            self._acf    = get_acf_path(steam)
            R["steam"].config(text=str(steam), fg=C["green"])
        else:
            self._source = self._dest = self._acf = None
            R["steam"].config(text="Not found", fg=C["red"])

        depot_ok = self._source and is_depot_ready(self._source)
        R["depot"].config(
            text="Ready ✓" if depot_ok else "Not downloaded yet",
            fg=C["green"] if depot_ok else C["red"]
        )

        gd_running = is_gd_running()
        R["gd"].config(
            text="RUNNING — close it first!" if gd_running else "Not running ✓",
            fg=C["red"] if gd_running else C["green"]
        )

        if self._acf:
            locked = is_acf_readonly(self._acf)
            R["acf"].config(
                text="Locked (read-only) ✓" if locked else "Unlocked (will auto-update!)",
                fg=C["green"] if locked else C["gold"]
            )
        else:
            R["acf"].config(text="ACF not found", fg=C["subtext"])

        if self._dest and self._dest.exists():
            geode_ok, geode_msg, _ = check_geode(self._dest)
            if geode_ok:
                color = C["green"]
            elif geode_msg.startswith("Wrong version"):
                color = C["red"]
            elif geode_msg == "Not installed":
                color = C["gold_dim"]
            else:
                color = C["red"]
            R["geode"].config(text=geode_msg, fg=color)
        else:
            R["geode"].config(text="GD not found", fg=C["subtext"])

    # ── Actions ───────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        def _write():
            self._log_text.configure(state="normal")
            self._log_text.insert("end", f"  {msg}\n")
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
        self.after(0, _write)

    def _set_progress(self, val: int):
        self.after(0, lambda: self._progress.configure(value=val))

    def _copy_cmd(self):
        self.clipboard_clear()
        self.clipboard_append(DEPOT_CMD)
        self._log("Copied depot command to clipboard.")

    def _do_open_console(self):
        self._log("Opening Steam console...")
        open_steam_console()
        self._log(f"Paste and run:  {DEPOT_CMD}")
        self._log("Wait for the download to complete, then click CHECK READINESS.")

    def _do_check(self):
        self._refresh_state()
        self._log("── Readiness check complete ──")
        if not self._steam_path:
            self._log("✗ Steam not found in registry.")
            return
        if not (self._source and is_depot_ready(self._source)):
            self._log("✗ Depot not ready. Run the console command first.")
            return
        if is_gd_running():
            self._log("✗ Close Geometry Dash before proceeding.")
            return
        self._log("✓ All checks passed. You can apply the downgrade.")

    def _do_apply(self):
        self._refresh_state()

        if not self._steam_path:
            messagebox.showerror("Error", "Steam not found.")
            return
        if not (self._source and is_depot_ready(self._source)):
            messagebox.showerror("Error", "Depot not ready.\nRun the Steam console command first.")
            return
        if is_gd_running():
            messagebox.showerror("Error", "Geometry Dash is running.\nClose it before downgrading.")
            return
        if not messagebox.askyesno(
            "Confirm Downgrade",
            "This will overwrite your current GD installation with v2.2074.\n\n"
            "A backup of GeometryDash.exe and libcocos2d.dll will be made.\n\n"
            "Continue?"
        ):
            return

        def _worker():
            try:
                self._log("── Starting downgrade ──")

                # Backup
                self._log("Backing up current files...")
                backup_files(self._dest, self._log)

                # Sync
                self._log(f"Copying depot files to GD folder...")
                sync_depot(self._source, self._dest, self._log, self._set_progress)

                # Lock ACF
                self._log("Locking appmanifest to prevent auto-updates...")
                lock_acf(self._acf, self._log)

                # Geode check
                geode_ok, geode_msg, geode_ver = check_geode(self._dest)
                if not geode_ok:
                    if geode_ver:
                        self._log(f"\u26a0 Wrong Geode version: v{geode_ver}")
                        self._log(f"  GD 2.2074 needs Geode {GEODE_VERSION}, not v{geode_ver}")
                        self._log(f"  -> Download: {GEODE_DL_WIN}")
                        def _ask_wrong(ver=geode_ver):
                            msg = (
                                f"You have Geode v{ver} installed which targets a different GD version.\n\n"
                                f"GD 2.2074 requires Geode {GEODE_VERSION} specifically.\n\n"
                                f"YES = download the correct installer ({GEODE_VERSION})\n"
                                f"NO  = open the GitHub releases page\n\n"
                                f"Uninstall your current Geode before installing {GEODE_VERSION}!"
                            )
                            choice = messagebox.askyesno(f"Wrong Geode Version: v{ver}", msg)
                            webbrowser.open(GEODE_DL_WIN if choice else GEODE_URL)
                        self.after(0, _ask_wrong)
                    else:
                        self._log(f"\u26a0 Geode not installed. You need {GEODE_VERSION} for GD 2.2074.")
                        self._log(f"  -> {GEODE_DL_WIN}")
                        def _ask_missing():
                            msg = (
                                f"Geode was not found in your GD folder.\n\n"
                                f"You need Geode {GEODE_VERSION} (last version for GD 2.2074).\n\n"
                                f"YES = open the direct Windows installer\n"
                                f"NO  = open the GitHub releases page\n\n"
                                f"Do NOT install a newer version - it wont work with 2.2074."
                            )
                            choice = messagebox.askyesno(f"Geode {GEODE_VERSION} Required", msg)
                            webbrowser.open(GEODE_DL_WIN if choice else GEODE_URL)
                        self.after(0, _ask_missing)

                self._set_progress(100)
                self._log("── Downgrade complete! GD is now v2.2074 ──")
                self.after(0, self._refresh_state)
                self.after(0, lambda: messagebox.showinfo(
                    "Done", "Downgrade applied!\n\nGeometry Dash is now v2.2074.\n"
                    "The manifest is locked — Steam won't auto-update it."
                ))
            except PermissionError as e:
                self._log(f"✗ Permission error: {e}")
                self.after(0, lambda: messagebox.showerror(
                    "Permission Error",
                    f"A file is in use or access was denied:\n{e}\n\nMake sure GD is closed."
                ))
            except Exception as e:
                self._log(f"✗ Error: {e}")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _do_revert(self):
        if not self._acf:
            messagebox.showerror("Error", "appmanifest not found.")
            return
        if not messagebox.askyesno(
            "Revert Manifest Lock",
            "This will make the manifest writable again.\n"
            "Steam will be able to update GD back to the latest version.\n\n"
            "Continue?"
        ):
            return
        unlock_acf(self._acf, self._log)
        self._refresh_state()
        self._log("Manifest unlocked. Steam can now update GD.")
        messagebox.showinfo("Reverted", "Manifest unlocked.\nSteam will update GD on next launch.")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform != "win32":
        print("This tool is Windows-only (Steam Registry + Windows file APIs).")
        sys.exit(1)
    app = GDDowngrader()
    app.mainloop()
