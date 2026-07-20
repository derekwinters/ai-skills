# Starter docs scaffold

A minimal [MkDocs](https://www.mkdocs.org/) +
[Material](https://squidfunk.github.io/mkdocs-material/) site a repo can adopt so
it has a documentation site the `docs-test` gate (from the ai-skills `spec`
bundle) can build with `mkdocs build --strict`.

## Adopt it

From the target repo root:

1. Copy `mkdocs.yml` to the repo root.
2. Copy the `docs/` folder to the repo root.
3. Optionally copy `docs-publish.yml` to `.github/workflows/docs-publish.yml`
   and enable **Settings → Pages → Source: GitHub Actions** to publish to
   GitHub Pages.
4. Replace every `REPLACE-ME` placeholder in `mkdocs.yml` and `docs/index.md`.
5. Verify locally:

   ```bash
   pip install -r docs/requirements.txt
   mkdocs build --strict
   ```

## What's here

| File | Goes to | Purpose |
|------|---------|---------|
| `mkdocs.yml` | repo root | MkDocs + Material config |
| `docs/index.md` | repo root | site landing page |
| `docs/spec/requirements.md` | repo root | starter requirement table |
| `docs/requirements.txt` | repo root | pinned MkDocs deps CI installs |
| `docs-publish.yml` | `.github/workflows/` | optional GitHub Pages deploy |

The `docs-test` workflow itself is installed automatically by the `spec`
bundle — you do not copy it from here.
