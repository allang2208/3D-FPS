"""Deploy the four selected faceless martial icons to their existing game paths."""
import json
import shutil
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
author = root / "SourceAssets/SkillIconRoundedSquare20261004"
work = author / "DeploymentV1"
runtime = root / "Content/ColdSteelData/Skills"
previous = work / "PreviousIcons"
previous.mkdir(parents=True, exist_ok=True)
icons = [
    ("swordUppercut", "UppercutSilhouetteV5/sword_uppercut_silhouette_v5.png", "sword_uppercut_cold_steel.png"),
    ("heavyStrike", "MartialSilhouetteFamilyV1/heavy_strike_silhouette_v1.png", "heavy_strike_cold_steel.png"),
    ("dashAttack", "MartialSilhouetteFamilyV1/dash_attack_silhouette_v1.png", "dash_attack.png"),
    ("whirlwind", "MartialSilhouetteFamilyV1/whirlwind_silhouette_v1.png", "whirlwind_cold_steel.png"),
]
tasks = []
for skill, source_name, runtime_name in icons:
    target = runtime / runtime_name
    for old_file in (target, target.with_suffix(".uasset")):
        backup = previous / old_file.name
        if old_file.is_file() and not backup.exists():
            shutil.copy2(old_file, backup)
    shutil.copy2(author / source_name, target)
    task = unreal.AssetImportTask()
    task.filename = str(target)
    task.destination_path = "/Game/ColdSteelData/Skills"
    task.destination_name = target.stem
    task.automated = True
    task.replace_existing = True
    task.save = False
    tasks.append(task)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
saved = []
for entry, task in zip(icons, tasks):
    skill, source_name, runtime_name = entry
    if not task.imported_object_paths:
        raise RuntimeError("Icon import failed: " + skill)
    asset_path = "/Game/ColdSteelData/Skills/" + Path(runtime_name).stem
    texture = unreal.load_asset(asset_path)
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError("Expected a Texture2D: " + asset_path)
    texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property("never_stream", True)
    texture.set_editor_property("srgb", True)
    texture.set_editor_property("max_texture_size", 512)
    if not unreal.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
        raise RuntimeError("Could not save icon: " + asset_path)
    saved.append({
        "skill": skill,
        "source": str((author / source_name).relative_to(root)),
        "runtime_png": str((runtime / runtime_name).relative_to(root)),
        "asset": texture.get_path_name(),
        "saved": True,
    })
    print("MARTIAL_ICON_SAVED " + skill + " " + texture.get_path_name())

receipt = {
    "selected_by_user": True,
    "style": "faceless figure, simplified dark training clothes, silver action trail and rounded square metal frame",
    "icons": saved,
    "game_tested": False,
}
(work / "deployment_result.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("MARTIAL_SILHOUETTE_DEPLOYMENT_COMPLETE " + str(len(saved)))
