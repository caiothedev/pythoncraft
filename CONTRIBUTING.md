# CONTRIBUTING - ᴇɴ

Thank you for considering a contribution to my Pythoncraft project! This document explains how the project is organized, the standards we follow, and how to submit your contribution correctly.

## Table of Contents

- [Prerequisites](#prerequisites)
- [How to contribute](#how-to-contribute)
- [Code standards](#code-standards)
- [Commits and Pull Requests](#commits-and-pull-requests)
- [Reporting bugs](#reporting-bugs)

## Prerequisites

- Python **3.10+**
- pip
- Git

## How to contribute

1. **Open an issue** before starting any major work — discuss the idea first.
2. **Fork** the repository and create a descriptive branch:
```bash
git checkout -b feature/crafting-system
git checkout -b fix/surface-block-collision
```
3. Make your changes, following the standards below.
4. Test your work by running `python main.py` and ensuring nothing is broken.
5. Open a **Pull Request** with a clear description of what was done and why.

## Code standards

- **Language:** Use English for variable, function, and class names; use Portuguese for comments, docstrings, and messages displayed to the player.
- **Typing:** Use type hints whenever possible (`def get_block(id: str) -> Block`).
- **No extra dependencies** without prior discussion — the project is intentionally kept lightweight.
- Follow the style already established in existing modules: registration functions (`register_*`), loading functions (`load_all_*`), and getters (`get_*`). ## Commits and Pull Requests

Use short commit messages in Portuguese:

```
feat: add sand block with physics
fix: fix collision at chunk edges
refactor: separate chunk logic into core/chunk.py
assets: add birch wood texture
docs: update CONTRIBUTING with entity workflow
```

Small, focused PRs are easier to review. Avoid mixing features and fixes in the same PR.

## Reporting bugs

Open an issue including:

- **What happened** (current behavior)
- **What should have happened** (expected behavior)
- **How ​​to reproduce** (step-by-step instructions)
- **Python version and operating system**

by caiothedev<br/>
#contributing #game