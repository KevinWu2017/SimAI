#!/usr/bin/env python3
"""Check official ancestry and upstream file preservation for the HBF checkouts.

Offline by default. --check-remote also compares the pinned bases with official
master at execution time; a newer upstream head fails the check explicitly.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

SPECS = (
    ("SimAI", ".", "a57d765c5478f319c5f5ab6fdc53f9cc7f461743", {".gitmodules", "aicb", "README.md"}),
    ("aicb", "aicb", "23eec3c48ca2d2d93dd888a4c7b22ab4421e782f", {"README.md"}),
)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True,
                                   stderr=subprocess.PIPE, timeout=45).strip()


def check(root, *, check_remote=False, ssh=False, require_clean=False):
    results = []
    for name, relative, base, allowed in SPECS:
        path = root / relative
        row = dict(repository=name, official_base=base, official_branch="master")
        try:
            row["head"] = git(path, "rev-parse", "HEAD")
            git(path, "merge-base", "--is-ancestor", base, "HEAD")
            row["official_base_is_ancestor"] = True
            # Added HBF files are allowed. Changes/deletions of official files
            # must be confined to the explicit integration points above.
            changed = git(path, "diff", "--name-only", "--diff-filter=MDRT", base, "HEAD").splitlines()
            row["upstream_file_overrides"] = changed
            unexpected = sorted(set(changed) - allowed)
            row["unexpected_upstream_file_changes"] = unexpected
            if require_clean:
                row["tracked_worktree_changes"] = git(path, "status", "--porcelain", "--untracked-files=no")
            if check_remote:
                url = (f"git@github.com:aliyun/{name}.git" if ssh
                       else f"https://github.com/aliyun/{name}.git")
                remote = git(path, "ls-remote", url, "refs/heads/master")
                row["official_remote_head"] = remote.split()[0]
                row["matches_current_official_master"] = row["official_remote_head"] == base
            row["passed"] = (not unexpected and not row.get("tracked_worktree_changes")
                             and row.get("matches_current_official_master", True))
        except (subprocess.SubprocessError, OSError, IndexError) as exc:
            row.update(passed=False, error=str(exc))
        results.append(row)
    return dict(passed=all(r["passed"] for r in results), repositories=results,
                scope="official parent/AICB master ancestry and tracked source preservation; not a functional test")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check-remote", action="store_true")
    parser.add_argument("--github-ssh", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    result = check(args.root.resolve(), check_remote=args.check_remote,
                   ssh=args.github_ssh, require_clean=args.require_clean)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
