"""Read local gathering donors requested by the user; no assets are saved."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/ProductionTools')
OUT.mkdir(parents=True, exist_ok=True)
paths = [
    '/Game/EasyBuildingSystem/Blueprints/InteractionObjects/BP_EBS_Tree',
    '/Game/EasyBuildingSystem/Blueprints/InteractionObjects/BP_EBS_Mine',
    '/Game/EasyBuildingSystem/Blueprints/Components/BP_EBS_ResourcesComponent',
    '/Game/EasyBuildingSystem/Mannequin/Mesh/SK_Tool_Hatchet_001',
    '/Game/EasyBuildingSystem/Mannequin/Mesh/SK_Tool_Pickaxe_001',
    '/Game/EasyBuildingSystem/Meshes/Tools/Polygonal/SM_Polygonal_Hatchet',
    '/Game/EasyBuildingSystem/Meshes/Tools/Polygonal/SM_Polygonal_Pickaxe',
    '/Game/MilitaryTrench/Assets/3D/Ind_Mine_Tool_Shovel_Old_01/StaticMeshes/SM_Ind_Mine_Tool_Shovel_Old_01',
    '/Game/EasyBuildingSystem/Mannequin/Animations/A_Tool_Hatchet_Act',
    '/Game/EasyBuildingSystem/Mannequin/Animations/A_Tool_Pickaxe_Act',
    '/Game/EasyBuildingSystem/Mannequin/Animations/A_Mannequin_Axe_Act',
    '/Game/EasyBuildingSystem/Mannequin/Animations/A_Mannequin_PickAxe_Act',
]
registry = u.AssetRegistryHelpers.get_asset_registry()
result = {}
for path in paths:
    obj = u.load_asset(path)
    entry = {'loaded': obj is not None}
    result[path] = entry
    if obj is None:
        continue
    entry['class'] = obj.get_class().get_name()
    entry['dependencies'] = [str(x) for x in registry.get_dependencies(path, u.AssetRegistryDependencyOptions())]
    for name in ['skeleton', 'imported_bounds', 'materials', 'static_materials', 'sequence_length', 'rate_scale']:
        try:
            entry[name] = str(obj.get_editor_property(name))
        except Exception:
            pass
    if hasattr(obj, 'get_bounds'):
        entry['bounds'] = str(obj.get_bounds())
    if isinstance(obj, u.AnimSequence):
        entry['duration'] = obj.get_play_length()
        entry['frames'] = u.AnimationLibrary.get_num_frames(obj)
        entry['tracks'] = [str(x) for x in u.AnimationLibrary.get_animation_track_names(obj)]
    if isinstance(obj, u.Blueprint):
        cdo = u.get_default_object(obj.generated_class())
        entry['defaults'] = {}
        for name in dir(cdo):
            if any(k in name.lower() for k in ['health', 'resource', 'damage', 'hit', 'tool', 'mesh', 'respawn', 'count', 'amount', 'interact']):
                try:
                    value = cdo.get_editor_property(name)
                    entry['defaults'][name] = str(value)
                except Exception:
                    pass
(OUT/'asset-sources.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('PRODUCTION_ASSET_SOURCES_READ '+str(OUT/'asset-sources.json'))
