# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository nature

This is **a content / knowledge repository**, not a software project. It is an Obsidian vault (`.obsidian/` is checked in) that organizes:

- Companion materials for a published Chinese-language AI book ("动手做 AI Agent：零基础玩转智能体")
- Original long-form AI books being authored in this repo (under `05-开源AI书籍/`)
- Courses, articles, notes, and reusable AI assets (prompts, Skills, MCP plugins)

There is no build system, no test suite, no linter, and no package manifest. The Python and shell files that do exist (`01-读者资料/chapter-3/code/...`) are illustrative code samples reproduced from the book — they are reference material, not application code. Do not treat them as a runnable project; do not add tooling (CI, formatters, dependency files) unless explicitly asked.

Most filenames, directory names, and prose are in **Simplified Chinese**. Preserve Chinese names verbatim when referencing paths — do not romanize or translate them in commits or links.

## Top-level layout

The repo uses **numbered, Chinese-named** top-level directories. The number prefix is meaningful — it defines reading order and section identity:

- `01-读者资料/` — Companion repo for the published book. Has its own `README.md`, `CONTRIBUTING.md`, `SOURCES.md`, `LICENSE`, and a `chapter-1/` … `chapter-3/` substructure.
- `02-课程与专辑/` — Courses (`课程/`) and albums (`专辑/`). Each course is a directory with `01-课程大纲/`, `02-课堂资料/`, `03-参考资料/`.
- `03-文章与笔记/` — Articles (`文章/`) and notes (`笔记/`). Currently placeholder-only (`.gitkeep`).
- `04-AI工具箱/` — Reusable assets: `Skills技能/`, `提示词与工作流/`, `MCP插件/`. Currently placeholder-only.
- `05-开源AI书籍/` — Long-form books being written in-repo. Each book is a directory; chapters are subdirectories named `第X章_…` or `第一部分/`, and individual sections are files named `X.X.X_主题.md` (e.g. `2.2.1_文件结构.md`).

When adding new top-level sections, follow the existing `NN-中文名/` numbering scheme and keep `.gitkeep` files in any directory that would otherwise be empty.

## Content conventions

### Chapter sub-structure (inside `01-读者资料/chapter-*/`)

Per `01-读者资料/CONTRIBUTING.md`:

```
chapter-X/
├── README.md       # Chapter intro
├── prompts/         # Prompt files (may have frameworks/, techniques/, examples/ subdirs)
├── code/            # Code samples (one subdir per project, e.g. flask-api/, metagpt/)
├── guides/          # How-to guides
└── knowledge/       # Concept summaries
```

### Provenance header (required for `01-读者资料/`)

Every Markdown file added under `01-读者资料/` must include a source-attribution block near the top, pointing back to the published book. The established pattern:

```markdown
> **📍 来源**：第X章 X.X 节 [节标题]
> **📄 行号**：第 XXXX-XXXX 行
> **📖 页码**：第 XX 页
```

For Python code samples, the same metadata goes in the module docstring (see `01-读者资料/chapter-3/code/flask-api/app.py` for the canonical example).

When you add or move files under `01-读者资料/`, also update `01-读者资料/SOURCES.md` — it is the master index mapping every file to its source location.

### Long-form book sections (inside `05-开源AI书籍/<book>/`)

- Section files use the pattern `X.X.X_主题名.md` (dotted numeric prefix, underscore, Chinese topic name). Match this exactly when adding new sections — sort order depends on it.
- Chapter directories use `第一章_…`, `第二章_…`, etc. (or `第一部分/`, `序章/`, `终章/`, `附录/`).
- Each book has a top-level outline file (e.g. `OpenClaw-自进化AI完全指南-大纲.md`). Keep it in sync when section structure changes.

## Git workflow

- Commit messages mix Chinese prose with Conventional Commits prefixes (`feat:`, `docs:`, `chore:`). Examples from history:
  - `feat: 添加OpenClaw完全指南 - 部署方案选型与一键配置`
  - `chore: 清理OpenClaw完全指南内容，重组资料库结构`
  - `docs: 重写 README 使用专业模板`
  - `新增课程: AI赋能投资研究` (a plain Chinese verb prefix is also acceptable)
- The `.gitignore` is intentionally minimal (just `.DS_Store`). Do not add language/tool-specific ignore entries unless the repo actually grows runnable code.

## Obsidian vault

`.obsidian/` contains workspace, plugin, and appearance config for users who open the repo in Obsidian. Do not delete or restructure `.obsidian/` files. When renaming or moving Markdown files, be aware that any `[[wikilinks]]` in other notes may break — Obsidian normally rewrites these, but when editing outside Obsidian you must update references manually.
