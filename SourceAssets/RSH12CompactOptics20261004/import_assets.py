"""Import the four compact RSH meshes and save the new optical sockets.

Existing mesh paths and component transforms are intentionally retained. The
author exports the inverse body-offset into vertices and sockets together.
"""
import json
import shutil
from pathlib import Path

import unreal as u

O = Path(__file__).resolve().parent
P = O.parents[1]
D = '/Game/Weapons/RSH12/CompactOptics20261004'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
auth = json.loads((O/'authoring.json').read_text(encoding='utf8'))
receipt = dict(saved=[], meshes={}, complete=False, runtime_tested=False)

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE blocks compact optic import; authored FBXs are preserved')

targets = {s['asset'] for s in auth['meshes'].values()}
targets.add('/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets & dirty or any(p.startswith(D) for p in dirty):
    raise RuntimeError('Target optic assets have unsaved edits; import deferred')


def record():
    (O/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing compact optic dependency '+path)
    return asset


def backup(path):
    disk = P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    dest = O/'BeforeAssets'/(path.removeprefix('/Game/')+'.uasset')
    if disk.exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(disk, dest)


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    if asset.get_path_name() not in receipt['saved']:
        receipt['saved'].append(asset.get_path_name())
    record()


for path in targets:
    backup(path)

metal = load('/Game/Weapons/RSH12/Optics20261004/Materials/MI_RSH12_RailSteel')
inner_path = D+'/Materials/MI_RSH12_CompactInner'
inner = load(inner_path) if E.does_asset_exist(inner_path) else E.duplicate_asset(metal.get_path_name(), inner_path)
if not inner:
    raise RuntimeError('Cannot create compact inner material')
L.set_material_instance_vector_parameter_value(inner, 'FinishColor', u.LinearColor(.005, .0055, .006, 1.))
for name, value in dict(Metallic=0., Roughness=.87, SourceColorWeight=0., SourceRoughnessWeight=0.,
                        GrainRoughness=.002, MottleRoughness=.001, WeaponWetness=0.).items():
    L.set_material_instance_scalar_parameter_value(inner, name, value)
L.update_material_instance(inner)
E.set_metadata_tag(inner, 'RSHCompactRegion', 'Matte optical bore, seals and controls; independent of exterior steel')
save(inner)
materials = {
    'RSH_CompactMetal': metal,
    'RSH_CompactInner': inner,
    'RSH_CompactGlass': load('/Game/Weapons/CommonHK41620260930/Optics20261001/M_EOTH_ClearGlass'),
    'RSH_CompactReticle': load('/Game/Weapons/CommonHK41620260930/Optics20261001/M_EOTH_ClearReticle'),
}
# Reimport retains some public slot names from the rifle-derived meshes. Read
# the editor-only imported name; those names are not Python direct attributes.
legacy_slots = {'Holosight':'RSH_CompactMetal', 'Red_Dot':'RSH_CompactReticle',
    'M_HK416_Eo_tech':'RSH_CompactMetal', 'M_HK416_Glass':'RSH_CompactGlass',
    'M_HK416_Eo_tech_Reticle':'RSH_CompactReticle', 'RSH_OpticMountSteel':'RSH_CompactMetal'}

flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag+' 0')
try:
    for key, spec in auth['meshes'].items():
        folder, name = spec['asset'].rsplit('/', 1)
        task = u.AssetImportTask()
        task.filename = spec['fbx']
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        task.factory = u.FbxFactory()
        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh = True
        opt.import_as_skeletal = False
        opt.import_materials = False
        opt.import_textures = False
        opt.import_animations = False
        data = opt.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        task.options = opt
        A.import_asset_tasks([task])
        mesh = load(spec['asset'])
        slots = list(mesh.static_materials)
        for i, slot in enumerate(slots):
            label = str(slot.material_slot_name)
            imported_label = str(slot.get_editor_property('imported_material_slot_name'))
            mat = materials.get(imported_label) or materials.get(label) or materials.get(legacy_slots.get(label))
            if mat:
                slot.material_interface = mat
                slots[i] = slot
            elif not slot.material_interface:
                raise RuntimeError('Unmapped compact optic slot '+key+' '+label)
        mesh.set_editor_property('static_materials', slots)
        for socket_name, point in spec.get('sockets_cm', {}).items():
            socket = mesh.find_socket(socket_name)
            if not socket:
                socket = u.new_object(u.StaticMeshSocket, outer=mesh)
                socket.set_editor_property('socket_name', socket_name)
                mesh.add_socket(socket)
            socket.set_editor_property('relative_location', u.Vector(*point))
        E.set_metadata_tag(mesh, 'RSHOpticRevision', 'CompactOptics20261004: rebuilt compact body and direct rail saddle')
        E.set_metadata_tag(mesh, 'SourceAttribution', 'Original FPSGAME compact optic geometry; fitted to Rsh-12 by Medji (CC BY 4.0); project common optical materials')
        E.set_metadata_tag(mesh, 'RSHOpticMountContract', 'Unchanged fixed WPN_root mount; inverse offset baked once into vertices and optical sockets')
        save(mesh)
        receipt['meshes'][key] = dict(asset=mesh.get_path_name(), sockets_cm=spec.get('sockets_cm', {}),
            materials={str(m.material_slot_name):m.material_interface.get_path_name() for m in slots},
            imported_slots={str(m.material_slot_name):str(m.get_editor_property('imported_material_slot_name')) for m in slots})
        record()
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(previous))

weather = load('/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials')
mapping = dict(weather.get_editor_property('wet_materials'))
mapping[inner.get_path_name()] = inner
weather.set_editor_property('wet_materials', mapping)
save(weather)
receipt['complete'] = True
receipt['native_build_required'] = False
record()
print('RSH_COMPACT_OPTICS_IMPORTED_AND_SAVED', len(receipt['meshes']), flush=True)
