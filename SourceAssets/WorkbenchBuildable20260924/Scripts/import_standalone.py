"""Import the standalone buildable workbench and register it in the build palette.

Runs inside UnrealEditor-Cmd:
  "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" `
    D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript `
    -script=D:/FPS3D/FPSGAME/SourceAssets/WorkbenchBuildable20260924/Scripts/import_standalone.py `
    -unattended -nop4 -nosplash -NullRHI

Steps: clutter textures -> MI children of the kit's M_WBK_Surface -> merged mesh with the
kit InUse materials -> DA_VoxelBuildPalette component entry (20 cm grid, Free mount).
Idempotent: content-hash metadata gates every asset.
"""
from pathlib import Path
import json, re, hashlib, math, unreal as u

ROOT = Path(__file__).resolve().parents[1]
KIT_ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkbenchKit20260921')
MAN = json.loads((ROOT / 'Authored/manifest_build.json').read_text(encoding='utf-8'))
KIT_RECEIPT = json.loads((KIT_ROOT / 'Receipts/asset-import.json').read_text(encoding='utf-8'))
INUSE = KIT_RECEIPT['materials']['InUse']
DEST = '/Game/Building/Workbench'
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
SURFACE_PARENT = '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/M_WBK_Surface'

E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
receipt = {'stage': 'starting', 'tests_run': False, 'renders_run': False}
def write():
    (ROOT / 'Receipts' / 'ue-import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
def save(o):
    if not E.save_loaded_asset(o, False):
        raise RuntimeError('save failed ' + o.get_path_name())
def sig(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()

# ---------------------------------------------------------------- clutter textures
TEX_CH = {'BaseColor': (u.TextureCompressionSettings.TC_BC7, True),
          'Normal': (u.TextureCompressionSettings.TC_NORMALMAP, False),
          'Roughness': (u.TextureCompressionSettings.TC_MASKS, False)}
textures = {}
for key, cfg in MAN['new_materials'].items():
    name = 'T_' + key + '_BaseColor'
    path = DEST + '/Textures/' + name
    src = Path(cfg['texture'])
    signature = hashlib.sha256(src.read_bytes()).hexdigest()
    t = u.load_asset(path)
    if not t or E.get_metadata_tag(t, 'WBStandaloneTexture') != signature:
        task = u.AssetImportTask()
        task.filename = str(src)
        task.destination_path = DEST + '/Textures'
        task.destination_name = name
        task.automated = True
        task.replace_existing = bool(t)
        task.save = False
        A.import_asset_tasks([task])
        t = u.load_asset(path)
        if not t:
            raise RuntimeError('texture import failed ' + name)
        t.modify()
        t.set_editor_property('srgb', True)
        t.set_editor_property('virtual_texture_streaming', False)
        t.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7)
        E.set_metadata_tag(t, 'WBStandaloneTexture', signature)
        save(t)
    textures[key] = t
receipt['textures'] = {k: v.get_path_name() for k, v in textures.items()}
write()

# ---------------------------------------------------------------- clutter material instances
parent = u.load_asset(SURFACE_PARENT)
if not parent:
    raise RuntimeError('missing surface parent ' + SURFACE_PARENT)
new_mis = {}
for key, cfg in MAN['new_materials'].items():
    name = 'MI_' + key
    path = DEST + '/Materials/' + name
    mi = u.load_asset(path)
    signature = sig('parent', SURFACE_PARENT, cfg['roughness'], cfg['metallic'], key)
    if mi and E.get_metadata_tag(mi, 'WBStandaloneMaterial') == signature:
        new_mis[key] = mi
        continue
    if not mi:
        mi = A.create_asset(name, DEST + '/Materials', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    mi.modify()
    L.set_material_instance_parent(mi, parent)
    L.set_material_instance_texture_parameter_value(mi, 'BaseColorMap', textures[key])
    L.set_material_instance_scalar_parameter_value(mi, 'UseBaseMap', 1.0)
    L.set_material_instance_scalar_parameter_value(mi, 'UseNormalMap', 0.0)
    L.set_material_instance_scalar_parameter_value(mi, 'UseRoughnessMap', 0.0)
    L.set_material_instance_scalar_parameter_value(mi, 'UseMetallicMap', 0.0)
    L.set_material_instance_scalar_parameter_value(mi, 'RoughnessValue', cfg['roughness'])
    L.set_material_instance_scalar_parameter_value(mi, 'MetallicValue', cfg['metallic'])
    L.set_material_instance_scalar_parameter_value(mi, 'DustAmount', 0.0)
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WBStandaloneMaterial', signature)
    save(mi)
    new_mis[key] = mi
receipt['materials'] = {k: v.get_path_name() for k, v in new_mis.items()}
write()

# ---------------------------------------------------------------- merged mesh
mesh_path = DEST + '/Meshes/' + MAN['name']
geometry_sig = str(MAN['triangles']) + '|' + json.dumps(MAN['bounds_cm'], sort_keys=True)
mesh = u.load_asset(mesh_path)
if mesh and E.get_metadata_tag(mesh, 'WBStandaloneGeometry') != geometry_sig:
    mesh = None
if not mesh:
    task = u.AssetImportTask()
    task.filename = MAN['fbx']
    task.destination_path = DEST + '/Meshes'
    task.destination_name = MAN['name']
    task.automated = True
    task.replace_existing = bool(mesh)
    task.replace_existing_settings = True
    task.save = False
    opt = u.FbxImportUI()
    opt.import_mesh = True
    opt.import_materials = False
    opt.import_textures = False
    opt.import_as_skeletal = False
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    d = opt.static_mesh_import_data
    d.combine_meshes = True
    d.convert_scene = True
    d.convert_scene_unit = True
    d.transform_vertex_to_absolute = True
    d.generate_lightmap_u_vs = False
    d.auto_generate_collision = False
    d.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    d.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task.options = opt
    task.factory = u.FbxFactory()
    A.import_asset_tasks([task])
    mesh = u.load_asset(mesh_path)
    if not mesh:
        raise RuntimeError('mesh import failed ' + mesh_path)
    mesh.modify()
    slots = mesh.get_editor_property('static_materials')
    # manifest may list slots that hold no faces (FBX export drops them); map by name
    for index, slot in enumerate(slots):
        key = re.sub(r'[._][0-9]{3}$', '', str(slot.get_editor_property('material_slot_name')))
        if key.startswith('WBKC_'):
            mat = new_mis.get(key)
        else:
            source = MAN['slot_sources'].get(key)
            mat = u.load_asset(INUSE.get(source, source)) if source else None
        if not mat:
            raise RuntimeError('material mapping failed for slot %s' % key)
        mesh.set_material(index, mat)
    ns = mesh.get_editor_property('nanite_settings')
    ns.enabled = MAN['triangles'] > 70000
    mesh.set_editor_property('nanite_settings', ns)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    E.set_metadata_tag(mesh, 'WBStandaloneGeometry', geometry_sig)
    save(mesh)
receipt['mesh'] = mesh.get_path_name()
bounds = mesh.get_bounds()
ext = bounds.box_extent
# box_extent is already in UE centimetres (half-size); full size = 2 * extent
size_cm = [ext.x * 2, ext.y * 2, ext.z * 2]
cells = [max(1, int(math.ceil(s / 20.0 - 1e-4))) for s in size_cm]
receipt['size_cm'] = [round(s, 1) for s in size_cm]
receipt['footprint_cells'] = cells
write()

# ---------------------------------------------------------------- palette entry
palette = E.load_asset(PALETTE)
if not palette:
    raise RuntimeError('active palette missing: ' + PALETTE)
entry = u.VoxelBuildPrefab()
entry.set_editor_property('id', 'workbench_table')
entry.set_editor_property('display_name', u.Text('工作台'))
entry.set_editor_property('mesh', mesh)
entry.set_editor_property('footprint', u.IntVector(cells[0], cells[1], cells[2]))
entry.set_editor_property('mount', u.VoxelPrefabMount.FREE)
entry.set_editor_property('surface', mesh.get_material(0))
entry.set_editor_property('pivot_offset_cm', u.Vector(0, 0, 0))
components = list(palette.get_editor_property('components'))
replaced = False
for index, existing in enumerate(components):
    if existing.get_editor_property('id') == 'workbench_table':
        components[index] = entry
        replaced = True
        break
if not replaced:
    components.append(entry)
palette.modify()
palette.set_editor_property('components', components)
if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(PALETTE)], False):
    raise RuntimeError('palette save failed')
back = E.load_asset(PALETTE).get_editor_property('components')
found = [c for c in back if c.get_editor_property('id') == 'workbench_table']
fp = found[0].get_editor_property('footprint') if found else None
receipt['palette'] = {'total': len(back), 'found': bool(found),
                      'footprint': [fp.x, fp.y, fp.z] if fp else None}
receipt['stage'] = 'done'
write()
print('WBSTANDALONE_DONE mesh=%s cells=%s slots=%d tris=%d palette_total=%d' % (
    mesh.get_path_name(), cells, len(MAN['slots']), MAN['triangles'], len(back)))
