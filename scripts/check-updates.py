#!/usr/bin/env python3
import json
import re
from pathlib import Path

new_file = Path("newver.json")

if not new_file.exists() or new_file.stat().st_size == 0:
    print(":: No updates detected by nvchecker.")
    raise SystemExit(0)

try:
    with new_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)
except Exception as e:
    print(f":: Error reading newver.json: {e}")
    raise SystemExit(1)

version_map = payload.get("data", {})

if not version_map:
    print(":: No updates detected by nvchecker.")
    raise SystemExit(0)


def build_pkgbuild_index():
    index = {}
    pkgs_dir = Path("pkgs")
    
    if not pkgs_dir.is_dir():
        return index

    for pkgbuild_path in pkgs_dir.glob("*/PKGBUILD"):
        folder_name = pkgbuild_path.parent.name
        index[folder_name] = pkgbuild_path

        content = pkgbuild_path.read_text()

        # 1. Extraer pkgname=...
        pkgname_match = re.search(r"^pkgname=([^\s#]+)", content, re.MULTILINE)
        if pkgname_match:
            clean_pkgname = pkgname_match.group(1).strip("'\"")
            index[clean_pkgname] = pkgbuild_path

        # 2. Extraer provides=(...) tolerando multilínea y comillas
        provides_match = re.search(r"^provides=\((.*?)\)", content, re.MULTILINE | re.DOTALL)
        if provides_match:
            raw_provides = provides_match.group(1)
            # Separa tokens limpiando comillas, apóstrofes y comentarios
            tokens = re.findall(r"['\"]?([a-zA-Z0-9_.-]+)['\"]?", raw_provides)
            for item in tokens:
                if item and not item.startswith("#"):
                    index[item] = pkgbuild_path

    return index


pkg_index = build_pkgbuild_index()

for raw_pkgname, info in version_map.items():
    new_ver = info.get("version") if isinstance(info, dict) else info
    if not new_ver:
        continue

    pkgbuild_path = pkg_index.get(raw_pkgname)
    
    if not pkgbuild_path or not pkgbuild_path.is_file():
        print(f":: Warning: No matching PKGBUILD found for '{raw_pkgname}'.")
        continue

    clean_ver = re.sub(r"^[vV]", "", str(new_ver))
    original = pkgbuild_path.read_text()

    updated, v_count = re.subn(r"^pkgver=.*$", f"pkgver={clean_ver}", original, count=1, flags=re.MULTILINE)
    updated, r_count = re.subn(r"^pkgrel=.*$", "pkgrel=1", updated, count=1, flags=re.MULTILINE)

    if v_count > 0 and r_count > 0 and updated != original:
        pkgbuild_path.write_text(updated)
        print(f":: Updated {pkgbuild_path.parent.name} ({raw_pkgname}) -> {clean_ver}-1")
    else:
        print(f":: {pkgbuild_path.parent.name} ({raw_pkgname}) is already at latest version ({clean_ver}).")