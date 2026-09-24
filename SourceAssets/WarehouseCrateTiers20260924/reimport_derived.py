"""Re-import the five tier crates FROM the chest geometry + refresh their palette footprints.

    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/WarehouseCrateTiers20260924/reimport_derived.py

Runs INSIDE the live editor (remote execution): the palette + SM_* assets are loaded there,
so an external commandlet write would silently fail (workflow §6). Textures/materials are
unchanged (slot names Crate_* are identical); only the mesh geometry changed and with it
the per-entry footprint (now 8x6x7 = 160x120x140 cm) and pivot_z (ground offset).
Delete-then-fresh-import per the revised-mesh rule (never replace_existing on revised meshes).
"""
import json, math, re
from pathlib import Path
import unreal as u

try:
    HERE = Path(__file__).parent
except NameError:
    HERE = Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924')
ROOT = '/Game/Props/WarehouseCrateTiers20260924'
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
MESHES = {  # palette id -> (old v1 asset name, new derived asset name, source fbx)
    'warehouse_crate_wood':      ('SM_WarehouseCrate_T1_Wood',      'SM_WarehouseCrate_T1_Wood_v2',      'SM_WarehouseCrate_T1_Wood.fbx'),
    'warehouse_crate_stonewood': ('SM_WarehouseCrate_T2_StoneWood', 'SM_WarehouseCrate_T2_StoneWood_v2', 'SM_WarehouseCrate_T2_StoneWood.fbx'),
    'warehouse_crate_iron':      ('SM_WarehouseCrate_T3_Iron',      'SM_WarehouseCrate_T3_Iron_v2',      'SM_WarehouseCrate_T3_Iron.fbx'),
    'warehouse_crate_irongold':  ('SM_WarehouseCrate_T4_IronGold',  'SM_WarehouseCrate_T4_IronGold_v2',  'SM_WarehouseCrate_T4_IronGold.fbx'),
    'warehouse_crate_silvergem': ('SM_WarehouseCrate_T5_SilverGem', 'SM_WarehouseCrate_T5_SilverGem_v2', 'SM_WarehouseCrate_T5_SilverGem.fbx'),
}
E = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
uasset_dir = Path('D:/FPS3D/FPSGAME/Content/Props/WarehouseCrateTiers20260924')
materials = {name: u.load_asset(ROOT + '/Materials/M_' + name) for name in
             ('Crate_Wood', 'Crate_WoodDark', 'Crate_Stone', 'Crate_Iron', 'Crate_IronDark',
              'Crate_Gold', 'Crate_Silver', 'Crate_Gem')}
assert all(materials.values()), 'missing a tier material under ' + ROOT

saved, receipts = [], []

def save(asset):
    path = asset.get_path_name().split('.')[0]
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(path)], False):
        raise RuntimeError('Cannot save ' + path)
    saved.append(path)

def import_one(pid, new_name, fbx):
    existing = u.load_asset(ROOT + '/' + new_name)
    if existing is not None:
        # already imported (idempotent rerun): do NOT delete a loaded package (ghost-file
        # collision hazard); verify magnitude and reuse it.
        ext = existing.get_bounds().box_extent
        size_cm = [round(ext.x * 2, 1), round(ext.y * 2, 1), round(ext.z * 2, 1)]
        if not (140.0 < size_cm[0] < 165.0):
            raise RuntimeError('Existing %s has wrong size %s; fix manually' % (new_name, size_cm))
        receipts.append({'id': pid, 'asset': new_name, 'size_cm': size_cm,
                         'triangles': existing.get_num_triangles(0), 'reused': True,
                         'slots': [str(s.get_editor_property('material_slot_name'))
                                   for s in existing.get_editor_property('static_materials')]})
        return
    if E.does_asset_exist(ROOT + '/' + new_name):
        E.delete_asset(ROOT + '/' + new_name)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_materials = False; options.import_textures = False; options.import_animations = False
    options.create_physics_asset = False; options.import_mesh = True; options.import_as_skeletal = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.convert_scene = True; data.convert_scene_unit = True; data.import_uniform_scale = 1
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.combine_meshes = True; data.auto_generate_collision = True; data.generate_lightmap_u_vs = True
    task = u.AssetImportTask(); task.filename = str(HERE / 'Authored' / fbx)
    task.destination_path = ROOT; task.destination_name = new_name; task.automated = True
    task.save = False; task.replace_existing = False
    task.set_editor_property('async_', False); task.factory = u.FbxFactory(); task.options = options
    AT.import_asset_tasks([task])
    mesh = next((a for a in task.get_objects() if a.get_path_name() == ROOT + '/' + new_name + '.' + new_name), None)
    if not mesh:
        raise RuntimeError('Mesh import failed ' + new_name)
    bound = mesh.get_bounds(); ext = bound.box_extent
    size_cm = [round(ext.x * 2, 1), round(ext.y * 2, 1), round(ext.z * 2, 1)]
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        slot_name = re.sub(r'[._][0-9]{3}$', '', str(slot.get_editor_property('material_slot_name')))
        if slot_name not in materials:
            raise RuntimeError('Unknown slot %r on %s' % (slot_name, new_name))
        mesh.set_material(index, materials[slot_name])
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
        u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    build = subsystem.get_lod_build_settings(mesh, 0)
    build.recompute_tangents = True; build.use_mikk_t_space = True
    build.use_high_precision_tangent_basis = True; build.use_full_precision_u_vs = True
    subsystem.set_lod_build_settings(mesh, 0, build)
    nanite = mesh.get_editor_property('nanite_settings'); nanite.enabled = True
    mesh.set_editor_property('nanite_settings', nanite)
    E.set_metadata_tag(mesh, 'CrateTier', new_name.split('_')[-2])
    E.set_metadata_tag(mesh, 'Source', 'Derived from warehouse chest RitualV8 geometry; WarehouseCrateTiers20260924')
    save(mesh)
    receipts.append({'id': pid, 'asset': new_name, 'size_cm': size_cm, 'triangles': mesh.get_num_triangles(0),
                     'slots': [str(s.get_editor_property('material_slot_name'))
                               for s in mesh.get_editor_property('static_materials')]})

flag = 'Interchange.FeatureFlags.Import.FBX'
previous_flag = u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    for pid, (old_name, new_name, fbx) in MESHES.items():
        import_one(pid, new_name, fbx)
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous_flag))

# refresh palette entries: mesh -> _v2 asset, footprint/pivot to the chest bounds
palette = u.load_asset(PALETTE)
components = list(palette.get_editor_property('components'))
by_index = {r['id']: r for r in receipts}
palette_touch = []
for position, entry in enumerate(components):
    pid = str(entry.get_editor_property('id'))
    if pid not in by_index:
        continue
    r = by_index[pid]
    size = r['size_cm']
    cells = [max(1, math.ceil((v - 0.01) / 20.0)) for v in size]
    entry.set_editor_property('mesh', u.load_asset(ROOT + '/' + r['asset']))
    entry.set_editor_property('footprint', u.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property('pivot_offset_cm', u.Vector(0.0, 0.0, -(cells[2] * 20.0 - size[2]) / 2.0))
    components[position] = entry
    palette_touch.append({'id': pid, 'mesh': r['asset'], 'footprint': cells,
                          'pivot_z': round(-(cells[2] * 20.0 - size[2]) / 2.0, 3)})
palette.modify(); palette.set_editor_property('components', components)
if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(PALETTE)], False):
    raise RuntimeError('Palette save failed')
saved.append(PALETTE)

# disk verification: the NEW .uasset files must exist; old v1 ghosts stay on disk (held by the
# running editor) and get trashed by the follow-up step / next editor session
missing = [r['asset'] for r in receipts if not (uasset_dir / (r['asset'] + '.uasset')).exists()]
if missing:
    raise RuntimeError('New .uasset files missing on disk: %s' % missing)

check = u.load_asset(PALETTE)
verified = {}
for entry in check.get_editor_property('components'):
    pid = str(entry.get_editor_property('id'))
    if pid in by_index:
        fp = entry.get_editor_property('footprint')
        mesh_ref = entry.get_editor_property('mesh')
        verified[pid] = {'footprint': [fp.x, fp.y, fp.z],
                         'mesh': mesh_ref.get_name() if mesh_ref else None,
                         'material_empty': entry.get_editor_property('material').is_none()}
for pid in by_index:
    if pid not in verified or not verified[pid]['material_empty'] or not verified[pid]['mesh'].endswith('_v2'):
        raise RuntimeError('Palette verify failed for ' + pid)

out = {'meshes': receipts, 'palette_updated': palette_touch, 'palette_verified': verified,
       'saved': saved, 'runtime_tested': False}
(HERE / 'reimport_receipt.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('DERIVED_REIMPORT_DONE ' + json.dumps({'cells': [t['footprint'] for t in palette_touch]}, ensure_ascii=False), flush=True)
