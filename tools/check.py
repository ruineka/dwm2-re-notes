#!/usr/bin/env python3
"""Sanity checks for this notes repository.

Run before committing:  python3 tools/check.py

Checks:
  * every Markdown file has a title line;
  * every relative link in README/HOW-TO/GLOSSARY/PROVENANCE/CONTRIBUTING
    resolves to a file that exists;
  * every numbered reference file is listed in README.md;
  * no absolute home paths, no ROM/save files, no oversized or binary files.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".txt"}
ALLOWED_NO_SUFFIX = {"LICENSE", ".gitignore"}
MAX_BYTES = 512 * 1024
BANNED_SUFFIXES = {".gbc", ".gb", ".gbx", ".sav", ".srm", ".ram", ".state",
                   ".bin", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HOME_PATHS = ("/home/", "/Users/", "C:\\", "file://")


def repo_files() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or ".git" in p.parts:
            continue
        out.append(p)
    return out


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    files = repo_files()
    md_files = [p for p in files if p.suffix == ".md"]

    # 1. non-text files, sizes, suffixes
    for p in files:
        rel = p.relative_to(ROOT)
        if p.suffix in BANNED_SUFFIXES:
            errors.append(f"{rel}: forbidden file type {p.suffix}")
            continue
        if p.suffix not in TEXT_SUFFIXES and p.name not in ALLOWED_NO_SUFFIX:
            warnings.append(f"{rel}: unexpected file type")
        if p.stat().st_size > MAX_BYTES:
            errors.append(f"{rel}: {p.stat().st_size} bytes is too large")

    # 2. titles
    for p in md_files:
        first = p.read_text(encoding="utf-8").splitlines()[:1]
        if not first or not first[0].startswith("# "):
            errors.append(f"{p.relative_to(ROOT)}: missing '# ' title line")

    # 3. links resolve
    for p in md_files:
        text = p.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0].strip()
            if not target:
                continue
            resolved = (p.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{p.relative_to(ROOT)}: broken link -> {target}")

    # 4. numbered files listed in README
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    numbered = sorted(p.name for p in ROOT.glob("[0-9][0-9]-*.md"))
    if len(numbered) != 14:
        errors.append(f"expected 14 numbered notes, found {len(numbered)}")
    for name in numbered:
        if name not in readme:
            errors.append(f"README.md does not link {name}")

    # 5. absolute home paths in prose
    for p in files:
        if p.suffix not in TEXT_SUFFIXES and p.name not in ALLOWED_NO_SUFFIX:
            continue
        if p.name == "check.py":  # this file defines the patterns
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for bad in HOME_PATHS:
            if bad in text:
                errors.append(f"{p.relative_to(ROOT)}: contains absolute path {bad!r}")

    # 6. trailing whitespace (warning only)
    for p in md_files:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line != line.rstrip():
                warnings.append(f"{p.relative_to(ROOT)}:{i}: trailing whitespace")
                break

    for w in warnings:
        print(f"warn:  {w}")
    for e in errors:
        print(f"error: {e}")

    print(f"\n{len(files)} files, {len(md_files)} Markdown, "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
