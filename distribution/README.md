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

## Distribution: pull, not push ("Dependabot for skills")

Each consumer repo runs its **own** scheduled workflow that checks `ai-skills`
for the latest release, renders the skills it subscribes to, and opens a PR **in
itself**. Nothing pushes in from a central place; `ai-skills` never touches the
other repos.

| Workflow | Lives in | Trigger | What it does |
|---|---|---|---|
| `workflows/skills-update.yml` | installed into **each consumer repo** | weekly cron (+ manual) | Pull latest `ai-skills`, render this repo's skills, open/update a PR **in this repo** using its own `GITHUB_TOKEN`. |
| `.github/workflows/skills-tests.yml` | `ai-skills` | PR / push | Engine tests + a guard that every repo in `registry.yml` plans cleanly. |

`workflows/skills-update.yml` is itself in the `core` bundle, so every repo
installs its own updater and it self-perpetuates. Nothing is force-applied —
every change lands as a PR a human reviews and merges.

## Setup required (one-time, human, per consumer repo)

- Enable Settings → Actions → General → **"Allow GitHub Actions to create and
  approve pull requests"** (so the repo's own token can open its self-PR).
- If `ai-skills` is **private**, add a read-only **`AI_SKILLS_READ_TOKEN`**
  secret (scoped to read `ai-skills` only) so the workflow can check it out. If
  `ai-skills` is public, no token is needed.
- Bootstrap: add `workflows/skills-update.yml` to the repo once (after that it
  keeps itself updated). Tracked in the rollout epic.

No cross-repo write token is needed anywhere.

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
