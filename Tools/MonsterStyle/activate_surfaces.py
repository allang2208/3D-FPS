"""Offline, scoped activation of the three Style V1 monster surfaces.

Leaves animation, AI, physics bodies, transforms and gameplay data unchanged.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2] / 'SourceAssets/MonsterStyleV1'
LIB = u.EditorAssetLibrary
source = json.loads((ROOT / 'ue_import.json').read_text(encoding='utf-8'))
recovery = ROOT / 'previous_references.json'
previous = json.loads(recovery.read_text(encoding='utf-8')) if recovery.exists() else {}
report = {'monsters': {}, 'preview_rendered': False, 'runtime_tested': False}

def save(asset):
    if not LIB.save_loaded_asset(asset, False): raise RuntimeError('Cannot save ' + asset.get_path_name())

for mode, info in source['monsters'].items():
    mesh = u.load_asset(info['mesh'])
    if mesh is None: raise RuntimeError('Missing imported surface: ' + info['mesh'])
    if 'blueprint' in info:
        bp = u.load_asset(info['blueprint'])
        cdo = u.get_default_object(bp.generated_class())
        if mode not in previous:
            old = cdo.get_editor_property('visual_mesh')
            previous[mode] = {'blueprint': bp.get_path_name(), 'visual_mesh': old.get_path_name()}
            recovery.write_text(json.dumps(previous, indent=2), encoding='utf-8')
        cdo.set_editor_property('visual_mesh', mesh)
        cdo.mesh.set_skeletal_mesh_asset(mesh)
        save(bp)
        report['monsters'][mode] = {'blueprint': bp.get_path_name(), 'mesh': mesh.get_path_name(), 'saved': True}
    else:
        slots = mesh.get_editor_property('materials')
        material_paths = list(info['materials'].values())
        if len(slots) != 1 or len(material_paths) != 1:
            raise RuntimeError('Mutant style activation requires its single authored material slot')
        if mode not in previous:
            previous[mode] = {'mesh': mesh.get_path_name(), 'materials': [
                {'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name()} for s in slots]}
            recovery.write_text(json.dumps(previous, indent=2), encoding='utf-8')
        material = u.load_asset(material_paths[0])
        slots[0].material_interface = material
        mesh.set_editor_property('materials', slots)
        save(mesh)
        report['monsters'][mode] = {'mesh': mesh.get_path_name(), 'material': material.get_path_name(), 'saved': True}
    (ROOT / 'activation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.log('MONSTER_STYLE_ACTIVATED ' + mode)

u.log('MONSTER_STYLE_ACTIVATION_COMPLETE')
