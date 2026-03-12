#!/usr/bin/env python3
"""
macOS Storage Analyzer - Find large files/folders and identify programming bloat.
"""

import os
import sys
import time
from pathlib import Path
from collections import defaultdict

# ── Programming-related patterns ──────────────────────────────────────────────

PROGRAMMING_DIRS = {
    "node_modules":        "Node.js dependencies",
    ".npm":                "npm cache",
    ".yarn":               "Yarn cache",
    ".pnpm-store":         "pnpm cache",
    "venv":                "Python virtualenv",
    ".venv":               "Python virtualenv",
    "env":                 "Python virtualenv",
    "__pycache__":         "Python bytecode cache",
    ".tox":                "Python tox environments",
    ".mypy_cache":         "mypy type-check cache",
    ".pytest_cache":       "pytest cache",
    "site-packages":       "Python installed packages",
    ".cargo":              "Rust cargo cache",
    "target":              "Rust/Java build output",
    ".rustup":             "Rust toolchain",
    ".gradle":             "Gradle cache",
    ".m2":                 "Maven cache",
    "build":               "Build output",
    "dist":                "Distribution/build output",
    ".next":               "Next.js build cache",
    ".nuxt":               "Nuxt.js build cache",
    ".cache":              "General cache",
    "Pods":                "CocoaPods (iOS deps)",
    "DerivedData":         "Xcode build data",
    ".cocoapods":          "CocoaPods cache",
    "vendor":              "Vendored dependencies",
    ".bundle":             "Ruby bundler",
    ".gem":                "Ruby gems",
    ".rbenv":              "Ruby version manager",
    ".pyenv":              "Python version manager",
    ".nvm":                "Node version manager",
    ".sdkman":             "SDK manager (Java etc)",
    ".conda":              "Conda environments",
    ".local":              "Local installs (pip etc)",
    "go":                  "Go workspace/modules",
    ".docker":             "Docker data",
    ".vagrant":            "Vagrant VMs",
    "Library/Developer":   "Xcode & dev tools data",
    ".android":            "Android SDK data",
    "anaconda3":           "Anaconda Python distribution",
    "miniconda3":          "Miniconda Python distribution",
    ".julia":              "Julia packages",
    ".ghcup":              "Haskell toolchain",
    ".stack":              "Haskell Stack",
    ".opam":               "OCaml package manager",
    ".pub-cache":          "Dart/Flutter pub cache",
    ".flutter":            "Flutter SDK",
    "Library/Caches/Homebrew": "Homebrew download cache",
    ".Trash":              "Trash (can be emptied)",
}

PROGRAMMING_EXTENSIONS = {
    ".o", ".a", ".dylib", ".so", ".dll", ".class", ".jar", ".war",
    ".pyc", ".pyo", ".whl", ".egg",
    ".log",
}

# ── Size formatting ───────────────────────────────────────────────────────────

def fmt_size(nbytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:,.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:,.1f} PB"

# ── Directory size calculation ────────────────────────────────────────────────

def dir_size(path):
    """Get total size of a directory (follows no symlinks)."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_symlink():
                    continue
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += dir_size(entry.path)
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    return total

# ── Scanning ──────────────────────────────────────────────────────────────────

def scan(root, min_size_mb=100, max_depth=6):
    """Walk the filesystem and collect large items."""
    min_bytes = min_size_mb * 1024 * 1024
    root = os.path.expanduser(root)
    results = []         # (path, size, programming_label_or_None)
    skip_dirs = set()    # dirs we already measured — don't recurse into
    large_files = []

    print(f"\n  Scanning {root} for items >= {min_size_mb} MB …\n")
    scanned = 0

    def _walk(current, depth):
        nonlocal scanned
        if depth > max_depth:
            return
        try:
            entries = list(os.scandir(current))
        except (PermissionError, OSError):
            return

        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                name = entry.name

                # Check if this directory matches a programming pattern
                if entry.is_dir(follow_symlinks=False):
                    scanned += 1
                    if scanned % 500 == 0:
                        print(f"  … scanned {scanned} directories", end="\r")

                    label = None
                    rel = entry.path.replace(os.path.expanduser("~"), "~")

                    # Check exact dir name matches
                    if name in PROGRAMMING_DIRS:
                        label = PROGRAMMING_DIRS[name]
                    else:
                        # Check path-based matches (e.g. Library/Developer)
                        for pattern, desc in PROGRAMMING_DIRS.items():
                            if "/" in pattern and entry.path.endswith(pattern):
                                label = desc
                                break

                    if label:
                        size = dir_size(entry.path)
                        if size >= min_bytes:
                            results.append((rel, size, label))
                            skip_dirs.add(entry.path)
                        continue  # don't recurse into known programming dirs

                    if entry.path not in skip_dirs:
                        _walk(entry.path, depth + 1)

                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    if stat.st_size >= min_bytes:
                        rel = entry.path.replace(os.path.expanduser("~"), "~")
                        ext = os.path.splitext(name)[1].lower()
                        label = None
                        if ext in PROGRAMMING_EXTENSIONS:
                            label = f"Programming artifact ({ext})"
                        large_files.append((rel, stat.st_size, label))

            except (PermissionError, OSError):
                pass

    _walk(root, 0)

    # Also measure top-level dirs that weren't caught as programming dirs
    # to give a high-level overview
    top_level = []
    try:
        for entry in os.scandir(root):
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                path = entry.path
                if path not in skip_dirs:
                    scanned += 1
                    size = dir_size(path)
                    if size >= min_bytes:
                        rel = path.replace(os.path.expanduser("~"), "~")
                        top_level.append((rel, size, None))
    except (PermissionError, OSError):
        pass

    print(f"  … done! Scanned {scanned} directories.            \n")
    return results, large_files, top_level


def print_section(title, items, color):
    if not items:
        return
    items.sort(key=lambda x: x[1], reverse=True)
    colors = {"red": "\033[91m", "yellow": "\033[93m", "blue": "\033[94m", "green": "\033[92m", "bold": "\033[1m"}
    c = colors.get(color, "")
    reset = "\033[0m"
    dim = "\033[2m"

    print(f"  {colors['bold']}{c}{'─' * 60}")
    print(f"  {title}")
    print(f"  {'─' * 60}{reset}\n")

    total = 0
    for path, size, label in items:
        total += size
        size_str = fmt_size(size)
        line = f"  {c}{size_str:>12}{reset}  {path}"
        if label:
            line += f"  {dim}← {label}{reset}"
        print(line)

    print(f"\n  {c}{'Total:':>12} {fmt_size(total)}{reset}\n")


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~")
    min_mb = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    bold = "\033[1m"
    reset = "\033[0m"
    dim = "\033[2m"

    print(f"\n  {bold}macOS Storage Analyzer{reset}")
    print(f"  {dim}Scanning for items >= {min_mb} MB{reset}")

    start = time.time()
    programming, large_files, top_level = scan(root, min_size_mb=min_mb)
    elapsed = time.time() - start

    print_section("🔧 PROGRAMMING / DEV  (safe to review for cleanup)", programming, "yellow")
    print_section("📄 LARGE FILES", large_files, "blue")
    print_section("📁 LARGE FOLDERS  (non-programming)", top_level, "green")

    # Summary
    prog_total = sum(s for _, s, _ in programming)
    file_total = sum(s for _, s, _ in large_files)
    folder_total = sum(s for _, s, _ in top_level)

    print(f"  {bold}{'─' * 60}")
    print(f"  SUMMARY")
    print(f"  {'─' * 60}{reset}")
    print(f"  Programming / Dev:   {fmt_size(prog_total)}")
    print(f"  Large files:         {fmt_size(file_total)}")
    print(f"  Large folders:       {fmt_size(folder_total)}")
    print(f"  {dim}Scan took {elapsed:.1f}s{reset}")
    print()

    if programming:
        print(f"  {bold}💡 Quick wins to free space:{reset}")
        print(f"  {dim}  • node_modules — run 'rm -rf node_modules' in unused projects{reset}")
        print(f"  {dim}  • .venv/venv   — delete virtualenvs for old projects{reset}")
        print(f"  {dim}  • DerivedData  — rm -rf ~/Library/Developer/Xcode/DerivedData{reset}")
        print(f"  {dim}  • Homebrew     — brew cleanup --prune=all{reset}")
        print(f"  {dim}  • npm/yarn     — npm cache clean --force{reset}")
        print(f"  {dim}  • pip          — pip cache purge{reset}")
        print(f"  {dim}  • Docker       — docker system prune -a{reset}")
        print(f"  {dim}  • Trash        — empty your Trash from Finder{reset}")
        print()


if __name__ == "__main__":
    main()
