"""Run on the active FPSGAME editor bridge to install only the repaired mesh packages and part paths."""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import unreal as ue


def digest(data):
    return hashlib.sha256(data).hexdigest()


def install(batch):
    project = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.get_project_file_path())).resolve().parent
    if project != Path("D:/FPS3D/FPSGAME").resolve():
        raise RuntimeError(f"Unexpected project {project}")
    entries = json.loads((batch / "imported.json").read_text(encoding="utf-8"))
    if len(entries) != 6:
        raise RuntimeError("Missing assembly packages")
    targets = {v["asset"].split(".")[0] for v in entries.values()}
    dirty = [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
    loaded = [r["asset"] for r in entries.values() if ue.find_object(None, r["asset"])]
    prior = json.loads((batch.parent / "RigContactR2_20261122/published.json").read_text(encoding="utf-8-sig"))
    catalog = Path("Content/ColdSteelData/bow-gunsmith.json")
    old_catalog = (project / catalog).read_bytes()
    new_catalog = old_catalog
    writes = []
    recorded = []
    for row in entries.values():
        asset = row["asset"].split(".")[0]
        rel = Path("Content") / (asset.removeprefix("/Game/") + ".uasset")
        path = project / rel
        staged = (batch / "Host" / rel).read_bytes()
        expected = digest(staged)
        old = path.read_bytes() if path.exists() else None
        if old != staged:
            if asset in dirty or row["asset"] in loaded:
                raise RuntimeError(f"Preserve loaded or unsaved package: {asset}")
            if old is not None and digest(old) != prior["files"].get(rel.as_posix(), {}).get("after"):
                raise RuntimeError(f"Package changed since the recorded source: {rel}")
            writes.append((rel, old, staged))
        if row["previous"] != row["asset"]:
            old_ref, new_ref = [json.dumps(row[key]).encode() for key in ("previous", "asset")]
            if new_catalog.count(old_ref) == 1 and new_ref not in new_catalog:
                new_catalog = new_catalog.replace(old_ref, new_ref, 1)
            elif old_ref in new_catalog or new_catalog.count(new_ref) != 1:
                raise RuntimeError(f"Unrecognized catalog reference: {asset}")
        recorded.append({"path":rel.as_posix(), "sha256":expected})
    json.loads(new_catalog.decode("utf-8-sig"))
    if new_catalog != old_catalog:
        writes.append((catalog, old_catalog, new_catalog))
    receipt = {"revision":"CamLinesR11", "packages":recorded, "catalog":catalog.as_posix(),
        "catalog_sha256":digest(new_catalog), "dirty_target_packages":dirty,
        "pie_running":ue.get_editor_subsystem(ue.LevelEditorSubsystem).is_in_play_in_editor(),
        "skeleton":next(iter(entries.values()))["skeleton"], "editor_build":"asset_only",
        "in_game_visual_test":False}
    for rel, old, new in writes:
        path = project / rel
        if (path.read_bytes() if path.exists() else None) != old:
            raise RuntimeError(f"Concurrent modification: {rel}")
        if old is not None:
            backup = batch / "Before" / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                backup.write_bytes(old)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".cam-install", delete=False) as f:
            f.write(new)
            temp = Path(f.name)
        try:
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
    for row in recorded:
        if digest((project / row["path"]).read_bytes()) != row["sha256"]:
            raise RuntimeError("Incomplete package publication: " + row["path"])
    after = batch / "After" / catalog
    after.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project / catalog, after)
    (batch / "published.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
