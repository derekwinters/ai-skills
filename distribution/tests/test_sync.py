"""Unit tests for the sync engine. Stdlib + PyYAML only.

Run: python -m unittest discover -s distribution/tests -v
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(DIST)
sys.path.insert(0, DIST)

import sync  # noqa: E402


def _make_source(tmp):
    """A tiny fake ai-skills source tree: one static skill, one parametrized
    skill, one agent, one workflow."""
    os.makedirs(os.path.join(tmp, "skills", "ci-watch"))
    with open(os.path.join(tmp, "skills", "ci-watch", "SKILL.md"), "w") as fh:
        fh.write("static skill, no placeholders\n")

    os.makedirs(os.path.join(tmp, "skills", "commit"))
    with open(os.path.join(tmp, "skills", "commit", "SKILL.md"), "w") as fh:
        fh.write("run: {{ config.test_command }}\nscopes: {{ config.commit_scopes }}\n")

    os.makedirs(os.path.join(tmp, "agents"))
    with open(os.path.join(tmp, "agents", "dev.md"), "w") as fh:
        fh.write("verify with: {{ config.verify_command }}\n")

    os.makedirs(os.path.join(tmp, "workflows"))
    with open(os.path.join(tmp, "workflows", "pr-title-lint.yml"), "w") as fh:
        fh.write("name: pr-title-lint\n")


def _registry():
    return {
        "version": 1,
        "defaults": {"install_root": ".claude"},
        "bundles": {
            "core": {"skills": ["ci-watch"]},
            "full": {
                "skills": ["ci-watch", "commit"],
                "agents": ["dev"],
                "workflows": ["pr-title-lint.yml"],
            },
        },
        "repos": {
            "owner/static": {"bundles": ["core"], "config": {}},
            "owner/full": {
                "bundles": ["full"],
                "config": {
                    "test_command": "pytest",
                    "verify_command": "npm run build",
                    "commit_scopes": ["api", "db"],
                },
            },
            "owner/badbundle": {"bundles": ["nope"], "config": {}},
            "owner/missingcfg": {"bundles": ["full"], "config": {}},
        },
    }


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_source(self.tmp)
        self.reg = _registry()

    def test_static_skill_plan(self):
        files = sync.plan(self.reg, "owner/static", self.tmp, ref="v1")
        self.assertIn(".claude/skills/ci-watch/SKILL.md", files)
        self.assertEqual(
            files[".claude/skills/ci-watch/SKILL.md"],
            "static skill, no placeholders\n",
        )
        manifest = json.loads(files[".claude/.skills-manifest.json"])
        self.assertEqual(manifest["ref"], "v1")
        self.assertEqual(manifest["skills"], ["ci-watch"])
        self.assertEqual(manifest["agents"], [])

    def test_parametrized_render(self):
        files = sync.plan(self.reg, "owner/full", self.tmp)
        self.assertEqual(
            files[".claude/skills/commit/SKILL.md"],
            "run: pytest\nscopes: api, db\n",
        )
        self.assertEqual(
            files[".claude/agents/dev.md"], "verify with: npm run build\n"
        )
        # workflows land under .github/workflows/, not the install root
        self.assertIn(".github/workflows/pr-title-lint.yml", files)

    def test_bundle_dedup(self):
        # 'full' lists ci-watch + commit; ci-watch appears once.
        units = sync.resolve_units(self.reg, "owner/full")
        self.assertEqual(units["skills"], ["ci-watch", "commit"])

    def test_unknown_bundle_raises(self):
        with self.assertRaises(KeyError):
            sync.plan(self.reg, "owner/badbundle", self.tmp)

    def test_missing_config_key_raises(self):
        # 'full' renders {{ config.test_command }} but this repo omits it.
        with self.assertRaises(KeyError):
            sync.plan(self.reg, "owner/missingcfg", self.tmp)

    def test_list_repos(self):
        self.assertEqual(len(sync.iter_repos(self.reg)), 4)

    def test_filter_repos(self):
        got = sync._filter_repos(sync.iter_repos(self.reg), "owner/static")
        self.assertEqual(got, ["owner/static"])


class RealRegistryTests(unittest.TestCase):
    """Guard the actual shipped registry + skills: every repo plans cleanly."""

    def test_real_registry_plans_for_every_repo(self):
        reg_path = os.path.join(DIST, "registry.yml")
        reg = sync.load_registry(reg_path)
        for repo in sync.iter_repos(reg):
            files = sync.plan(reg, repo, REPO_ROOT, ref="test")
            self.assertTrue(files, f"{repo} produced no files")
            self.assertIn(".claude/.skills-manifest.json", files)


if __name__ == "__main__":
    unittest.main()
