"""Publish the supplied revision directly into the texture objects used by the runtime mesh."""
import hashlib
import json
from pathlib import Path

import unreal as ue


ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "Saved/HerbalistFaceReview"
INPUT = ROOT / "SourceAssets/VillageHerbalist/FullBody/FaceR2"
MESH = "/Game/Characters/VillageHerbalist/SK_VillageHerbalist"
if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() != ROOT:
    raise RuntimeError("Texture publication must target FPSGAME.")
if "-run=" not in ue.SystemLibrary.get_command_line().lower() and ue.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError("The running editor is in PIE. Finish the current session before publishing.")
reference = json.loads((REVIEW / "bindings-before.json").read_text(encoding="utf-8"))
dirty = {pkg.get_path_name() for pkg in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
mesh = ue.load_asset(MESH)
used = {}
packages = {MESH}
for slot in mesh.materials:
    mat = slot.material_interface
    packages.add(mat.get_path_name().split(".")[0])
    for tex in ue.MaterialEditingLibrary.get_used_textures(mat.get_base_material()):
        used[tex.get_name()] = tex
    # A NullRHI commandlet can have no compiled material resources. Resolve
    # the saved material's actual texture dependencies in that case.
    if mat.get_path_name() in [entry["material"] for entry in reference["slots"]]:
        registry = ue.AssetRegistryHelpers.get_asset_registry()
        options = ue.AssetRegistryDependencyOptions(include_hard_package_references=True)
        assets = registry.get_dependencies(mat.get_base_material().get_path_name().split(".")[0], options) or []
        dependencies = {str(package) for package in assets}
        for name, entry in reference["textures"].items():
            if name not in used and entry["path"].split(".")[0] in dependencies:
                used[name] = ue.load_asset(entry["path"])
sources = []
for role in ("Color", "ORM", "Normal"):
    name = "T_VillageHerbalist_" + role
    path = INPUT / (name + ".png")
    if not path.is_file():
        if role == "Color":
            raise FileNotFoundError(path)
        continue
    tex = used.get(name)
    if not tex or tex.get_path_name() != reference["textures"][name]["path"]:
        raise RuntimeError(f"Could not resolve {name} from {sorted(packages)}, found {list(used)}")
    package = tex.get_path_name().split(".")[0]
    packages.add(package)
    sources.append((tex, path, package))
conflicts = sorted(dirty.intersection(packages))
if conflicts:
    raise RuntimeError("Unsaved herbalist assets in the editor: " + ", ".join(conflicts))

tools = ue.AssetToolsHelpers.get_asset_tools()
saved = []
for original, path, package in sources:
    # TextureFactory copies the texture's existing settings with this import task flag.
    # Remember editable display/compression properties too, so Interchange-enabled hosts
    # preserve the same settings even if their import path differs.
    properties = {name: original.get_editor_property(name)
                  for name in reference["textures"][original.get_name()]["settings"]}
    task = ue.AssetImportTask()
    task.filename = str(path)
    task.destination_path = package.rsplit("/", 1)[0]
    task.destination_name = original.get_name()
    task.factory = ue.TextureFactory()
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = False
    task.save = False
    tools.import_asset_tasks([task])
    imported = task.get_objects()
    if len(imported) != 1 or imported[0].get_path_name().split(".")[0] != package:
        raise RuntimeError("Import returned unexpected objects for " + package)
    texture = imported[0]
    for name, value in properties.items():
        if texture.get_editor_property(name) != value:
            texture.set_editor_property(name, value)
    if not ue.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError("Could not save texture " + package)
    saved.append({"asset": texture.get_path_name(), "source": str(path),
                  "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (REVIEW / "published.json").write_text(json.dumps({"saved": saved}, indent=2), encoding="utf-8")
print("HERBALIST_FACE_SAVED", [row["asset"] for row in saved], flush=True)
