"""Save color-matched V9 followers by duplication, retaining all corrective morphs."""
import gc
import hashlib
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
ROOT = '/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/ViewSkin'
modular = json.loads(Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
tint = json.loads((WORK / 'ViewSkin/tint.json').read_text())['skin_tint_linear']
A, E = u.AssetToolsHelpers.get_asset_tools(), u.EditorAssetLibrary
material_path = ROOT + '/MI_Kaitlin_V9'
material = u.load_asset(material_path)
if not material:
    parent = u.load_asset('/Game/Characters/ModularOutfit20260924/BareSkinV9/MI_BareSkinV9')
    material = A.duplicate_asset('MI_Kaitlin_V9', ROOT, parent)
    u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(material, 'SkinTint', u.LinearColor(*tint, 1.))
    u.MaterialEditingLibrary.update_material_instance(material)
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Female V9 skin material did not save.')
sources = {}
for profile in modular['profiles'].values():
    if profile.get('rig_profile') not in ('Jason', 'Body') and profile.get('native_bare_skin'):
        sources[profile['native_bare_skin']] = profile['rig_profile']
for item in modular['items'].values():
    for rig, path in item.get('skin_meshes', {}).items():
        if rig not in ('Jason', 'Body') and path:
            sources[path] = rig
receipt_path = WORK / 'ViewSkin/saved_assets.json'
saved = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
count = 0
for source, rig in sources.items():
    if source in saved:
        continue
    asset = u.load_asset(source)
    name = 'SK_KaitlinView_' + rig + '_' + hashlib.sha256(source.encode()).hexdigest()[:10]
    if E.does_asset_exist(ROOT + '/' + name):
        raise RuntimeError('Unreceipted view-skin output exists; preserve it: ' + name)
    copy = A.duplicate_asset(name, ROOT, asset)
    materials = list(copy.get_editor_property('materials'))
    changed = 0
    for index, slot in enumerate(materials):
        source_material = slot.material_interface.get_path_name() if slot.material_interface else ''
        if 'SkinV9' in source_material:
            new_slot = slot.copy()
            new_slot.material_interface = material
            materials[index] = new_slot
            changed += 1
    if not changed:
        raise RuntimeError('V9 surface input needs an explicit material mapping: ' + source)
    copy.set_editor_property('materials', materials)
    if not E.save_loaded_asset(copy, False):
        raise RuntimeError('Female V9 follower did not save: ' + name)
    saved[source] = copy.get_path_name()
    receipt_path.write_text(json.dumps(saved, indent=2), encoding='utf-8')
    print('KAITLIN_VIEW_SKIN_SAVED', rig, name, flush=True)
    del copy, asset, materials
    gc.collect()
    u.SystemLibrary.collect_garbage()
    count += 1
    if count >= 4:
        break
remaining = sum(source not in saved for source in sources)
(WORK / 'save_view_skin_status.json').write_text(json.dumps({'remaining': remaining, 'complete': remaining == 0}), encoding='utf-8')
