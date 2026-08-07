#!/usr/bin/env bash
set -Eeuo pipefail

FOUND=0

if [ ! -d "pkgs" ]; then
    echo ":: Error: Directory 'pkgs' does not exist."
    exit 1
fi

while IFS= read -r -d '' pkgbuild; do
    FOUND=1
    pkg_dir="$(dirname "$pkgbuild")"
    
    echo ":: Generating .SRCINFO for $pkg_dir"
    (
        cd "$pkg_dir"
        makepkg --printsrcinfo > .SRCINFO
    )
done < <(find pkgs -mindepth 2 -name PKGBUILD -print0)

if [ "$FOUND" -eq 0 ]; then
    echo ":: Warning: No PKGBUILD files found under pkgs/."
fi