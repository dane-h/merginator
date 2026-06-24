# ⚡ Merginator 3000

A local web app for tracking pull requests through an AI-assisted review workflow. Every PR, every step, every safeguard.

---

## The name

In Ratchet & Clank, every weapon has a name that's one part function, one part absurdity. The Groovitron. The Sheepinator. The Merginator 3000 merges PRs. That's the whole pitch.

![Ratchet & Clank grind rail](docs/BataliaMerginator.webp)

---

## What it does

Merginator 3000 gives each PR its own card and walks it through an 11-step workflow — from implementation through AI review, security scanning, senior review, tester review, and merge. It connects to GitHub to detect which step a PR is actually on, checks CI status, and posts the right prompt directly to the PR.

```
1.  Implement Fix
2.  Trigger AI Review
3.  Address Comments
4.  Update PR Description
5.  Post Evidence
6.  Ready to Review         ← Aikido security scan triggers here
7.  Address Aikido Comments
8.  Request Senior Review
9.  Senior Feedback
10. Tester Review
11. Final Gate → 🚀 Merge
```

The pipeline can send you back at any step — CI failures, security scan blocks, reviewer feedback loops. Merginator 3000 tracks all of it.

![Merginator 3000 app screenshot](docs/MerginatorScreenshot.png)

---

## Prerequisites

- Python 3
- A GitHub org with CI checks (GitHub Actions, CircleCI, etc.)
- A GitHub personal access token (classic, `repo` scope)
- Optionally: an issue tracker (Linear, Shortcut, Jira — any URL works) and a workflow doc (Notion, Confluence, etc.)

---

## Setup

```bash
git clone https://github.com/dane-h/merginator.git
cd merginator
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
