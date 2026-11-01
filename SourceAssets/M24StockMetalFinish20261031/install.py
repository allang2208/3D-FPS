"""Apply a restrained metallic finish to both active M24 advanced-body variants."""
import unreal as u, json, hashlib, shutil
from pathlib import Path
O = Path(__file__).resolve().parent
D = '/Game/Weapons/M24/StockMetalFinish20261031/Materials'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
inputs = json.loads((O / 'inputs.json').read_text(encoding='utf-8'))
R = {'complete': False, 'saved': [], 'bindings': {}, 'runtime_tested': False,
     'geometry_changed': False, 'animations_changed': False, 'shared_materials_changed': False}

def record():
    (O / 'install_receipt.json').write_text(json.dumps(R, indent=2), encoding='utf-8')

def load(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError('Missing ' + path)
    return obj

def disk(path):
    return Path(u.Paths.project_content_dir()) / (path.split('.')[0].removeprefix('/Game/') + '.uasset')

def save(obj):
    if not E.save_loaded_asset(obj, False): raise RuntimeError('Save failed ' + obj.get_path_name())
    R['saved'].append(obj.get_path_name())
    record()

dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for row in inputs['assets'].values():
    if row['path'] in dirty: raise RuntimeError('Unsaved mesh retained ' + row['path'])
    if hashlib.sha256(disk(row['path']).read_bytes()).hexdigest() != row['sha256']:
        raise RuntimeError('Concurrent mesh edit retained ' + row['path'])
for path, data in inputs['materials'].items():
    if path.split('.')[0] in dirty: raise RuntimeError('Unsaved source material retained ' + path)
    if hashlib.sha256(disk(path).read_bytes()).hexdigest() != data['sha256']:
        raise RuntimeError('Concurrent material edit retained ' + path)
if any(p.startswith(D) for p in dirty): raise RuntimeError('Unsaved finish work retained')

# Preserve the source microfinish, the geometry's real bevels and its own masks.
# This recipe changes only the M24 advanced chassis; the native receiver,
# stock polymer/rubber, optics and the shared WS mother material are untouched.
families = {
    'anodized': {'color': [.026, .028, .030], 'metal': 1., 'rough': .36,
                 'source_rough': .85, 'grain': .008, 'edge': .055},
    'steel': {'color': [.058, .062, .066], 'metal': 1., 'rough': .29,
              'source_rough': .8, 'grain': .006, 'edge': .04},
    'interior': {'color': [.009, .010, .011], 'metal': 0., 'rough': .60,
                 'source_rough': .7, 'grain': .004, 'edge': .01},
    'seat': {'color': [.026, .028, .030], 'metal': 1., 'rough': .36,
             'source_rough': .85, 'grain': .008, 'edge': 0.},
}
slots = {
    'M24_AAS_CoatedMetal': 'anodized', 'M24_AAS_SatinSteel': 'steel', 'M24_AAS_Interior': 'interior',
    'M24_Advanced_0': 'anodized', 'M24_Advanced_2': 'steel', 'M24_Advanced_1': 'interior',
    'M24_NewReceiverMetal': 'seat',
}
materials = {}
record()
for key, row in inputs['assets'].items():
    mesh = load(row['path'])
    backup = O / 'Before' / (row['path'].removeprefix('/Game/') + '.uasset')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists(): shutil.copy2(disk(row['path']), backup)
    bindings = []
    for i, slot in enumerate(mesh.static_materials):
        name = str(slot.material_slot_name)
        family = slots.get(name)
        if not family:
            bindings.append({'slot': name, 'material': slot.material_interface.get_path_name(), 'preserved': True})
            continue
        src = slot.material_interface.get_path_name()
        target = D + '/MI_M24_' + key + '_' + family
        if E.does_asset_exist(target):
            raise RuntimeError('Finish destination already exists; do not overwrite previous authoring: ' + target)
        mi = E.duplicate_asset(src, target)
        if not mi: raise RuntimeError('Material duplication refused; finish PIE before asset publication')
        recipe = families[family]
        values = {'Metallic': recipe['metal'], 'EdgeMetallic': recipe['metal'], 'Specular': .5,
                  'Roughness': recipe['rough'], 'SourceRoughnessWeight': recipe['source_rough'],
                  'SourceRoughnessPivot': .5, 'SourceColorWeight': 0.,
                  'GrainRoughness': recipe['grain'], 'MottleRoughness': 0., 'MottleColor': 0.,
                  'EdgeWear': 0., 'EdgeHighlight': recipe['edge'], 'ScratchAmount': 0.,
                  'Stipple': 0., 'HandlingPolish': 0.,
                  'CavityDarken': 0. if family == 'seat' else .025,
                  'CavityRoughness': 0. if family == 'seat' else .018,
                  'AOStrength': 0. if family == 'seat' else .45, 'WeaponWetness': 0.,
                  'RainSurfaceResponse': 1. if recipe['metal'] else 2.}
        available = inputs['materials'][src]['parameters']['scalar']
        if 'ContinuityNormalStrength' in available:
            values['ContinuityNormalStrength'] = 1.
        for name_, value in values.items():
            L.set_material_instance_scalar_parameter_value(mi, name_, value)
        L.set_material_instance_vector_parameter_value(mi, 'FinishColor', u.LinearColor(*recipe['color'], 1.))
        L.update_material_instance(mi)
        E.set_metadata_tag(mi, 'M24FinishRecipe', str(O / 'install.py'))
        E.set_metadata_tag(mi, 'M24FinishIntent', 'Reference dark satin metal; authored microfinish restored; no bright wear or heavy grain')
        save(mi)
        mesh.set_material(i, mi)
        bindings.append({'slot': name, 'material': mesh.get_material(i).get_path_name(),
                         'family': family, 'source': src,
                         'scalars': {p: L.get_material_instance_scalar_parameter_value(mi, p) for p in values},
                         'normal': L.get_material_instance_texture_parameter_value(mi, 'SurfaceNormal').get_path_name(),
                         'mask': L.get_material_instance_texture_parameter_value(mi, 'SurfaceMask').get_path_name(),
                         'mask_uv': L.get_material_instance_scalar_parameter_value(mi, 'MaskUVChannel')})
    save(mesh)
    R['bindings'][row['path']] = bindings
    record()
R['recipe'] = families
R['stock_catalog'] = {'factory_id_preserved': 'm24_cheekrest', 'removed_option': 'none',
                      'factory_includes_cheekrest': True,
                      'legacy_resolution': 'UGunsmithSystem::Normalize rejects the removed option, then restores default_parts.stock'}
R['complete'] = True
record()
print('M24_STOCK_METAL_FINISH_SAVED', len(R['saved']), flush=True)
