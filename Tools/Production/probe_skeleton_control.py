"""Control probe: does skeleton reporting work at all in this commandlet? Read-only.

Compares a known-working M4 viewmodel against the harvest tool meshes.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
report = {}

for label, path in [
        ('mannequin_skeleton_direct', '/Game/EasyBuildingSystem/Mannequin/Mesh/UE4_Mannequin_Skeleton'),
        ('m4_viewmodel_mesh', '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'),
        ('harvest_axe_mesh', '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe'),
        ('harvest_pickaxe_mesh', '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe')]:
    asset = u.load_asset(path)
    entry = {'loaded': bool(asset), 'class': asset.get_class().get_name() if asset else None}
    if asset and isinstance(asset, u.SkeletalMesh):
        skeleton = asset.get_editor_property('skeleton')
        entry['skeleton'] = skeleton.get_path_name() if skeleton else None
        entry['skeleton_valid'] = bool(skeleton)
    if asset and isinstance(asset, u.Skeleton):
        entry['bones'] = asset.get_editor_property('bone_tree')[0].get_editor_property('name') if False else 'n/a'
    report[label] = entry

# Animations: the M4 viewmodel anims are known to work in game.
for label, path in [
        ('harvest_axe_idle', '/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle'),
        ('harvest_pickaxe_idle', '/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Pickaxe_Idle')]:
    asset = u.load_asset(path)
    entry = {'loaded': bool(asset), 'class': asset.get_class().get_name() if asset else None}
    if asset:
        skeleton = asset.get_editor_property('skeleton')
        entry['skeleton'] = skeleton.get_path_name() if skeleton else None
        entry['length'] = round(asset.get_play_length(), 4)
    report[label] = entry

# Try the standalone getter path too: USkeletalMesh.get_skeleton() may differ from the property.
mesh = u.load_asset('/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe')
if mesh:
    for accessor in ['get_skeleton', 'get_editor_property']:
        try:
            value = getattr(mesh, accessor)('skeleton') if accessor == 'get_editor_property' else getattr(mesh, accessor)()
            report['accessor_' + accessor] = value.get_path_name() if value else None
        except Exception as error:
            report['accessor_' + accessor] = 'ERR ' + str(error)

# What does the asset registry know about the GripMotion folder?
registry = u.EditorAssetLibrary.list_assets('/Game/Items/ProductionTools/GripMotion20260913', recursive=True, include_folder=False)
report['folder_assets'] = sorted(str(a) for a in registry)

(ROOT / 'SourceAssets/BattleAxeReplace20260919/skeleton-control.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print(json.dumps(report, indent=2, default=str))
u.log('BATTLE_AXE_SKELETON_CONTROL_DONE')