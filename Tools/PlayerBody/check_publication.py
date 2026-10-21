"""Read-only proof that explicitly selected body routes reached a Git snapshot.

Use --revision :index for the real staged snapshot, or a commit/ref. --remote
reads a branch tip without fetching, staging, committing, pushing, or editing it.
This proves selected config values/source-file presence, not a complete build.
"""
import argparse
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.PIPE)


def snapshot(manifest, prefix):
    try:
        staged = json.loads(git("show", prefix + manifest["config"]).decode("utf-8-sig"))
    except subprocess.CalledProcessError:
        staged = {}
    actual = staged.get("clips", {})
    differences = {k: {"expected": v, "actual": actual.get(k)} for k, v in manifest["roles"].items() if actual.get(k) != v}
    missing_sources = []
    for name in manifest.get("required_source_files", []):
        try:
            git("cat-file", "-e", prefix + name)
        except subprocess.CalledProcessError:
            missing_sources.append(name)
    required_cook = manifest.get("required_cook_directories", [])
    missing_cook = []
    if required_cook:
        try:
            packaging = git("show", prefix + "Config/DefaultGame.ini").decode("utf-8-sig")
        except subprocess.CalledProcessError:
            packaging = ""
        directories = re.findall(r'^\+DirectoriesToAlwaysCook=\(Path="([^"]+)"\)', packaging, re.M)
        missing_cook = [p for p in required_cook if not any(p == d or p.startswith(d.rstrip("/") + "/") for d in directories)]
    return differences, missing_sources, missing_cook


def inspect(manifest, revision, remote=None, branch="main"):
    config = manifest["config"]
    resolved = None if revision == ":index" else git("rev-parse", "--verify", revision + "^{commit}").decode().strip()
    differences, missing_sources, missing_cook = snapshot(manifest, ":" if resolved is None else resolved + ":")
    remote_tip = None
    remote_contains = None
    remote_matches = None
    remote_differences = None
    remote_missing_sources = None
    remote_missing_cook = None
    if remote and resolved:
        output = git("ls-remote", remote, "refs/heads/" + branch).decode().split()
        remote_tip = output[0] if output else None
        if remote_tip == resolved:
            remote_contains = True
            remote_differences, remote_missing_sources, remote_missing_cook = differences, missing_sources, missing_cook
            remote_matches = not remote_differences and not remote_missing_sources and not remote_missing_cook
        elif remote_tip:
            # Do not fetch as a side effect. An unknown tip cannot prove ancestry.
            try:
                git("cat-file", "-e", remote_tip + "^{commit}")
            except subprocess.CalledProcessError:
                remote_contains = None
            else:
                result = subprocess.run(["git", "merge-base", "--is-ancestor", resolved, remote_tip], cwd=ROOT, capture_output=True)
                remote_contains = True if result.returncode == 0 else False if result.returncode == 1 else None
                remote_differences, remote_missing_sources, remote_missing_cook = snapshot(manifest, remote_tip + ":")
                remote_matches = not remote_differences and not remote_missing_sources and not remote_missing_cook
    matches = not differences and not missing_sources and not missing_cook
    return {
        "manifest_scope": manifest.get("scope"), "revision": revision, "commit": resolved,
        "config": config, "expected_roles": len(manifest["roles"]), "different_roles": differences,
        "missing_source_files": missing_sources, "selected_content_in_snapshot": matches,
        "missing_cook_directories": missing_cook,
        "remote": remote, "branch": branch, "remote_tip": remote_tip,
        "remote_contains_revision": remote_contains,
        "selected_content_at_remote_tip": remote_matches,
        "different_remote_roles": remote_differences, "missing_remote_source_files": remote_missing_sources,
        "missing_remote_cook_directories": remote_missing_cook,
        "selected_content_pushed": matches and remote_contains is True and remote_matches is True,
        "asset_binaries_published": None, "build_tested": False, "game_tested": False,
        "proof_limit": "Selected config values and source-file presence only; no source-version/build/asset/visual acceptance proof.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--revision", default=":index")
    parser.add_argument("--remote")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    if not manifest.get("roles"):
        raise ValueError("Manifest must explicitly name the required roles")
    report = inspect(manifest, args.revision, args.remote, args.branch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "expected_roles": report["expected_roles"], "different_roles": len(report["different_roles"]),
        "missing_source_files": len(report["missing_source_files"]),
        "missing_cook_directories": len(report["missing_cook_directories"]),
        "selected_content_in_snapshot": report["selected_content_in_snapshot"],
        "selected_content_pushed": report["selected_content_pushed"], "report": str(args.output),
    }))
    return 0 if report["selected_content_in_snapshot"] and (not args.remote or report["selected_content_pushed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
