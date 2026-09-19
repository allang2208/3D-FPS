"""Compare skeleton state of the re-imported axe against the untouched pickaxe. Read-only.

If both report the same skeleton situation, the "missing skeleton asset" trait is pre-existing
project behaviour rather than something this replacement introduced.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
GRIP = '/Game/Items/ProductionTools/GripMotion20260913'
report = {}

registry = u.EditorAssetLibrary.list_assets(GRIP, recursive=True, include_folder=False)
report['folder_assets'] = sorted(str(a) for a in registry)


def describe(path):
    asset = u.load_asset(path)
    if not asset:
        return {'asset': path, 'loaded': False}
    entry = {'loaded': True, 'class': asset.get_class().get_name()}
    if isinstance(asset, u.SkeletalMesh):
        skeleton = asset.get_editor_property('skeleton')
        entry['skeleton'] = skeleton.get_path_name() if skeleton else None
        entry['skeleton_class'] = skeleton.get_class().get_name() if skeleton else None
        entry['materials'] = [str(s.material_slot_name) for s in asset.get_editor_property('materials')]
    if isinstance(asset, u.AnimSequence):
        skeleton = asset.get_editor_property('skeleton')
        entry['skeleton'] = skeleton.get_path_name() if skeleton else None
    return entry


for name in ['SK_Harvest_Axe', 'SK_Harvest_Pickaxe']:
    report[name] = describe(f'{GRIP}/{name}')
for name in ['A_Harvest_Axe_Idle', 'A_Harvest_Pickaxe_Idle']:
    report[name] = describe(f'{GRIP}/{name}')

# Does the referenced skeleton path resolve at all, and what does the registry know about it?
for path in [f'{GRIP}/SK_Harvest_Axe_Skeleton', f'{GRIP}/SK_Harvest_Pickaxe_Skeleton']:
    entry = {'exists': u.EditorAssetLibrary.does_asset_exist(path)}
    asset = u.load_asset(path)
    entry['loads'] = bool(asset)
    entry['class'] = asset.get_class().get_name() if asset else None
    if asset and isinstance(asset, u.Skeleton):
        entry['bones'] = asset.get_editor_property('bone_tree')[0].get_editor_property('name') if False else None
        entry['reference_skeleton'] = str(asset.get_editor_property('reference_skeleton').get_path_name()) if False else None
    report[path] = entry

# Compare with the pickaxe's own known-good reference through its mesh package path.
report['axe_mesh_package'] = u.load_asset(f'{GRIP}/SK_Harvest_Axe').get_outer().get_path_name() if u.load_asset(f'{GRIP}/SK_Harvest_Axe') else None

(ROOT / 'SourceAssets/BattleAxeReplace20260919/skeleton-probe.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print(json.dumps(report, indent=2, default=str))
u.log('BATTLE_AXE_SKELETON_PROBE_DONE')