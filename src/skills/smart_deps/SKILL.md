---
name: smart_deps
description: "Automatically detects and upgrades outdated Python dependencies."
entry_point: upgrader.py
---

# Smart Dependency Skill

Provides automated dependency management by monitoring the current environment for outdated Python packages and facilitating their upgrade. It ensures the system remains secure and up-to-date with the latest library versions.

### 🔧 Tools / Functions
- `check_outdated()`: Uses `pip` to list all currently installed packages that have newer versions available.
- `upgrade_package(name)`: Upgrades a specified package to its latest version using `pip install --upgrade`.
- `format_deps_report()`: Generates a human-readable summary report of all outdated dependencies.

### 📝 Examples
- "Are any of my packages outdated?" -> Returns a report of outdated dependencies.
- "Upgrade the 'requests' library" -> Upgrades the specified library and logs the result.

### 🛠️ Requirements
- `pip` executable available in the system path.
- Write permissions for the environment's site-packages.
