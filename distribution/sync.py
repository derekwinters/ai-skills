#!/usr/bin/env python3
"""Repo-config-as-code sync engine for ai-skills.

`distribution/registry.yml` is the single source of truth: it declares
*bundles* (named sets of skills / agents / workflows) and *repos* (which
bundles each consumer repo installs, plus that repo's per-repo config values).

`plan(registry, repo, source_root)` is a **pure** function: given the registry,
a repo name, and a checkout of this repo, it returns a dict of
``{path-in-consumer-repo: file-content}`` — the exact set of files that repo
should contain, with each skill's `{{ config.KEY }}` placeholders rendered from
that repo's config block. No network, no git, no clock — so it is trivially
unit-tested (see ``tests/test_sync.py``).

The CLI wraps it for the GitHub Actions workflows (``skills-sync.yml`` /
``skills-update.yml``):

    sync.py --registry registry.yml --list-repos --json [--filter all|a,b]
    sync.py --registry registry.yml --repo owner/name --source . --out DIR --ref REF
    sync.py --registry registry.yml --repo owner/name --source . --print

Only PyYAML is required. If a repo adopts the `gh skill` extension instead,
the render step in the workflow can be swapped for `gh skill install`; the
registry stays the source of truth either way.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import yaml

# `{{ config.KEY }}` is required (missing -> error); `{{ config.KEY? }}` is
# optional (missing or null -> empty string). Optional placeholders let a
# shared skill body carry per-repo values that only some repos set.
PLACEHOLDER = re.compile(r"\{\{\s*config\.([a-zA-Z0-9_]+)(\?)?\s*\}\}")
# Files we render placeholders in; anything else is copied byte-for-byte.
TEXT_SUFFIXES = (".md", ".txt", ".py", ".json", ".yml", ".yaml", ".sh", ".toml")
MANIFEST_NAME = ".skills-manifest.json"


def load_registry(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "repos" not in data:
        raise ValueError("registry must be a mapping with a top-level 'repos' key")
    return data


def iter_repos(registry):
    return list(registry.get("repos", {}).keys())


def _render_value(value):
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def render(text, config, *, where=""):
    """Substitute ``{{ config.KEY }}`` (required) and ``{{ config.KEY? }}``
    (optional → empty when absent) from ``config``; error on a missing
    required key."""
    def repl(match):
        key = match.group(1)
        optional = match.group(2) == "?"
        if key not in config or config[key] is None:
            if optional:
                return ""
            raise KeyError(
                f"{where}: references config.{key} but the repo has no such config value"
            )
        return _render_value(config[key])

    return PLACEHOLDER.sub(repl, text)


def resolve_units(registry, repo):
    """Merge the repo's bundles into a deduped set of skills/agents/workflows."""
    repos = registry.get("repos", {})
    if repo not in repos:
        raise KeyError(f"repo '{repo}' is not in the registry")
    bundles = registry.get("bundles", {})
    out = {"skills": [], "agents": [], "workflows": []}
    seen = {"skills": set(), "agents": set(), "workflows": set()}
    for bundle_name in repos[repo].get("bundles", []):
        if bundle_name not in bundles:
            raise KeyError(
                f"repo '{repo}' requests unknown bundle '{bundle_name}'"
            )
        bundle = bundles[bundle_name] or {}
        for kind in out:
            for unit in bundle.get(kind, []) or []:
                if unit not in seen[kind]:
                    seen[kind].add(unit)
                    out[kind].append(unit)
    return out


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _walk_files(root):
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            full = os.path.join(dirpath, name)
            yield full, os.path.relpath(full, root)


def plan(registry, repo, source_root, *, ref="local"):
    """Return {consumer_path: content} for `repo`. Pure — no I/O beyond reading
    the source skill/agent/workflow files under `source_root`."""
    cfg = registry["repos"][repo].get("config", {}) or {}
    install_root = registry.get("defaults", {}).get("install_root", ".claude")
    units = resolve_units(registry, repo)
    files = {}

    # Skills: skills/<name>/** -> <install_root>/skills/<name>/**
    for skill in units["skills"]:
        sdir = os.path.join(source_root, "skills", skill)
        if not os.path.isdir(sdir):
            raise FileNotFoundError(f"skill '{skill}' not found under {sdir}")
        for full, rel in _walk_files(sdir):
            dest = f"{install_root}/skills/{skill}/{rel}".replace(os.sep, "/")
            files[dest] = _maybe_render(full, cfg, dest)

    # Agents: agents/<name>.md -> <install_root>/agents/<name>.md
    for agent in units["agents"]:
        src = os.path.join(source_root, "agents", f"{agent}.md")
        if not os.path.isfile(src):
            raise FileNotFoundError(f"agent '{agent}' not found at {src}")
        dest = f"{install_root}/agents/{agent}.md"
        files[dest] = _maybe_render(src, cfg, dest)

    # Workflows: workflows/<file> -> .github/workflows/<file>
    for wf in units["workflows"]:
        src = os.path.join(source_root, "workflows", wf)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"workflow '{wf}' not found at {src}")
        dest = f".github/workflows/{wf}"
        files[dest] = _maybe_render(src, cfg, dest)

    # Manifest so `update` and humans can see what's installed and from where.
    manifest = {
        "source": "derekwinters/ai-skills",
        "ref": ref,
        "bundles": registry["repos"][repo].get("bundles", []),
        "skills": units["skills"],
        "agents": units["agents"],
        "workflows": units["workflows"],
    }
    files[f"{install_root}/{MANIFEST_NAME}"] = json.dumps(manifest, indent=2) + "\n"
    return files


def _maybe_render(full_path, cfg, dest):
    raw = _read(full_path)
    if dest.endswith(TEXT_SUFFIXES):
        text = raw.decode("utf-8")
        return render(text, cfg, where=dest)
    return raw  # bytes, copied as-is


def _write_plan(files, out_root):
    written = []
    for rel, content in sorted(files.items()):
        dest = os.path.join(out_root, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        mode = "w" if isinstance(content, str) else "wb"
        with open(dest, mode, encoding="utf-8" if mode == "w" else None) as fh:
            fh.write(content)
        written.append(rel)
    return written


def _filter_repos(all_repos, spec):
    if not spec or spec == "all":
        return all_repos
    wanted = [r.strip() for r in spec.split(",") if r.strip()]
    return [r for r in all_repos if r in wanted]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--repo")
    ap.add_argument("--source", default=".")
    ap.add_argument("--out")
    ap.add_argument("--ref", default="local")
    ap.add_argument("--list-repos", action="store_true")
    ap.add_argument("--filter", default="all")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--print", dest="do_print", action="store_true")
    args = ap.parse_args(argv)

    registry = load_registry(args.registry)

    if args.list_repos:
        repos = _filter_repos(iter_repos(registry), args.filter)
        sys.stdout.write(json.dumps(repos) if args.json else "\n".join(repos))
        sys.stdout.write("\n" if not args.json else "")
        return 0

    if not args.repo:
        ap.error("--repo is required unless --list-repos is given")

    files = plan(registry, args.repo, args.source, ref=args.ref)

    if args.do_print or not args.out:
        for rel in sorted(files):
            print(rel)
        return 0

    written = _write_plan(files, args.out)
    print(f"Synced {len(written)} file(s) for {args.repo} into {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
