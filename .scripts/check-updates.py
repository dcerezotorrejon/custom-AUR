#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path

new_file = Path("newver.json")
old_file = Path("oldver.json")

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

old_payload = {"version": 2, "data": {}}
if old_file.exists() and old_file.stat().st_size > 0:
    try:
        with old_file.open("r", encoding="utf-8") as f:
            old_payload = json.load(f)
    except Exception:
        pass

old_data = old_payload.get("data", old_payload)

def build_pkgbuild_index():
    index = {}
    ignored_dirs = {"scripts", "utils", "ci-helpers"}

    for pkg_dir in Path(".").iterdir():
        if not pkg_dir.is_dir():
            continue
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

# Get default branch
default_branch_res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
default_branch = default_branch_res.stdout.strip()

updated_count = 0

for raw_pkgname, info in version_map.items():
    new_ver = info.get("version") if isinstance(info, dict) else info
    if not new_ver:
        continue

    pkgbuild_path = pkg_index.get(raw_pkgname)
    if not pkgbuild_path or not pkgbuild_path.is_file():
        print(f":: Warning: No matching PKGBUILD found for '{raw_pkgname}'.")
        continue

    pkg_dir = pkgbuild_path.parent
    app_name = pkg_dir.name

    # Sanitización estricta para cumplir con las reglas de Arch Linux
    clean_ver = str(new_ver).lstrip("vV")
    clean_ver = re.sub(r"-.*$", "", clean_ver)
    clean_ver = re.sub(r"[^\w.]", "", clean_ver)

    old_entry = old_data.get(raw_pkgname, {})
    old_ver = old_entry.get("version") if isinstance(old_entry, dict) else old_entry

    if clean_ver == old_ver:
        print(f":: {app_name} ({raw_pkgname}) is already up to date ({clean_ver}).")
        continue

    print(f":: Processing update for {app_name} ({raw_pkgname}): {old_ver} -> {clean_ver}")

    # Ensure we start from default branch and clean workspace
    subprocess.run(["git", "checkout", default_branch], check=True)
    subprocess.run(["git", "reset", "--hard", f"origin/{default_branch}"], capture_output=True)

    branch_name = f"update/{app_name}-{clean_ver}"
    
    # Create or reset branch
    subprocess.run(["git", "checkout", "-B", branch_name], check=True)

    original = pkgbuild_path.read_text()

    # 1. Actualizar pkgver y resetear pkgrel a 1
    updated, v_count = re.subn(r"^pkgver=.*$", f"pkgver={clean_ver}", original, count=1, flags=re.MULTILINE)
    updated, r_count = re.subn(r"^pkgrel=.*$", "pkgrel=1", updated, count=1, flags=re.MULTILINE)

    if v_count > 0 and r_count > 0 and updated != original:
        pkgbuild_path.write_text(updated)
        print(f":: Updated PKGBUILD for {app_name} -> {clean_ver}-1")

        # 2. Actualizar sha256sums / sha512sums en el PKGBUILD
        print(f":: Updating checksums for {app_name}...")
        try:
            subprocess.run(["updpkgsums"], cwd=pkg_dir, check=True)
            print(f":: Checksums updated successfully for {app_name}")
        except subprocess.CalledProcessError as e:
            print(f":: Error updating checksums for {app_name}: {e}")
            continue

        # 3. Generar .SRCINFO actualizado
        print(f":: Generating .SRCINFO for {app_name}...")
        try:
            with open(pkg_dir / ".SRCINFO", "w", encoding="utf-8") as f:
                subprocess.run(["makepkg", "--printsrcinfo"], cwd=pkg_dir, stdout=f, check=True)
            print(f":: .SRCINFO updated successfully for {app_name}")
        except subprocess.CalledProcessError as e:
            print(f":: Error generating .SRCINFO for {app_name}: {e}")
            continue

        # 4. Actualizar oldver.json para este paquete
        if "data" not in old_payload:
            old_payload["data"] = {}
        old_payload["data"][raw_pkgname] = {"version": clean_ver}
        with old_file.open("w", encoding="utf-8") as f:
            json.dump(old_payload, f, indent=2)

        # 5. Commit y push
        subprocess.run(["git", "add", str(pkgbuild_path), str(pkg_dir / ".SRCINFO"), str(old_file)], check=True)

        diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff_check.returncode == 0:
            print(f":: No changes detected for {app_name}.")
            continue

        subprocess.run(["git", "commit", "-m", f"auto: update {app_name} to {clean_ver}"], check=True)
        
        print(f":: Pushing branch {branch_name}...")
        subprocess.run(["git", "push", "-f", "origin", branch_name], check=True)

        # 6. Crear PR y auto-aprobar
        pr_title = f"[UPDATE] {app_name} - {clean_ver}"
        pr_body = f"Automated update for **{app_name}** to version **{clean_ver}**.\n\nGenerated by nvchecker & check-updates script."
        
        print(f":: Creating PR: {pr_title}")
        try:
            pr_list = subprocess.run(["gh", "pr", "list", "--head", branch_name, "--state", "open", "--json", "number"], capture_output=True, text=True, check=True)
            pr_data = json.loads(pr_list.stdout)
            
            if not pr_data:
                subprocess.run([
                    "gh", "pr", "create",
                    "--title", pr_title,
                    "--body", pr_body,
                    "--base", default_branch,
                    "--head", branch_name
                ], check=True)
            else:
                print(f":: PR already exists for branch {branch_name}, updating title if needed.")
                pr_num = pr_data[0]["number"]
                subprocess.run(["gh", "pr", "edit", str(pr_num), "--title", pr_title, "--body", pr_body], check=True)

            print(f":: Auto-approving PR for {app_name}...")
            subprocess.run([
                "gh", "pr", "review", branch_name, "--approve",
                "--body", "Auto-approved update PR."
            ], check=True)

        except subprocess.CalledProcessError as e:
            print(f":: Error creating or approving PR for {app_name}: {e}")

        updated_count += 1
    else:
        print(f":: {app_name} ({raw_pkgname}) is up to date ({clean_ver}).")

print(f":: Total recipes updated & PRs created: {updated_count}")
