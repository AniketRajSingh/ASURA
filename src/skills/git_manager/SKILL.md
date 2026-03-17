---
name: git_manager
description: "Git integration skill. Provides auto-commits, branch management, status, diffs, and logs to track system evolution."
entry_point: git.py
---

# Git Manager

Integrates version control into the ASURA ecosystem. It enables the system to track its own evolution through automated commits, manage development branches, and provide detailed insights into code changes via status, diff, and log summaries.

### 🔧 Tools / Functions
- `init_repo()`: Initialize a new Git repository in the project root if one does not already exist.
- `status()`: Retrieve the current Git status in a concise porcelain format.
- `diff(staged)`: Generate a diff of current changes (optionally restricted to staged files).
- `auto_commit(message)`: Automatically stage all changes and create a commit with a timestamped message.
- `create_branch(name)`: Create and immediately switch to a new Git branch.
- `switch_branch(name)`: Switch between existing Git branches.
- `log(n)`: Display the last `n` commit messages in a condensed oneline format.
- `format_git_summary()`: Generate a formatted Markdown summary of the current branch, status, and recent history.

### 📝 Examples
- "Check my git status" -> Displays current branch and modified files.
- "Commit these changes" -> Automatically stages all files and creates a new commit.

### 🛠️ Requirements
- `git` (system-level installation)
