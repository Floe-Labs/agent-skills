#!/usr/bin/env python3
"""Validate every skills/*/SKILL.md has valid frontmatter with a name + description.

Mirrors what public skill directories check when they index a repo. Run locally with
`python3 .github/validate_skills.py`; CI runs it on every push / PR.
"""
import glob
import sys

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

errors: list[str] = []
paths = sorted(glob.glob("skills/*/SKILL.md"))
if not paths:
    errors.append("no skills/*/SKILL.md found")

for path in paths:
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---"):
        errors.append(f"{path}: missing YAML frontmatter")
        continue
    parts = text.split("---", 2)
    if len(parts) < 3:
        errors.append(f"{path}: unterminated frontmatter")
        continue
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        errors.append(f"{path}: invalid YAML ({exc})")
        continue
    for key in ("name", "description"):
        if not str(fm.get(key, "")).strip():
            errors.append(f"{path}: frontmatter missing non-empty '{key}'")
    print(f"checked {path}")

if errors:
    print("\nVALIDATION FAILED:", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    sys.exit(1)

print(f"\nOK — {len(paths)} skill(s) valid")
