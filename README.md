# ⚡ GrindRail

A local web app for tracking pull requests through an AI-assisted review workflow. Hit the wrong rail and CI sends you back to the start.

Built for people who run multiple PRs at once and lose track of where each one is up to.

---

## The name

In Ratchet & Clank, grind rails are the rails you jump onto and ride through a level. Pick the wrong one and you're sent back to the beginning.

![Ratchet & Clank grind rail](docs/grindrail-ratchet.png)

That's CI. You're flying through the pipeline, take the wrong path, and suddenly you're back at step one. GrindRail keeps you on the right rail.

---

## What it does

GrindRail gives each PR its own card and walks it through an 8-step workflow — from implementation through AI review, senior review, and merge. It connects to GitHub to detect which step a PR is actually on, checks CI status, and posts the four-angle review prompt directly to the PR.

```
1. Implement Fix
2. Trigger AI Review
3. Address Comments
4. Update PR Description
5. Post Evidence
6. Request Senior Review   ← security scan runs here
7. Senior Feedback
8. Final Gate → 🚀 Merge
```

CI can interrupt at any step. GrindRail tracks that too.

![GrindRail app screenshot](docs/screenshot.png)

---

## Prerequisites

- Python 3
- A GitHub org with CI checks (GitHub Actions, CircleCI, etc.)
- A GitHub personal access token (classic, `repo` scope)
- Optionally: an issue tracker (Linear, Shortcut, Jira — any URL works) and a workflow doc (Notion, Confluence, etc.)

---

## Setup

```bash
git clone https://github.com/dane-h/grindrail.git
cd grindrail
```

Then either double-click `start.command` or:

```bash
python3 server.py
```

Opens at `http://localhost:8767`.

On first launch, open **Settings** (⚙) and enter:
- **GitHub token** — classic PAT with `repo` scope
- **Workflow doc URL** — optional link to your team's workflow doc, shown in the Flow modal

---

## Stack

- Python 3 stdlib HTTP server — no dependencies
- Single HTML file, vanilla JS, no build step
- State persisted to `data/state.json`
- GitHub REST API for PR details, CI checks, and posting comments

---

## Notes

- `data/` is gitignored — your token and PR state stay local; see `config.example.json` for the expected shape
- Designed to run locally, not deployed
