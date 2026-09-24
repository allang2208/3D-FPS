"""Deliberate revision pass: replace the installed furnace assets in place.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

Why this exists separately from ``install_blast_furnace.py``: that script keeps
existing assets on purpose, so a re-run never silently overwrites a revision.
This revision is requested (rounded block arrises, re-authored linear-albedo
PBR maps including a real metal, frozen slag removed), so it replaces in place
rather than deleting and recreating — replacing keeps the palette's soft object
path to the mesh valid.

Texture and mesh paths, material slot names and the palette entry ID are
unchanged; only the content is replaced. Nothing is placed in a level, no PIE
and no screenshot runs here.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = '/Game/Props/BlastFurnace20260923'
TEX_ROOT = ROOT + '/Textures'
MAT_ROOT = ROOT + '/Materials'
MESH_PATH = ROOT + '/SM_BlastFurnace'

MATERIAL_SPEC = [
    'BlastFurnace_Masonry', 'BlastFurnace_Firebrick', 'BlastFurnace_WroughtIron',
    'BlastFurnace_ClayLuting', 'BlastFurnace_SlagLining', 'BlastFurnace_EmberBed',
    'BlastFurnace_OreLump',
]
CHANNELS = ('BaseColor', 'Roughness', 'Metallic', 'Normal', 'AO')
EDITOR = u.EditorAssetLibrary
ASSETS = u.AssetToolsHelpers.get_asset_tools()
receipt = {'reason': 'PBR sets replaced with the project\'s own UnrealNormandy library '
                     '(Sharur\'s Normandy Village + PCG Plants, 4096 photogrammetry): brick from the '
                     'wall atlas clean block, T_StoneSurface_01A ashlar, T_MetalRust_00A iron, '
                     'T_SoilSurface_02A loam; on top of the earlier rounded arrises and the removed '
                     'launder/flow geometry',
           'runtime_tested': False, 'rendered': False}


def log(message):
    print('[blast_furnace_revise] ' + message, flush=True)


def save(asset):
    package = u.load_package(asset.get_path_name().split('.')[0])
    if not u.EditorLoadingAndSavingUtils.save_packages([package], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())


# --- textures: replace in place, then re-apply the sampling settings ----
replaced = []
for name in MATERIAL_SPEC:
    for channel in CHANNELS:
        png = HERE / 'Authored' / 'Textures' / ('%s_%s.png' % (name, channel))
        if not png.exists():
            raise RuntimeError('Missing generated map: ' + str(png))
        asset_name = 'T_%s_%s' % (name, channel)
        asset_path = '%s/%s' % (TEX_ROOT, asset_name)
        if not EDITOR.does_asset_exist(asset_path):
            raise RuntimeError('Revision expects the asset to exist: ' + asset_path)
        task = u.AssetImportTask()
        task.filename = str(png)
        task.destination_path = TEX_ROOT
        task.destination_name = asset_name
        task.automated = True
        task.replace_existing = True
        task.save = False
        ASSETS.import_asset_tasks([task])
        texture = u.load_asset(asset_path)
        if texture is None:
            raise RuntimeError('Texture missing after replace: ' + asset_path)
        srgb = asset_path.endswith('_BaseColor')
        texture.set_editor_property('srgb', srgb)
        if asset_path.endswith('_Normal'):
            texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
        elif not srgb:
            texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
        else:
            texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
        if bool(texture.get_editor_property('srgb')) != srgb:
            raise RuntimeError('sRGB did not stick on ' + asset_path)
        save(texture)
        replaced.append(asset_path)
receipt['textures_replaced'] = len(replaced)
log('textures replaced %d' % len(replaced))

# --- mesh: delete, then import from scratch -----------------------------
# ``replace_existing=True`` routes through UE's reimport path, which reuses the
# import options already stored on the asset. Run twice, that stacked the unit
# scale and left a 1.2 cm mesh (confirmed by an independent-process read-back),
# so the asset is deleted and re-imported instead. The palette stores a soft
# object path, which resolves again once the same path exists.
if EDITOR.does_asset_exist(MESH_PATH):
    if not EDITOR.delete_asset(MESH_PATH):
        raise RuntimeError('Could not delete the existing mesh for a clean import: ' + MESH_PATH)
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
data = options.static_mesh_import_data
data.combine_meshes = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = True
data.transform_vertex_to_absolute = True
data.convert_scene = True
data.convert_scene_unit = True
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task = u.AssetImportTask()
task.filename = str(HERE / 'Authored' / 'SM_BlastFurnace.fbx')
task.destination_path = ROOT
task.destination_name = 'SM_BlastFurnace'
task.automated = True
task.replace_existing = False
task.save = False
task.options = options
task.factory = u.FbxFactory()
ASSETS.import_asset_tasks([task])

mesh = u.load_asset(MESH_PATH)
if mesh is None:
    raise RuntimeError('Furnace mesh missing after import')
slots = []
for index, slot in enumerate(mesh.get_editor_property('static_materials')):
    raw = str(slot.get_editor_property('material_slot_name'))
    # The revision keeps the authored slot names; a suffix would mean the FBX
    # drifted and the mapping below would silently bind the wrong material.
    if raw not in MATERIAL_SPEC:
        raise RuntimeError('Unexpected slot name after import: ' + raw)
    mat = u.load_asset('%s/M_%s' % (MAT_ROOT, raw))
    if mat is None:
        raise RuntimeError('Required furnace material missing: ' + raw)
    mesh.set_material(index, mat)
    slots.append(raw)
if len(slots) != len(MATERIAL_SPEC):
    raise RuntimeError('Expected %d slots, got %d: %s' % (len(MATERIAL_SPEC), len(slots), slots))
mesh.get_editor_property('body_setup').set_editor_property(
    'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
nanite = mesh.get_editor_property('nanite_settings')
nanite.enabled = True
mesh.set_editor_property('nanite_settings', nanite)
save(mesh)

box = mesh.get_bounds()
size = [2 * box.box_extent.x, 2 * box.box_extent.y, 2 * box.box_extent.z]
# The 20 cm-lattice contract is a save contract; a silently rescaled import is
# the failure this assertion exists to catch.
for measured, expected in zip(size, (120.0, 100.0, 220.0)):
    if abs(measured - expected) > 0.5:
        raise RuntimeError('Imported mesh has the wrong scale: %s, expected 120/100/220' % size)
receipt['mesh'] = {'asset': mesh.get_path_name(), 'slots': slots,
                   'size_cm': [round(v, 3) for v in size],
                   'collision': 'CTF_USE_COMPLEX_AS_SIMPLE', 'nanite': True}
log('mesh reimported, size %s' % receipt['mesh']['size_cm'])

(HERE / 'revise_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('BLAST_FURNACE_REVISE_DONE ' + json.dumps(receipt, ensure_ascii=False), flush=True)
