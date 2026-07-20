# REPLACE-ME

Welcome to the documentation site for **REPLACE-ME**.

This site is built with [MkDocs](https://www.mkdocs.org/) +
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) and is the
place where this project's design and requirements are decided and recorded.

## Spec-driven development

Behavior is specified as **requirement rows** in
[`spec/requirements.md`](spec/requirements.md):

```
| AREA-NNN | short description | auto |
```

The third column is the verification tag — `auto` (an automated test covers it),
`manual` (a human verifies it), or `planned` (specced, not built yet). The
`validate-specs` skill enforces that every `auto` requirement is referenced by a
real test, that IDs are unique, and that doc links resolve.

## Building locally

```bash
pip install -r docs/requirements.txt
mkdocs serve      # live preview at http://127.0.0.1:8000
mkdocs build --strict   # what CI runs
```
