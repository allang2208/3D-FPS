"""Explicit regression review in disposable local Git repos; no project Git writes."""
import json
from pathlib import Path
import runpy
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    api = runpy.run_path(str(ROOT / "Tools/PlayerBody/check_publication.py"))
    inspect = api["inspect"]
    results = []
    with tempfile.TemporaryDirectory(prefix="fps-publication-review-") as name:
        root = Path(name)
        repo, remote = root / "work", root / "remote.git"
        repo.mkdir()

        def git(*args):
            return subprocess.check_output(["git", "-c", "user.name=OfflineReview", "-c", "user.email=review@invalid", *args], cwd=repo, stderr=subprocess.PIPE).decode().strip()

        git("init", "-b", "main")
        git("init", "--bare", str(remote))
        git("remote", "add", "origin", str(remote))
        api["inspect"].__globals__["ROOT"] = repo
        config = repo / "Content/ColdSteelData/player_body.json"
        config.parent.mkdir(parents=True)
        source = repo / "Source/Hammer.h"
        source.parent.mkdir()
        source.write_text("// isolated source fixture\n", encoding="utf-8")
        manifest = {"config": "Content/ColdSteelData/player_body.json", "roles": {"Warhammer.Idle": "/Game/A.A"}, "required_source_files": ["Source/Hammer.h"]}

        def commit(data, message):
            config.write_text(json.dumps(data), encoding="utf-8")
            git("add", "--", "Content/ColdSteelData/player_body.json", "Source/Hammer.h")
            git("commit", "-m", message)
            git("push", "origin", "HEAD:main")
            return git("rev-parse", "HEAD")

        base = commit({"clips": manifest["roles"]}, "complete routes")
        assert inspect(manifest, base, "origin")["selected_content_pushed"]
        results.append("exact remote tip proves selected content")
        assert inspect(manifest, ":index")["selected_content_in_snapshot"]
        results.append("index comparison uses actual staged content")
        commit({"clips": manifest["roles"], "other": True}, "unrelated edit")
        assert inspect(manifest, base, "origin")["selected_content_pushed"]
        results.append("later unrelated commit retains publication proof")
        commit({"clips": {}}, "regression deletes routes")
        failed = inspect(manifest, base, "origin")
        assert failed["remote_contains_revision"] and not failed["selected_content_pushed"]
        assert "Warhammer.Idle" in failed["different_remote_roles"]
        results.append("ancestor in remote history cannot hide later route removal")
        source.unlink()
        commit({"clips": manifest["roles"]}, "missing source")
        failed = inspect(manifest, base, "origin")
        assert not failed["selected_content_pushed"] and failed["missing_remote_source_files"] == ["Source/Hammer.h"]
        results.append("restored routes without required source do not pass")
        cook_manifest = dict(manifest, required_source_files=[], required_cook_directories=["/Game/Hammer/Animations"])
        assert inspect(cook_manifest, "HEAD", "origin")["missing_cook_directories"] == ["/Game/Hammer/Animations"]
        packaging = repo / "Config/DefaultGame.ini"
        packaging.parent.mkdir()
        packaging.write_text('[/Script/UnrealEd.ProjectPackagingSettings]\n+DirectoriesToAlwaysCook=(Path="/Game/Hammer/Animations")\n', encoding="utf-8")
        git("add", "--", "Config/DefaultGame.ini")
        git("commit", "-m", "add cook rule")
        git("push", "origin", "HEAD:main")
        assert inspect(cook_manifest, "HEAD", "origin")["selected_content_pushed"]
        results.append("dynamic animation dependencies require explicit cook coverage")
    out = ROOT / "Saved/AnimationHandoffReview20261021/publication-tool.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {"passed": len(results), "cases": results, "real_project_git_written": False, "external_remote_written": False}
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
