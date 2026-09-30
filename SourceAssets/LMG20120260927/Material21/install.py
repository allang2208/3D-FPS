"""Create 201-private material variants, compile, bind and save; no game launch."""
import unreal as u
import json, sys, shutil
from pathlib import Path

O = Path(__file__).parent
sys.path.insert(0, str(O))
import finish_recipe as F
E = u.EditorAssetLibrary
M = u.MaterialEditingLibrary
R = O.parents[2]
source = json.loads((O / 'before.json').read_text(encoding='utf8'))
receipt = {'status': 'authoring', 'materials': {}, 'meshes': {}, 'compiled': {},
           'normal_preserved': {}, 'runtime_tested': False, 'rendered': False}


def record(): (O / 'delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')


def save(a):
    if not E.save_loaded_asset(a, False): raise RuntimeError('Save failed ' + a.get_path_name())


def clone(src, dest):
    a = u.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(src, dest)
    if not a: raise RuntimeError('Cannot clone ' + src)
    return a


def normal_signature(mat):
    n = M.get_material_property_input_node(mat, u.MaterialProperty.MP_NORMAL)
    if not n: return None
    return {'node': n.get_name(), 'pin': str(M.get_material_property_input_node_output_name(mat, u.MaterialProperty.MP_NORMAL))}


grain = clone(F.GRAIN_SOURCE, F.GRAIN_PATH)
grain.set_editor_property('srgb', False)
grain.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_GRAYSCALE)
grain.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
save(grain)
receipt['detail_texture'] = grain.get_path_name()
mapping = {}
for path, d in source['materials'].items():
    if not path.startswith('/Game/Weapons/LMG201/'): continue
    name = path.split('.')[-1]
    # Keep intentional interior anti-glare and existing titanium appearance.
    if 'titanium_brake' in name or name in ['M_LMG201_Inside', 'M_LMG201_ReferenceSightInner']: continue
    mapping[path] = F.P + '/Materials/' + name
for path, dest in mapping.items():
    d = source['materials'][path]
    if d['class'] != 'Material': continue
    mat = clone(path, dest)
    before_normal = normal_signature(mat)
    settings = F.profile(mat.get_name(), d['parameters'])
    method = F.apply_graph(mat, settings, grain)
    errors = M.recompile_material(mat)
    receipt['compiled'][dest] = [str(e) for e in (errors or [])]
    if errors: record(); raise RuntimeError('Material compiler errors ' + dest + ': ' + str(errors))
    after_normal = normal_signature(mat)
    if before_normal != after_normal: raise RuntimeError('Structural normal changed ' + dest)
    receipt['normal_preserved'][dest] = after_normal
    E.set_metadata_tag(mat, 'LMG201FinishRevision', 'Material21')
    E.set_metadata_tag(mat, 'LMG201FinishSource', path)
    E.set_metadata_tag(mat, 'LMG201FinishMethod', method)
    save(mat)
    receipt['materials'][path] = {'asset': mat.get_path_name(), 'settings': settings, 'method': method}
    record()
for path, dest in mapping.items():
    d = source['materials'][path]
    if d['class'] != 'MaterialInstanceConstant': continue
    mat = clone(path, dest)
    old = u.load_asset(path)
    parent_path = old.parent.get_path_name()
    M.set_material_instance_parent(mat, u.load_asset(mapping.get(parent_path, parent_path)))
    settings = F.profile(mat.get_name(), d['parameters'])
    for k, v in settings['scalar'].items(): M.set_material_instance_scalar_parameter_value(mat, k, v)
    for k, v in settings['vector'].items(): M.set_material_instance_vector_parameter_value(mat, k, u.LinearColor(*v, 1))
    M.update_material_instance(mat)
    save(mat)
    receipt['materials'][path] = {'asset': mat.get_path_name(), 'settings': settings, 'parent': mat.parent.get_path_name()}
    record()

# All new materials are saved before any live mesh binding is changed.
bindings = {'meshes': {}}
for path, d in source['meshes'].items():
    mesh = u.load_asset(path)
    package = R / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    backup = O / 'Before' / package.relative_to(R)
    if not backup.exists(): backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(package, backup)
    prop = 'materials' if isinstance(mesh, u.SkeletalMesh) else 'static_materials'
    slots = mesh.get_editor_property(prop)
    expected = {s['slot']: s['material'] for s in d['slots']}
    final = {}
    for i, slot in enumerate(slots):
        old_path = slot.material_interface.get_path_name() if slot.material_interface else None
        old_source = expected.get(str(slot.material_slot_name))
        if old_source not in mapping: continue
        desired = mapping[old_source]
        desired_full = desired + '.' + desired.rsplit('/', 1)[-1]
        if old_path not in [old_source, desired_full]: raise RuntimeError('Material binding changed during work: ' + path)
        slot.material_interface = u.load_asset(desired)
        slots[i] = slot
        final[str(slot.material_slot_name)] = desired_full
    mesh.set_editor_property(prop, slots)
    save(mesh)
    actual = {str(s.material_slot_name): s.material_interface.get_path_name() if s.material_interface else None
              for s in mesh.get_editor_property(prop)}
    if any(actual.get(k) != v for k, v in final.items()): raise RuntimeError('Binding save failed: ' + path)
    bindings['meshes'][path] = final
    receipt['meshes'][path] = actual
    record()
(O / 'bindings.json').write_text(json.dumps(bindings, indent=2), encoding='utf8')
receipt['status'] = 'materials_compiled_meshes_bound_and_saved'
record()
u.log('LMG201_MATERIAL21_SAVED materials=' + str(len(receipt['materials'])) + ' meshes=' + str(len(receipt['meshes'])))
