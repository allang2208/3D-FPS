"""Item 2: put the A762 accessories on the weapon-surface standard. Run through ../run_ue.ps1.

Reads Bake/accessory_plan.json (plan_accessories.py) and the baked masks in
Bake/Accessories/ that passed qa_accessory_masks.py (others use the neutral mask). For every 'preset' slot creates MI_A762_WS_<acc>_<slot suffix> under
/Game/Weapons/A762/SurfaceStandard08/Accessories/Materials (parent: the surface-card preset,
mask sampled in UV0, the slot's own normal map kept) and binds it; skipped slots (glass,
reticles, masked housings, muzzle recesses) keep their material. Mesh packages are backed
up to BeforeAccessories/ first; accessory_receipt.json records every binding for rollback.
Idempotent. No PIE, capture or gameplay check is performed.
"""
import hashlib
import json
import shutil
import unreal as u
from pathlib import Path

HERE = Path(__file__).parent
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
DEST = '/Game/Weapons/A762/SurfaceStandard08/Accessories'
PRESET = '/Game/Weapons/WeaponSurface/Presets/MI_WS_'
VERSION = 'WS1-Accessories-20260930'
BEADS_PER_CM = json.loads((HERE / 'slot_plan.json').read_text(encoding='utf-8'))['bead_cells_per_cm']
plan = json.loads((HERE / 'Bake' / 'accessory_plan.json').read_text(encoding='utf-8'))
qa = json.loads((HERE / 'Bake' / 'accessory_mask_qa.json').read_text(encoding='utf-8'))
RECEIPT = HERE / 'accessory_receipt.json'
receipt = json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else {
    'version': VERSION, 'backups': {}, 'textures': {}, 'materials': {}, 'bindings': {}, 'game_tested': False}


def record():
    RECEIPT.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())


if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('A762 accessories: PIE is running; nothing changed')

content = Path(u.Paths.project_dir()).resolve() / 'Content'


def mask_texture(name):
    source = HERE / 'Bake' / 'Accessories' / (name + '.png')
    path = DEST + '/Textures/' + name
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if not E.does_asset_exist(path) or receipt['textures'].get(name, {}).get('sha256') != digest:
        task = u.AssetImportTask()
        task.filename = str(source)
        task.destination_path = DEST + '/Textures'
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        A.import_asset_tasks([task])
    tex = u.load_asset(path)
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
    E.set_metadata_tag(tex, 'WeaponSurfaceVersion', VERSION)
    save(tex)
    receipt['textures'][name] = {'path': tex.get_path_name(), 'sha256': digest}
    return tex


def instance(name, spec, mask, bead_scale):
    path = DEST + '/Materials/' + name
    mi = u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(
        name, DEST + '/Materials', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    L.clear_all_material_instance_parameters(mi)
    mi.set_editor_property('parent', u.load_asset(PRESET + spec['preset']))
    scalars = {'MaskUVChannel': 0.0, 'BeadScale': bead_scale}
    scalars.update(spec.get('scalars', {}))
    for k, v in scalars.items():
        L.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in spec.get('vectors', {}).items():
        L.set_material_instance_vector_parameter_value(mi, k, u.LinearColor(*v, 1))
    textures = {}
    if mask:
        textures['SurfaceMask'] = mask
    if spec.get('normal'):
        textures['SurfaceNormal'] = u.load_asset(spec['normal'])
    for k, v in textures.items():
        L.set_material_instance_texture_parameter_value(mi, k, v)
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceVersion', VERSION)
    E.set_metadata_tag(mi, 'WeaponSurfacePreset', spec['preset'])
    save(mi)
    receipt['materials'][name] = {'path': mi.get_path_name(), 'preset': spec['preset'], 'scalars': scalars,
                                  'textures': {k: v.get_path_name() for k, v in textures.items()}}
    return mi


done = 0
for mesh_name, entry in plan.items():
    specs = {k: d for k, d in entry['slots'].items() if d['action'] == 'preset'}
    if not specs:
        continue
    rel = entry['path'].split('.')[0].removeprefix('/Game/') + '.uasset'
    if entry['path'] not in receipt['backups']:
        dst = HERE / 'BeforeAccessories' / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(content / rel, dst)
        receipt['backups'][entry['path']] = str(dst)
        record()
    acc = mesh_name.replace('SM_A762_', '')
    tex_name = 'T_A762_%s_WS_Mask' % acc
    mask = mask_texture(tex_name) if entry['mask'] == 'bake' and qa.get(tex_name, {}).get('use') else None
    bead = round(BEADS_PER_CM / max(entry['uv0']['uv_per_cm'], 1e-4), 3)
    mesh = u.load_asset(entry['path'])
    slots = mesh.get_editor_property('static_materials')
    changed = []
    for i, s in enumerate(slots):
        name = str(s.material_slot_name)
        if name not in specs:
            continue
        suffix = name.replace('A762_' + acc + '_', '').replace('M_', '')
        mi = instance('MI_A762_WS_%s_%s' % (acc, suffix), specs[name], mask, bead)
        changed.append({'slot': name, 'before': s.material_interface.get_path_name() if s.material_interface else None,
                        'after': mi.get_path_name()})
        s.material_interface = mi
        slots[i] = s
    mesh.set_editor_property('static_materials', slots)
    readback = {str(s.material_slot_name): s.material_interface.get_path_name() for s in mesh.get_editor_property('static_materials')
                if s.material_interface}
    if any(readback.get(c['slot']) != c['after'] for c in changed):
        raise RuntimeError('binding did not persist on ' + mesh_name)
    save(mesh)
    receipt['bindings'][entry['path']] = changed
    record()
    done += 1
    print('A762_ACCESSORY_BOUND', mesh_name, len(changed), 'mask' if mask else 'neutral', flush=True)
receipt['complete'] = True
record()
print('A762_ACCESSORIES_INSTALLED', done, len(receipt['materials']), flush=True)
