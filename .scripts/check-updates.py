#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path

new_file = Path("newver.json")

if not new_file.exists() or new_file.stat().st_size == 0:
    print(":: No updates detected by nvchecker.")
    sys.exit(0)

try:
    with new_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)
except Exception as e:
    print(f":: Error reading newver.json: {e}")
    sys.exit(1)

version_map = payload.get("data", payload)

if not isinstance(version_map, dict) or not version_map:
    print(":: No valid version data found.")
    sys.exit(0)


def build_pkgbuild_index():
    index = {}
    
    # Carpetas en la raíz que NO contienen paquetes y queremos ignorar explícitamente
    ignored_dirs = {"scripts", "utils", "ci-helpers"}

    # Escaneamos todas las subcarpetas del directorio actual (raíz)
    for pkg_dir in Path(".").iterdir():
        if not pkg_dir.is_dir():
            continue
            
        # Ignoramos carpetas ocultas (como .git o .github) o de herramientas
        if pkg_dir.name.startswith(".") or pkg_dir.name in ignored_dirs:
            continue

        pkgbuild_path = pkg_dir / "PKGBUILD"
        if not pkgbuild_path.is_file():
            continue

        folder_name = pkg_dir.name
        index[folder_name] = pkgbuild_path

        content = pkgbuild_path.read_text()

        pkgname_match = re.search(r"^pkgname=([^\s#]+)", content, re.MULTILINE)
        if pkgname_match:
            clean_pkgname = pkgname_match.group(1).strip("'\"")
            index[clean_pkgname] = pkgbuild_path

        provides_match = re.search(r"^provides=\((.*?)\)", content, re.MULTILINE | re.DOTALL)
        if provides_match:
            tokens = re.findall(r"['\"]?([a-zA-Z0-9_.-]+)['\"]?", provides_match.group(1))
            for item in tokens:
                if item and not item.startswith("#"):
                    index[item] = pkgbuild_path

    return index


pkg_index = build_pkgbuild_index()
updated_count = 0

for raw_pkgname, info in version_map.items():
    new_ver = info.get("version") if isinstance(info, dict) else info
    if not new_ver:
        continue

    pkgbuild_path = pkg_index.get(raw_pkgname)
    if not pkgbuild_path or not pkgbuild_path.is_file():
        print(f":: Warning: No matching PKGBUILD found for '{raw_pkgname}'.")
        continue

    # Sanitización estricta para cumplir con las reglas de Arch Linux
    clean_ver = str(new_ver).lstrip("vV")
    clean_ver = re.sub(r"-.*$", "", clean_ver)          # Elimina el guion y sufijo Debian/RPM (ej: 151.0.7922.108-1 -> 151.0.7922.108)
    clean_ver = re.sub(r"[^\w.]", "", clean_ver)        # Remueve cualquier carácter no permitido en pkgver

    original = pkgbuild_path.read_text()

    # 1. Actualizar pkgver y resetear pkgrel a 1
    updated, v_count = re.subn(r"^pkgver=.*$", f"pkgver={clean_ver}", original, count=1, flags=re.MULTILINE)
    updated, r_count = re.subn(r"^pkgrel=.*$", "pkgrel=1", updated, count=1, flags=re.MULTILINE)

    if v_count > 0 and r_count > 0 and updated != original:
        pkgbuild_path.write_text(updated)
        pkg_dir = pkgbuild_path.parent
        print(f":: Updated {pkg_dir.name} ({raw_pkgname}) -> {clean_ver}-1")

        # 1. Actualizar sha256sums / sha512sums en el PKGBUILD
        print(f":: Updating checksums for {pkg_dir.name}...")
        try:
            subprocess.run(["updpkgsums"], cwd=pkg_dir, check=True)
            print(f":: Checksums updated successfully for {pkg_dir.name}")
        except subprocess.CalledProcessError as e:
            print(f":: Error updating checksums for {pkg_dir.name}: {e}")

        # 2. Generar .SRCINFO actualizado para esta receta
        print(f":: Generating .SRCINFO for {pkg_dir.name}...")
        try:
            with open(pkg_dir / ".SRCINFO", "w", encoding="utf-8") as f:
                subprocess.run(["makepkg", "--printsrcinfo"], cwd=pkg_dir, stdout=f, check=True)
            print(f":: .SRCINFO updated successfully for {pkg_dir.name}")
        except subprocess.CalledProcessError as e:
            print(f":: Error generating .SRCINFO for {pkg_dir.name}: {e}")

        updated_count += 1
    else:
        print(f":: {pkgbuild_path.parent.name} ({raw_pkgname}) is up to date ({clean_ver}).")

print(f":: Total recipes updated: {updated_count}")