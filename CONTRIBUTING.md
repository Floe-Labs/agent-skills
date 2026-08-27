# Contributing to Floe agent skills

Thanks for improving Floe's agent skills. This repo is a small, curated set of
[Agent Skills](https://www.anthropic.com/news/skills) — each one teaches an agent to do
something real with Floe, and each one must be accurate against the live product.

## Principles

- **One skill, one job.** A skill has a clear trigger (its `description`) and a focused
  playbook. If it's doing two unrelated things, it's two skills.
- **Accurate over aspirational.** Every endpoint, schema, price, and limit must match
  the shipped product. Don't document features that aren't live; if something is
  planned, say so explicitly (or leave it out).
- **Grounded.** Prefer canonical sources of truth (`GET /v1/models` for the catalog,
  the API's own schemas) over frozen copies that drift.
- **Self-contained.** A skill lives in `skills/<name>/` with `SKILL.md` at its root and
  any supporting docs under `references/`.

## Skill structure

```
skills/<name>/
  SKILL.md            # required — YAML frontmatter (name, description) + the playbook
  references/*.md     # optional — deep-dive docs the skill points to
```

`SKILL.md` frontmatter must have at least:

```yaml
---
name: <kebab-case-name>
description: >
  One or more sentences describing WHEN to use this skill (triggers), so the client
  can route to it. Be specific about the situations that should invoke it.
---
```

CI validates that every `skills/*/SKILL.md` has valid frontmatter with a non-empty
`name` and `description`.

## Making a change

1. Fork + branch.
2. Edit or add a skill. Keep line-level claims traceable to the product.
3. Run the check locally if you like: `python3 .github/validate_skills.py`.
4. Open a PR describing what changed and how you verified it against the live product.

## Reporting problems

- Inaccuracy or bug in a skill → open a [Bug issue](../../issues/new?template=bug_report.md).
- Idea for a new skill → open a [Feature issue](../../issues/new?template=feature_request.md).
- Security issue → email **hello@floefinance.com**, do not open a public issue.
