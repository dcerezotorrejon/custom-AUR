#!/usr/bin/env python3
import json
import re
from pathlib import Path

new_file = Path("nvchecker.json")
if not new_file.exists():
    print(":: No updates detected by nvchecker.")
    raise SystemExit(0)

with new_file.open() as f:
    data = json.load(f)

version_map = data.get("data", data)
if not isinstance(version_map, dict):
    raise SystemExit(":: Error: Invalid json format in nvchecker.json")

for pkgname, info in version_map.items():
    new_ver = info.get("version") if isinstance(info, dict) else info
    if not new_ver:
        continue

    # Apunta a pkgs/<pkgname>/PKGBUILD
    pkgbuild_path = Path("pkgs") / pkgname / "PKGBUILD"
    if not pkgbuild_path.is_file():
        print(f":: Warning: PKGBUILD for {pkgname} not found at {pkgbuild_path}.")
        continue

    clean_ver = re.sub(r"^[vV]", "", str(new_ver))
    original = pkgbuild_path.read_text()

    updated, v_count = re.subn(r"^pkgver=.*$", f"pkgver={clean_ver}", original, count=1, flags=re.MULTILINE)
    updated, r_count = re.subn(r"^pkgrel=.*$", "pkgrel=1", updated, count=1, flags=re.MULTILINE)

    if v_count > 0 and r_count > 0 and updated != original:
        pkgbuild_path.write_text(updated)
        print(f":: Updated {pkgname} -> {clean_ver}-1")