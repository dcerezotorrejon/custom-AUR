#!/usr/bin/env bash
set -Eeuo pipefail

FOUND=0

# Escanea los directorios en el primer nivel de la raíz que contengan un PKGBUILD
while IFS= read -r -d '' pkgbuild; do
    FOUND=1
    pkg_dir="$(dirname "$pkgbuild")"
    
    # Ignora carpetas ocultas del sistema (como .git o .github)
    if [[ "$pkg_dir" == .* ]]; then
        continue
    fi
    
    echo ":: Generating .SRCINFO for $pkg_dir"
    (
        cd "$pkg_dir"
        makepkg --printsrcinfo > .SRCINFO
    )
done < <(find . -maxdepth 2 -mindepth 2 -name PKGBUILD -print0)

if [ "$FOUND" -eq 0 ]; then
    echo ":: Warning: No PKGBUILD files found in root subdirectories."
fi
