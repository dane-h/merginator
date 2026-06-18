# ⚡ GrindRail

A local web app for tracking pull requests through an AI-assisted review workflow. Hit the wrong rail and CI sends you back to the start.

Built for people who run multiple PRs at once and lose track of where each one is up to.

---

## What it does

GrindRail gives each PR its own card and walks it through an 8-step workflow — from implementation through AI review, senior review, and merge. It connects to GitHub to detect which step a PR is actually on, checks CI status, and posts the four-angle review prompt directly to the PR.

```
1. Implement Fix
2. Trigger AI Review
3. Address Comments
4. Update PR Description
5. Evidence → Linear
6. Request Senior Review   ← security scan runs here
7. Senior Feedback
8. Final Gate → 🚀 Merge
```

CI can interrupt at any step. GrindRail tracks that too.

---

## Setup

**Requirements:** Python 3, a GitHub personal access token (classic, `repo` scope)

```bash
git clone https://github.com/deskpro/qa-tools.git
cd qa-tools
```

Then either double-click `start.command` or:

```bash
python3 server.py
```

Opens at `http://localhost:8767`.

On first launch, open **Settings** (⚙) and enter:
- **GitHub token** — classic PAT with `repo` scope
- **Linear workspace** — the slug from `linear.app/{workspace}/...`
- **Workflow doc URL** — optional link to your team's workflow doc (e.g. a Notion page), shown in the Flow modal

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
- Named after the grind rails in Ratchet & Clank. Pick the wrong one and you're back at the beginning.
