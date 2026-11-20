"""Install one staged package while holding the existing editor batch lock."""
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FACE = ROOT / "SourceAssets/VillageHerbalist/FullBody/FaceR2"
NAME = "SK_VillageHerbalist"
PACKAGE = "/Game/Characters/VillageHerbalist/" + NAME
RELATIVE = Path("Content/Characters/VillageHerbalist") / (NAME + ".uasset")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_from(source, target):
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    shutil.copyfile(source, temporary)
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def publish(work, editor):
    work = Path(work)
    source = FACE / (NAME + ".fbx")
    job = json.loads((work / "job.json").read_text(encoding="utf-8-sig"))
    staged = json.loads((work / "staged.json").read_text())
    target = ROOT / RELATIVE
    dependencies = {target: job["mesh"], target.with_name(NAME + "_Skeleton.uasset"): job["skeleton"],
                    source: job["fbx"], FACE / "mesh-ready.json": job["ready"]}
    for path, expected in dependencies.items():
        if digest(path) != expected.lower():
            raise RuntimeError(f"Production input changed while staging: {path}")
    package = None
    if editor:
        import unreal as ue
        if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() != ROOT:
            raise RuntimeError("The selected editor is not the FPSGAME project")
        if ue.EditorLevelLibrary.get_pie_worlds(False):
            raise RuntimeError("PIE is active. The mesh package has not been changed")
        dirty = {p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        conflicts = dirty.intersection({PACKAGE, PACKAGE + "_Skeleton"})
        if conflicts:
            raise RuntimeError(f"Unsaved target mesh or skeleton in editor: {sorted(conflicts)}")
        package = ue.find_package(PACKAGE)
        if package:
            ue.EditorLoadingAndSavingUtils.fully_load_packages([package])
    loaded = package is not None
    backup = work / "previous-mesh.uasset"
    shutil.copyfile(target, backup)
    staged_asset = work / RELATIVE
    replace_from(staged_asset, target)
    if editor:
        if loaded:
            def reload_one(pkg):
                changed, message = ue.EditorLoadingAndSavingUtils.reload_packages(
                    [pkg], ue.ReloadPackagesInteractionMode.ASSUME_NEGATIVE)
                if not changed or str(message):
                    raise RuntimeError(f"Mesh package reload returned {changed}, {message}")

            try:
                reload_one(package)
            except Exception:
                current = ue.find_package(PACKAGE)
                if current:
                    ue.EditorLoadingAndSavingUtils.fully_load_packages([current])
                replace_from(backup, target)
                if current:
                    reload_one(current)
                raise
        else:
            ue.AssetRegistryHelpers.get_asset_registry().scan_modified_asset_files([str(target)])
    staged.update({"package": PACKAGE, "fbx_sha256": job["fbx"].lower(),
                   "package_sha256": digest(target), "previous_package_sha256": job["mesh"].lower(),
                   "existing_editor": editor, "reloaded_in_editor": loaded, "work": str(work)})
    output = json.dumps(staged, ensure_ascii=False, indent=2)
    (work / "published.json").write_text(output, encoding="utf-8")
    temporary = FACE / ("mesh_delivery." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(output, encoding="utf-8")
    os.replace(temporary, FACE / "mesh_delivery.json")
    print("Saved", PACKAGE, staged["package_sha256"])
