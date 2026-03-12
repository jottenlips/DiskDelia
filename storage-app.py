#!/usr/bin/env python3
"""
DiskDelia — 90s Cyberdelia-themed macOS Storage Analyzer
"Hack the Planet... starting with your hard drive."
"""

import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

# ── Programming-related patterns ──────────────────────────────────────────────

PROGRAMMING_DIRS = {
    "node_modules":        ("Node.js dependencies", "rm -rf node_modules"),
    ".npm":                ("npm cache", "npm cache clean --force"),
    ".yarn":               ("Yarn cache", "yarn cache clean"),
    ".pnpm-store":         ("pnpm cache", "pnpm store prune"),
    "venv":                ("Python virtualenv", "Delete & recreate: python -m venv venv"),
    ".venv":               ("Python virtualenv", "Delete & recreate: python -m venv .venv"),
    "__pycache__":         ("Python bytecode cache", "find . -type d -name __pycache__ -exec rm -rf {} +"),
    ".tox":                ("Python tox envs", "rm -rf .tox"),
    ".mypy_cache":         ("mypy cache", "rm -rf .mypy_cache"),
    ".pytest_cache":       ("pytest cache", "rm -rf .pytest_cache"),
    "site-packages":       ("Python packages", "Part of a virtualenv or system Python"),
    ".cargo":              ("Rust cargo cache", "cargo cache --autoclean"),
    "target":              ("Rust/Java build output", "cargo clean / mvn clean"),
    ".rustup":             ("Rust toolchain", "rustup self uninstall"),
    ".gradle":             ("Gradle cache", "rm -rf ~/.gradle/caches"),
    ".m2":                 ("Maven cache", "rm -rf ~/.m2/repository"),
    "build":               ("Build output", "Project build artifacts"),
    "dist":                ("Dist output", "Distribution build output"),
    ".next":               ("Next.js cache", "rm -rf .next"),
    ".nuxt":               ("Nuxt.js cache", "rm -rf .nuxt"),
    ".cache":              ("General cache", "Various tool caches"),
    "Pods":                ("CocoaPods", "pod deintegrate && pod install"),
    "DerivedData":         ("Xcode build data", "rm -rf ~/Library/Developer/Xcode/DerivedData"),
    ".cocoapods":          ("CocoaPods cache", "pod cache clean --all"),
    "vendor":              ("Vendored deps", "Bundler/Composer/Go vendor"),
    ".bundle":             ("Ruby bundler", "bundle clean"),
    ".gem":                ("Ruby gems", "gem cleanup"),
    ".rbenv":              ("Ruby versions", "rbenv versions — remove unused"),
    ".pyenv":              ("Python versions", "pyenv versions — remove unused"),
    ".nvm":                ("Node versions", "nvm ls — remove unused"),
    ".sdkman":             ("SDK manager", "sdk flush"),
    ".conda":              ("Conda envs", "conda clean --all"),
    ".local":              ("Local installs", "pip/pipx installed packages"),
    "go":                  ("Go workspace", "go clean -cache -modcache"),
    ".docker":             ("Docker data", "docker system prune -a"),
    ".vagrant":            ("Vagrant VMs", "vagrant destroy"),
    "anaconda3":           ("Anaconda", "Large Python distro (~5 GB)"),
    "miniconda3":          ("Miniconda", "Conda Python distribution"),
    ".julia":              ("Julia packages", "Julia package cache"),
    ".ghcup":              ("Haskell toolchain", "ghcup nuke"),
    ".stack":              ("Haskell Stack", "stack clean"),
    ".opam":               ("OCaml packages", "opam clean"),
    ".pub-cache":          ("Dart/Flutter cache", "flutter pub cache clean"),
    ".flutter":            ("Flutter SDK", "Flutter framework files"),
    ".Trash":              ("Trash", "Empty from Finder or: rm -rf ~/.Trash/*"),
}

SYSTEM_DATA_PATHS = {
    "~/Library/Caches":                    "App caches (browser/Xcode/Spotify)",
    "~/Library/Application Support":       "App data — check for removed apps",
    "~/Library/Logs":                      "System & app logs",
    "~/Library/Containers":                "Sandboxed app data (Messages etc)",
    "~/Library/Group Containers":          "Shared app group data",
    "~/Library/Mail":                      "Mail.app local storage",
    "~/Library/Messages":                  "iMessage attachments & history",
    "~/Library/Developer/Xcode/DerivedData": "Xcode build cache (often 10+ GB)",
    "~/Library/Developer/Xcode/Archives":  "Xcode archived builds",
    "~/Library/Developer/Xcode/iOS DeviceSupport": "iOS device symbols",
    "~/Library/Developer/CoreSimulator":   "iOS Simulator data",
    "/Library/Caches":                     "System-level caches",
    "/private/var/folders":                "Temp files & per-user caches",
    "/private/var/db/diagnostics":         "System diagnostic logs",
    "/private/var/log":                    "System logs",
    "~/Library/Mobile Documents":          "iCloud Drive local cache",
    "~/Library/Application Support/MobileSync/Backup": "iOS device backups (10-50+ GB)",
    "~/.docker":                           "Docker images/containers/volumes",
    "~/Library/Application Support/Docker": "Docker Desktop data",
}

# ── 90s Cyberdelia Color Palette ──────────────────────────────────────────────
# Inspired by the movie Hackers (1995) and 90s hacker culture

C = {
    "bg":           "#0A0A1A",      # deep dark blue-black
    "bg2":          "#0F1128",      # slightly lighter panel
    "panel":        "#141433",      # card/panel background
    "border":       "#2A2A5A",      # subtle borders
    "fg":           "#00FF88",      # classic green terminal text
    "fg_dim":       "#007744",      # dimmed green
    "cyan":         "#00FFFF",      # cyan — the iconic hacker color
    "cyan_dim":     "#008888",
    "magenta":      "#FF00FF",      # neon magenta
    "magenta_dim":  "#880088",
    "yellow":       "#FFFF00",      # neon yellow
    "yellow_dim":   "#888800",
    "red":          "#FF3366",      # hot pink/red
    "orange":       "#FF8800",      # amber
    "blue":         "#4488FF",      # electric blue
    "white":        "#EEEEFF",      # slightly blue white
    "grid":         "#1A1A3A",      # grid lines
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_size(nbytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            if unit in ("B", "KB"):
                return f"{nbytes:,.0f} {unit}"
            return f"{nbytes:,.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:,.1f} PB"


def dir_size_fast(path):
    try:
        result = subprocess.run(
            ["du", "-sk", path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.split()[0]) * 1024
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    return 0


# ── Floppy Disk — 90s neon style ─────────────────────────────────────────────

def draw_floppy(canvas, x, y, size=64):
    s = size
    pad = 3
    # Outer glow effect
    for i in range(3, 0, -1):
        alpha_color = C["cyan_dim"] if i > 1 else C["cyan"]
        canvas.create_rectangle(x + pad - i, y + pad - i, x + s - pad + i, y + s - pad + i,
                                outline=alpha_color, width=1)
    # Main body
    canvas.create_rectangle(x + pad, y + pad, x + s - pad, y + s - pad,
                            fill=C["panel"], outline=C["cyan"], width=2)
    # Metal slider (top)
    sw, sh = s * 0.45, s * 0.20
    sx = x + (s - sw) / 2
    sy = y + pad + 2
    canvas.create_rectangle(sx, sy, sx + sw, sy + sh,
                            fill=C["bg2"], outline=C["magenta"], width=1)
    nw = s * 0.10
    canvas.create_rectangle(sx + sw/2 - nw/2, sy, sx + sw/2 + nw/2, sy + sh,
                            fill=C["magenta_dim"], outline=C["magenta"], width=1)
    # Label area (bottom) — with scan lines
    lw, lh = s * 0.7, s * 0.30
    lx = x + (s - lw) / 2
    ly = y + s - pad - lh - 2
    canvas.create_rectangle(lx, ly, lx + lw, ly + lh,
                            fill=C["bg"], outline=C["fg_dim"], width=1)
    for i in range(4):
        liney = ly + 4 + i * (lh / 5)
        canvas.create_line(lx + 4, liney, lx + lw - 4, liney, fill=C["fg_dim"])
    # Corner notch
    canvas.create_rectangle(x + pad, y + pad, x + pad + 6, y + pad + 6,
                            fill=C["yellow"], outline=C["yellow_dim"])


# ── Main App ──────────────────────────────────────────────────────────────────

class StorageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DiskDelia v1.0")
        self.root.geometry("900x700")
        self.root.configure(bg=C["bg"])
        self.root.minsize(750, 550)

        self.scanning = False
        self.items = []
        self.path_history = []

        self._build_ui()
        self._animate_title()

    def _animate_title(self):
        """Cycle the subtitle text with a blinking cursor."""
        if not hasattr(self, '_anim_tick'):
            self._anim_tick = 0
        self._anim_tick += 1
        cursor = "█" if self._anim_tick % 2 == 0 else " "
        if not self.scanning:
            self.subtitle_label.configure(text=f"hack the planet... starting with your hard drive {cursor}")
        self.root.after(600, self._animate_title)

    def _build_ui(self):
        bg = C["bg"]
        fg = C["fg"]
        cyan = C["cyan"]
        panel = C["panel"]

        # ── Header ────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=bg)
        header.pack(fill="x", padx=20, pady=(12, 4))

        self.floppy_canvas = tk.Canvas(header, width=64, height=64,
                                       bg=bg, highlightthickness=0)
        self.floppy_canvas.pack(side="left", padx=(0, 14))
        draw_floppy(self.floppy_canvas, 0, 0, 64)

        title_frame = tk.Frame(header, bg=bg)
        title_frame.pack(side="left", fill="y")
        tk.Label(title_frame, text="D I S K D E L I A", font=("Courier", 24, "bold"),
                 bg=bg, fg=cyan).pack(anchor="w")
        self.subtitle_label = tk.Label(title_frame,
                 text="hack the planet... starting with your hard drive █",
                 font=("Courier", 11), bg=bg, fg=C["fg_dim"])
        self.subtitle_label.pack(anchor="w")

        # ── Decorative scan line ──────────────────────────────────────────
        scan_line = tk.Canvas(self.root, height=2, bg=bg, highlightthickness=0)
        scan_line.pack(fill="x", padx=20, pady=(2, 6))
        scan_line.create_line(0, 1, 900, 1, fill=C["cyan_dim"], dash=(4, 4))

        # ── Controls ──────────────────────────────────────────────────────
        ctrl = tk.Frame(self.root, bg=bg)
        ctrl.pack(fill="x", padx=20, pady=(4, 8))

        tk.Label(ctrl, text="TARGET>", font=("Courier", 12, "bold"),
                 bg=bg, fg=C["magenta"]).pack(side="left")
        self.path_var = tk.StringVar(value=os.path.expanduser("~"))
        path_entry = tk.Entry(ctrl, textvariable=self.path_var, width=32,
                              font=("Courier", 12), bg=C["bg2"], fg=fg,
                              insertbackground=fg, relief="flat", bd=4,
                              selectbackground=C["cyan_dim"], selectforeground=C["white"])
        path_entry.pack(side="left", padx=(6, 10))

        tk.Label(ctrl, text="MIN>", font=("Courier", 12, "bold"),
                 bg=bg, fg=C["magenta"]).pack(side="left")
        self.min_mb_var = tk.StringVar(value="100")
        mb_entry = tk.Entry(ctrl, textvariable=self.min_mb_var, width=5,
                            font=("Courier", 12), bg=C["bg2"], fg=fg,
                            insertbackground=fg, relief="flat", bd=4,
                            selectbackground=C["cyan_dim"])
        mb_entry.pack(side="left", padx=(6, 4))
        tk.Label(ctrl, text="MB", font=("Courier", 11),
                 bg=bg, fg=C["fg_dim"]).pack(side="left", padx=(0, 10))

        self.back_btn = tk.Button(ctrl, text="◄ BACK", font=("Courier", 11, "bold"),
                                   bg="#FFFFFF", fg="#000000", relief="flat", bd=0,
                                   activebackground=C["cyan"], activeforeground="#000000",
                                   disabledforeground="#000000",
                                   cursor="hand2", command=self._go_back, state="disabled")
        self.back_btn.pack(side="left", padx=3)

        self.scan_btn = tk.Button(ctrl, text=" ► SCAN ", font=("Courier", 13, "bold"),
                                  bg=C["magenta"], fg=C["bg"], relief="flat", bd=0,
                                  activebackground=C["yellow"], activeforeground=C["bg"],
                                  cursor="hand2", command=self._start_scan)
        self.scan_btn.pack(side="left", padx=6)

        # ── Status bar ────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="[READY] Awaiting scan command...")
        tk.Label(self.root, textvariable=self.status_var, font=("Courier", 10),
                 bg=bg, fg=C["yellow_dim"], anchor="w").pack(fill="x", padx=24, pady=(0, 4))

        # ── Results tree ──────────────────────────────────────────────────
        tree_frame = tk.Frame(self.root, bg=C["border"], bd=1, relief="solid")
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Cyber.Treeview",
                        background=C["bg2"], foreground=fg, fieldbackground=C["bg2"],
                        font=("Courier", 11), rowheight=26, borderwidth=0)
        style.configure("Cyber.Treeview.Heading",
                        background=C["panel"], foreground=cyan,
                        font=("Courier", 11, "bold"), borderwidth=0, relief="flat")
        style.map("Cyber.Treeview",
                  background=[("selected", C["border"])],
                  foreground=[("selected", C["yellow"])])
        cols = ("size", "type", "path")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="Cyber.Treeview", selectmode="browse")
        self.tree.heading("size", text="[ SIZE ]", anchor="e")
        self.tree.heading("type", text="[ TYPE ]")
        self.tree.heading("path", text="[ PATH ]")

        self.tree.column("size", width=110, anchor="e", stretch=False)
        self.tree.column("type", width=170, stretch=False)
        self.tree.column("path", width=550, stretch=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        # ── Action buttons bar (ABOVE detail, never covered) ─────────────
        action_bar = tk.Frame(self.root, bg=bg)
        action_bar.pack(fill="x", padx=20, pady=(4, 2))

        btn_style = {"font": ("Courier", 11, "bold"), "relief": "flat", "bd": 0,
                     "cursor": "hand2", "padx": 10, "pady": 3}

        tk.Button(action_bar, text="OPEN", bg="#FFFFFF", fg="#000000",
                  activebackground=C["cyan"], activeforeground="#000000",
                  command=self._open_selected, **btn_style).pack(side="left", padx=3)

        tk.Button(action_bar, text="OPEN PARENT", bg="#FFFFFF", fg="#000000",
                  activebackground=C["cyan"], activeforeground="#000000",
                  command=self._open_parent, **btn_style).pack(side="left", padx=3)

        tk.Button(action_bar, text="COPY PATH", bg="#FFFFFF", fg="#000000",
                  activebackground=C["cyan"], activeforeground="#000000",
                  command=self._copy_path, **btn_style).pack(side="left", padx=3)

        tk.Button(action_bar, text="SCAN INTO ►", bg="#FFFFFF", fg="#000000",
                  activebackground=C["cyan"], activeforeground="#000000",
                  command=self._drill_into, **btn_style).pack(side="left", padx=3)

        # ── Detail panel (below buttons, fixed height) ────────────────────
        detail_outer = tk.Frame(self.root, bg=C["border"], bd=1, relief="solid")
        detail_outer.pack(fill="x", padx=20, pady=(2, 4))

        self.detail_var = tk.StringVar(value="// select a target to inspect")
        self.detail_label = tk.Label(detail_outer, textvariable=self.detail_var,
                                     font=("Courier", 10), bg=C["bg2"], fg=C["cyan"],
                                     anchor="w", justify="left", height=2)
        self.detail_label.pack(fill="x", ipady=4, ipadx=8)

        # ── Summary bar ──────────────────────────────────────────────────
        self.summary_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.summary_var,
                 font=("Courier", 10, "bold"), bg=bg, fg=C["cyan"],
                 anchor="w").pack(fill="x", padx=24, pady=(0, 8))

    # ── Scanning ──────────────────────────────────────────────────────────

    def _start_scan(self):
        if self.scanning:
            return
        self.scanning = True
        self.scan_btn.configure(state="disabled", text=" ■ SCANNING ")
        self.subtitle_label.configure(text="scanning... do not disconnect from the Gibson...", fg=C["yellow"])
        self.tree.delete(*self.tree.get_children())
        self.items = []
        self.detail_var.set("")
        self.summary_var.set("")

        scan_path = self.path_var.get().strip()
        try:
            min_mb = int(self.min_mb_var.get())
        except ValueError:
            min_mb = 100

        threading.Thread(target=self._scan_worker, args=(scan_path, min_mb),
                         daemon=True).start()

    def _scan_worker(self, root_path, min_mb):
        min_bytes = min_mb * 1024 * 1024
        root_path = os.path.expanduser(root_path)
        results = []
        found_paths = set()

        def update_status(msg):
            self.root.after(0, lambda: self.status_var.set(msg))

        def add_result(path, size, kind, label, hint):
            if path not in found_paths:
                found_paths.add(path)
                results.append((path, size, kind, label, hint))

        start = time.time()

        # Phase 1: du scan
        update_status("[PHASE 1/2] Running du scan...")
        try:
            proc = subprocess.run(
                ["du", "-d", "3", "-k", root_path],
                capture_output=True, text=True, timeout=120
            )
            du_lines = proc.stdout.strip().split("\n") if proc.stdout else []
        except subprocess.TimeoutExpired:
            du_lines = []

        scanned = 0
        home = os.path.expanduser("~")
        for line in du_lines:
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            try:
                size_kb = int(parts[0])
            except ValueError:
                continue
            full_path = parts[1]
            size_bytes = size_kb * 1024
            if size_bytes < min_bytes:
                continue

            scanned += 1
            name = os.path.basename(full_path)
            rel = full_path.replace(home, "~")

            if name in PROGRAMMING_DIRS:
                label, hint = PROGRAMMING_DIRS[name]
                add_result(rel, size_bytes, "dev", label, hint)
            else:
                for pattern, (desc, h) in PROGRAMMING_DIRS.items():
                    if "/" in pattern and full_path.endswith(pattern):
                        add_result(rel, size_bytes, "dev", desc, h)
                        break

        # Phase 2: System data + large files in parallel
        update_status("[PHASE 2/2] Probing system data & large files...")

        existing_sys_paths = []
        for raw_path, description in SYSTEM_DATA_PATHS.items():
            full = os.path.expanduser(raw_path)
            if os.path.isdir(full):
                existing_sys_paths.append((raw_path, full, description))

        sys_results = [None]
        file_results = [None]

        def scan_system_paths():
            if not existing_sys_paths:
                sys_results[0] = []
                return
            paths = [p[1] for p in existing_sys_paths]
            try:
                proc = subprocess.run(
                    ["du", "-sk"] + paths,
                    capture_output=True, text=True, timeout=60
                )
                size_map = {}
                for line in (proc.stdout.strip().split("\n") if proc.stdout else []):
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        try:
                            size_map[parts[1]] = int(parts[0]) * 1024
                        except ValueError:
                            pass
                out = []
                for raw_path, full, description in existing_sys_paths:
                    size = size_map.get(full, 0)
                    if size >= min_bytes:
                        out.append((raw_path, size, "system", "System Data", description))
                sys_results[0] = out
            except subprocess.TimeoutExpired:
                sys_results[0] = []

        def scan_large_files():
            try:
                proc = subprocess.run(
                    ["find", root_path, "-maxdepth", "6", "-type", "f",
                     "-size", f"+{min_mb}M"],
                    capture_output=True, text=True, timeout=60
                )
                out = []
                for fpath in (proc.stdout.strip().split("\n") if proc.stdout.strip() else []):
                    try:
                        size = os.path.getsize(fpath)
                        rel = fpath.replace(home, "~")
                        out.append((rel, size, "file", "Large file", ""))
                    except OSError:
                        pass
                file_results[0] = out
            except subprocess.TimeoutExpired:
                file_results[0] = []

        t1 = threading.Thread(target=scan_system_paths, daemon=True)
        t2 = threading.Thread(target=scan_large_files, daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        for r in (sys_results[0] or []):
            add_result(*r)
        for r in (file_results[0] or []):
            add_result(*r)

        # Top-level folders from du output
        for line in du_lines:
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            full_path = parts[1]
            if full_path == root_path:
                continue
            if full_path.count("/") != root_path.rstrip("/").count("/") + 1:
                continue
            try:
                size_bytes = int(parts[0]) * 1024
            except ValueError:
                continue
            if size_bytes >= min_bytes:
                rel = full_path.replace(home, "~")
                add_result(rel, size_bytes, "folder", "Folder", "")

        elapsed = time.time() - start
        results.sort(key=lambda x: x[1], reverse=True)

        self.root.after(0, lambda: self._display_results(results, scanned, elapsed))

    def _display_results(self, results, scanned, elapsed):
        self.items = results
        self.tree.delete(*self.tree.get_children())

        tag_colors = {
            "dev":    C["yellow"],
            "file":   C["blue"],
            "folder": C["fg"],
            "system": C["red"],
        }
        for tag, color in tag_colors.items():
            self.tree.tag_configure(tag, foreground=color)

        dev_total = 0
        system_total = 0
        other_total = 0

        for path, size, kind, label, hint in results:
            if kind == "dev":
                dev_total += size
            elif kind == "system":
                system_total += size
            else:
                other_total += size
            self.tree.insert("", "end", values=(fmt_size(size), label, path),
                             tags=(kind,))

        self.status_var.set(f"[COMPLETE] {scanned} targets scanned in {elapsed:.1f}s — "
                            f"{len(results)} items found")
        self.subtitle_label.configure(text="hack the planet... starting with your hard drive █",
                                      fg=C["fg_dim"])
        grand = dev_total + system_total + other_total
        self.summary_var.set(
            f"DEV: {fmt_size(dev_total)}  |  "
            f"SYSTEM: {fmt_size(system_total)}  |  "
            f"OTHER: {fmt_size(other_total)}  |  "
            f"TOTAL: {fmt_size(grand)}"
        )

        self.scan_btn.configure(state="normal", text=" ► SCAN ")
        self.scanning = False

    # ── Actions ───────────────────────────────────────────────────────────

    def _get_selected_path(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        if idx < len(self.items):
            return os.path.expanduser(self.items[idx][0])
        return None

    def _copy_path(self):
        path = self._get_selected_path()
        if not path:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.status_var.set(f"[COPIED] {path}")

    def _drill_into(self):
        path = self._get_selected_path()
        if not path or not os.path.isdir(path):
            return
        self.path_history.append(self.path_var.get())
        self.back_btn.configure(state="normal")
        self.path_var.set(path)
        self._start_scan()

    def _go_back(self):
        if not self.path_history:
            return
        prev = self.path_history.pop()
        self.path_var.set(prev)
        if not self.path_history:
            self.back_btn.configure(state="disabled")
        self._start_scan()

    def _on_double_click(self, event):
        path = self._get_selected_path()
        if path and os.path.isdir(path):
            self._drill_into()

    def _open_selected(self):
        path = self._get_selected_path()
        if not path:
            return
        if os.path.exists(path):
            subprocess.Popen(["open", path])
        else:
            messagebox.showwarning("TARGET NOT FOUND", f"Path does not exist:\n{path}")

    def _open_parent(self):
        path = self._get_selected_path()
        if not path:
            return
        parent = os.path.dirname(path)
        if os.path.exists(parent):
            subprocess.Popen(["open", parent])
        else:
            messagebox.showwarning("TARGET NOT FOUND", f"Parent not found:\n{parent}")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if idx < len(self.items):
            path, size, kind, label, hint = self.items[idx]
            if hint:
                self.detail_var.set(f"// {label}: {hint}\n>> {path}")
            else:
                self.detail_var.set(f">> {path}  ({fmt_size(size)})")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = StorageApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
