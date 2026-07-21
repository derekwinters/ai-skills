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

    def test_optional_placeholder_renders_empty_when_absent(self):
        # required {{ config.k }} errors on absence, optional {{ config.k? }}
        # renders to empty string (and null renders empty too).
        self.assertEqual(sync.render("a{{ config.x? }}b", {}), "ab")
        self.assertEqual(sync.render("a{{ config.x? }}b", {"x": None}), "ab")
        self.assertEqual(sync.render("a{{ config.x? }}b", {"x": "Z"}), "aZb")
        with self.assertRaises(KeyError):
            sync.render("a{{ config.x }}b", {})

    def test_missing_config_key_raises(self):
        # 'full' renders {{ config.test_command }} but this repo omits it.
        with self.assertRaises(KeyError):
            sync.plan(self.reg, "owner/missingcfg", self.tmp)

    def test_optional_placeholder_renders_when_present(self):
        self.assertEqual(
            sync.render("run: {{ config.test_command? }}",
                        {"test_command": "pytest"}),
            "run: pytest",
        )

    def test_optional_placeholder_empty_when_absent(self):
        # `{{ config.KEY? }}` renders empty rather than raising when absent.
        self.assertEqual(
            sync.render("run: {{ config.test_command? }}!", {}),
            "run: !",
        )

    def test_required_placeholder_still_raises_when_absent(self):
        with self.assertRaises(KeyError):
            sync.render("run: {{ config.test_command }}", {})

    def test_list_repos(self):
        self.assertEqual(len(sync.iter_repos(self.reg)), 4)

    def test_filter_repos(self):
        got = sync._filter_repos(sync.iter_repos(self.reg), "owner/static")
        self.assertEqual(got, ["owner/static"])


class RenderTests(unittest.TestCase):
    def test_required_present(self):
        self.assertEqual(sync.render("x {{ config.a }}", {"a": "1"}), "x 1")

    def test_required_missing_raises(self):
        with self.assertRaises(KeyError):
            sync.render("x {{ config.a }}", {})

    def test_optional_present(self):
        self.assertEqual(sync.render("x {{ config.a? }}", {"a": "1"}), "x 1")

    def test_optional_missing_is_empty(self):
        self.assertEqual(sync.render("x{{ config.a? }}y", {}), "xy")

    def test_list_value_joined(self):
        self.assertEqual(sync.render("{{ config.a }}", {"a": ["p", "q"]}), "p, q")


class RealRegistryTests(unittest.TestCase):
    """Guard the actual shipped registry + skills: every repo plans cleanly."""

    def setUp(self):
        self.reg = sync.load_registry(os.path.join(DIST, "registry.yml"))

    def test_real_registry_plans_for_every_repo(self):
        for repo in sync.iter_repos(self.reg):
            files = sync.plan(self.reg, repo, REPO_ROOT, ref="test")
            self.assertTrue(files, f"{repo} produced no files")
            self.assertIn(".claude/.skills-manifest.json", files)

    def test_triage_bundle_units(self):
        units = sync.resolve_units(self.reg, "derekwinters/chores-web-backend")
        for skill in [
            "github-issue-categorize",
            "github-issue-find-duplicates",
            "github-issue-validate-bug",
            "github-issue-validate-feature",
            "github-issue-validate-refactor",
            "github-issue-completeness",
            "github-issue-label",
            "github-issue-suggest-milestone",
            "github-issue-review",
            "grill-with-docs",
        ]:
            self.assertIn(skill, units["skills"])
        for agent in [
            "github-issue-triage-orchestrator",
            "github-issue-implementation-orchestrator",
            "milestone-implementation-orchestrator",
        ]:
            self.assertIn(agent, units["agents"])
        # Deprecated skill must not ship.
        self.assertNotIn("github-issue-plan", units["skills"])

    def test_grill_renders_repo_areas(self):
        # grill-with-docs is the one parametrized triage skill: its Area
        # Checklist must render this repo's config.areas, leaving no placeholder.
        files = sync.plan(self.reg, "derekwinters/chores-web-android", REPO_ROOT)
        grill = files[".claude/skills/grill-with-docs/SKILL.md"]
        self.assertNotIn("{{ config", grill)
        self.assertIn("data, network, domain", grill)  # android's areas, comma-joined

    def test_review_uses_ready_to_grill_not_ready_to_plan(self):
        files = sync.plan(self.reg, "derekwinters/chores-web-backend", REPO_ROOT)
        review = files[".claude/skills/github-issue-review/SKILL.md"]
        self.assertIn("ready-to-grill", review)
        self.assertNotIn("ready-to-plan", review)

    def test_actions_repo_not_subscribed_to_triage(self):
        units = sync.resolve_units(self.reg, "derekwinters/chores-web-actions")
        self.assertNotIn("grill-with-docs", units["skills"])
        # Gets the universal `dev` agent (core) but not the triage orchestrators.
        self.assertIn("dev", units["agents"])
        self.assertNotIn("github-issue-triage-orchestrator", units["agents"])

    def test_dev_agent_universal(self):
        for repo in sync.iter_repos(sync.load_registry(
                os.path.join(DIST, "registry.yml"))):
            units = sync.resolve_units(sync.load_registry(
                os.path.join(DIST, "registry.yml")), repo)
            self.assertIn("dev", units["agents"], f"{repo} missing dev agent")


if __name__ == "__main__":
    unittest.main()
