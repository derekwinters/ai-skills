# ai-skills

The source of truth for the shared AI development pattern across
[Derek's](https://github.com/derekwinters) repos — skills, agent templates, and
the workflows that distribute them.

The full standardization plan is
**[issue #1](https://github.com/derekwinters/ai-skills/issues/1)**; rollout work
is tracked in the rollout epic.

## Layout

```
skills/          canonical skills (installed into consumer repos)
agents/          agent templates (the unified dev agent, orchestrators)   [planned]
workflows/       reusable GH workflow snippets to distribute              [planned]
distribution/    repo-config-as-code: registry.yml + sync.py + schema + tests
  └─ README.md   how install / weekly-update works
.github/workflows/
  skills-sync.yml     install/update repos from the registry (opens PRs)
  skills-update.yml   weekly fan-out across all repos
  skills-tests.yml    CI for the engine + registry
```

## How it works

`distribution/registry.yml` declares which repos install which bundles of
skills, plus each repo's per-repo config. `distribution/sync.py` renders the
canonical skills (substituting `{{ config.KEY }}` per repo) and the workflows
open a PR in each consumer repo. One skill body, many repos, no drift. See
[`distribution/README.md`](distribution/README.md).
