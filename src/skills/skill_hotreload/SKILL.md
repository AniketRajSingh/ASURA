---
name: skill_hotreload
description: "Dynamically hot-reload skill modules without restarting the ASURA system."
entry_point: reloader.py
---

# Skill Hot-Reload

Hot-reload individual or all skills dynamically to apply code changes without a full system restart.

### 🔧 Tools / Functions
- `reload_skill(skill_name: str) -> dict`: Hot-reload a specific skill module by name.
- `reload_all_skills() -> dict`: Discover and reload all available skill modules.

### 📝 Examples
- "Reload the weather skill" -> Hot-reloads `skills.weather`.
- "Apply changes to all skills" -> Triggers a full reload of the skill registry.

### 🛠️ Requirements
- Skill modules must be located in the `skills/` package.
