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
workflows/       workflows distributed into consumer repos (skills-update.yml)
distribution/    repo-config-as-code: registry.yml + sync.py + schema + tests
  └─ README.md   how the pull-based update works
.github/workflows/
  skills-tests.yml    CI for the engine + registry
```

## How it works (pull model — "Dependabot for skills")

`distribution/registry.yml` declares which repos install which bundles of
skills, plus each repo's per-repo config. Each consumer repo runs its **own**
`skills-update.yml` on a schedule: it pulls the latest `ai-skills`, renders its
skills via `distribution/sync.py` (substituting `{{ config.KEY }}` per repo),
and opens a PR **in itself** using its own token. `ai-skills` never pushes into
other repos. One skill body, many repos, no drift. See
[`distribution/README.md`](distribution/README.md).
