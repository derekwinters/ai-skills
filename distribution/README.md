# Distribution — repo config as code

`ai-skills` is the source of truth for the shared AI development pattern
(skills, agents, and pattern workflows). This directory is how that source of
truth gets **installed into** and **kept in sync with** the consumer repos —
without hand-copying and without drift.

## The model

- **`registry.yml`** is the single declarative config. It defines:
  - **bundles** — named sets of installable units (`skills` / `agents` /
    `workflows`), and
  - **repos** — which bundles each consumer repo installs, plus that repo's
    per-repo **`config`** values.
- **`sync.py`** is a pure, unit-tested engine. `plan(registry, repo, source)`
  returns the exact set of files that repo should contain, rendering each
  skill's `{{ config.KEY }}` placeholders from that repo's config — so we ship
  **one skill body, not N forks**. The only per-repo axis is the config block
  (test/verify commands, areas, commit scopes, requirement-ID prefix).
- **`schema/`** — JSON Schema for `registry.yml` and the per-repo config.

## The two workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `.github/workflows/skills-sync.yml` | manual / reusable | Install/update one repo or a list. Renders skills from the registry and **opens a PR** per repo that drifted. This is the "install" path. |
| `.github/workflows/skills-update.yml` | weekly cron (+ manual) | Runs `skills-sync` across **all** repos — the `gh skill update --all` equivalent. Fan-out is just "merge a change here and wait for Monday." |
| `.github/workflows/skills-tests.yml` | PR / push | Runs the engine tests + a guard that every repo in `registry.yml` plans cleanly. |

Nothing is force-applied to consumer repos: every change arrives as a PR a
human reviews and merges.

## Setup required (one-time, human)

- A token with `repo` + `workflow` scope on the consumer repos, stored as the
  **`SKILLS_SYNC_TOKEN`** secret in this repo. The built-in `GITHUB_TOKEN`
  cannot push to sibling repos. (Tracked in the rollout epic.)

## Using it

```bash
# List target repos
python distribution/sync.py --registry distribution/registry.yml --list-repos

# Preview what a repo would receive
python distribution/sync.py --registry distribution/registry.yml \
  --repo derekwinters/chores-web-backend --source . --print

# Render into a checkout (what the workflow does)
python distribution/sync.py --registry distribution/registry.yml \
  --repo derekwinters/chores-web-backend --source . --out /path/to/checkout --ref v0.1.0
```

## Relationship to `gh skill`

The workflow's render step is deliberately implemented in `sync.py` so it works
today with no external dependency. If the `gh skill` extension is adopted, that
one step can be swapped for `gh skill install` / `gh skill update` — the
registry stays the source of truth. (Confirming `gh skill`'s availability is
tracked in the rollout epic.)
