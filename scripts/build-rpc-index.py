#!/usr/bin/env python3
import os
import json
from pathlib import Path

results = []
repo_url = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'usuario/repo')}"

# Busca los .SRCINFO exclusivamente dentro de pkgs/
for srcinfo_path in sorted(Path("pkgs").glob("*/.SRCINFO")):
    pkgname = srcinfo_path.parent.name
    pkgver, pkgrel, desc = "", "", ""

    with srcinfo_path.open() as f:
        for line in f:
            line = line.strip()
            if line.startswith("pkgver ="):
                pkgver = line.split("=")[1].strip()
            elif line.startswith("pkgrel ="):
                pkgrel = line.split("=")[1].strip()
            elif line.startswith("pkgdesc ="):
                desc = line.split("=")[1].strip()

    results.append({
        "Name": pkgname,
        "PackageBase": pkgname,
        "Version": f"{pkgver}-{pkgrel}",
        "Description": desc,
        "URLPath": f"{repo_url}/raw/main/pkgs/{pkgname}",
        "URL": repo_url
    })

output_dir = Path("public")
output_dir.mkdir(exist_ok=True)

output = {
    "version": 5,
    "type": "multiinfo",
    "resultcount": len(results),
    "results": results
}

with (output_dir / "rpc.json").open("w") as f:
    json.dump(output, f, indent=2)

print(f":: Indexed {len(results)} packages in public/rpc.json")