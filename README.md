# Custom AUR Recipes 🚀

A personal `PKGBUILD` repository for **Arch Linux** and **CachyOS**, fully automated via **GitHub Actions** and **nvchecker**.

It keeps custom package recipes updated against upstream sources and allows consuming them natively on your local system using **Paru 2.0+**, leveraging the external PKGBUILD repositories feature without needing RPC servers or proxy intermediaries.

---

## 🛠️ Repository Structure

```text
custom-AUR/
├── .github/workflows/
│   └── update-recipes.yml   # Continuous integration workflow
├── pkgs/
│   └── visual-studio-code/  # Package recipe directory
│       ├── PKGBUILD
│       └── .SRCINFO
├── scripts/
│   ├── check-updates.py     # Updates pkgver, pkgrel & invokes updpkgsums
│   └── generate-srcinfo.sh  # Generates .SRCINFO using makepkg
├── nvchecker.toml           # Version tracking configuration
├── oldver.json              # Tracked version state
└── README.md
```

---

## 🔄 How It Works

The repository runs an automated daily pipeline via **GitHub Actions**:

1. **Upstream Tracking:** `nvchecker` queries official upstream APIs and endpoints.
2. **Recipe Updates:** `check-updates.py` updates `pkgver`, resets `pkgrel=1`, and runs `updpkgsums` to recalculate `sha256sums` directly in the `PKGBUILD`.
3. **Metadata Refresh:** `generate-srcinfo.sh` executes `makepkg --printsrcinfo > .SRCINFO` to keep metadata synced.
4. **Auto-commit:** If changes are detected, the workflow automatically commits and pushes them to the `main` branch.

---

## 💻 Local Setup (`paru.conf`)

Add the repository to your local **Paru** configuration (`~/.config/paru/paru.conf` or `/etc/paru.conf`):

```ini
[custom-AUR]
Url = [https://github.com/dcerezotorrejon/custom-AUR.git](https://github.com/dcerezotorrejon/custom-AUR.git)
```

*(Optional) For local testing during development:*
```ini
[custom-AUR-local]
Path = /path/to/your/clone/custom-AUR
```

---

## 🚀 Usage

```bash
# Sync external PKGBUILD repositories
paru -Sy --pkgbuilds

# Install or update a package
paru -S visual-studio-code
```

---

## 🔗 Useful Links

* [Arch Wiki: PKGBUILD Documentation](https://wiki.archlinux.org/title/PKGBUILD)
* [Paru Official GitHub Repository](https://github.com/Morganamilo/paru)
* [nvchecker Documentation](https://nvchecker.readthedocs.io/en/latest/)
* [It's FOSS: Paru 2.0 Release & Features](https://itsfoss.com/news/aur-helper-paru-2-0/)
* [CachyOS Official Website](https://cachyos.org/)