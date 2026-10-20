"""Import and save isolated R8 surface assets; retain the accepted R7 V9 profile."""
import json, copy, hashlib, runpy
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
ROOT = '/Game/Weapons/SVCH/Refined20261018/R8Surface'
MESH = ROOT + '/SK_SVCH_R8Surface'
DONOR = '/Game/Weapons/SVCH/Refined20261018/R5/SK_SVCH_Refined_R5'
PROFILE = '/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
receipt = {'complete': False, 'saved': [], 'runtime_tested': False,
           'profile_preserved': PROFILE, 'animations_modified': False}

def checkpoint():
    (O / 'install_receipt.json').write_text(json.dumps(receipt, indent=2))

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing asset: ' + path)
    return asset

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    checkpoint()

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is running; preserve current session')
if E.does_asset_exist(MESH):
    raise RuntimeError('R8 mesh already exists; preserve installed revision')

donor = load(DONOR)
load(PROFILE)  # Accepted R7 profile is referenced, never regenerated from R5 data.
source_materials = {str(s.material_slot_name): s.material_interface for s in donor.materials}
maps = json.loads((O / 'texture_receipt.json').read_text())['parts']
textures = {}
for part, row in maps.items():
    textures[part] = {}
    for kind in ('normal', 'roughness', 'surface_mask'):
        task = u.AssetImportTask()
        task.filename = row[kind]
        task.destination_path = ROOT + '/Textures'
        task.automated = True
        task.replace_existing = True
        task.save = False
        A.import_asset_tasks([task])
        tex = load(ROOT + '/Textures/' + Path(row[kind]).stem)
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP
                                if kind == 'normal' else u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR)
        tex.set_editor_property('compression_settings',
            u.TextureCompressionSettings.TC_NORMALMAP if kind == 'normal'
            else u.TextureCompressionSettings.TC_MASKS if kind == 'surface_mask'
            else u.TextureCompressionSettings.TC_GRAYSCALE)
        if kind == 'normal':
            tex.set_editor_property('flip_green_channel', True)
        save(tex)
        textures[part][kind] = tex

colors = {'Body': (.027, .030, .033), 'BarrelSteel': (.045, .047, .050),
          'BoltCarrier': (.10, .105, .11), 'Polymer': (.021, .023, .022),
          'Magazine': (.024, .025, .023), 'Rubber': (.009, .010, .010),
          'MagRelease': (.027, .030, .033), 'Selector': (.027, .030, .033)}
materials = {}
receipt['material_parameters'] = {}
for identity, old in source_materials.items():
    if not identity.startswith('SVCH_'):
        materials[identity] = old
        continue
    part = identity.removeprefix('SVCH_')
    atlas = 'Body' if part in ('Body', 'Polymer', 'Rubber', 'BarrelSteel') else part
    path = ROOT + '/Materials/MI_SVCH_R8_' + part
    instance = u.load_asset(path) or E.duplicate_asset(old.get_path_name(), path)
    if not instance:
        raise RuntimeError('Cannot create local finish: ' + part)
    for param, kind in [('SurfaceNormal', 'normal'), ('SourceRoughness', 'roughness'),
                         ('SurfaceMask', 'surface_mask')]:
        L.set_material_instance_texture_parameter_value(instance, param, textures[atlas][kind])
    scalars = {'SourceRoughnessWeight': 1., 'SourceRoughnessPivot': .5, 'Roughness': .5,
               'MaskUVChannel': 0., 'GrainTileCm': 3.,
               'GrainRoughness': .006 if part in ('Polymer', 'Rubber', 'Magazine') else .004,
               'MottleRoughness': 0., 'MottleColor': 0., 'Stipple': 0.,
               'ScratchAmount': 0., 'HandlingPolish': 0., 'EdgeWear': 0.,
               'EdgeHighlight': .01, 'CavityDarken': .025, 'CavityRoughness': .01,
               'AOStrength': .35, 'BeadScale': 2.42 * maps[atlas]['cm_per_uv'][identity]}
    for param, value in scalars.items():
        L.set_material_instance_scalar_parameter_value(instance, param, value)
    if part in colors:
        L.set_material_instance_vector_parameter_value(instance, 'FinishColor', u.LinearColor(*colors[part], 1.))
    E.set_metadata_tag(instance, 'SVCHSurface', 'R8 local structural normal/AO/roughness; restrained WS1 finish')
    save(instance)
    materials[identity] = instance
    receipt['material_parameters'][identity] = {'atlas': atlas, 'scalars': scalars,
                                              'color': colors.get(part, 'preserved brass')}

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal = True
options.import_mesh = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
options.skeleton = donor.skeleton
options.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task = u.AssetImportTask()
task.filename = str(O / 'SK_SVCH_R8Surface.fbx')
task.destination_path = ROOT
task.destination_name = 'SK_SVCH_R8Surface'
task.automated = True
task.save = False
task.options = options
task.factory = u.FbxFactory()
A.import_asset_tasks([task])
mesh = load(MESH)
slots = list(mesh.materials)
if set(str(s.material_slot_name) for s in slots) != set(materials):
    raise RuntimeError('Imported material identities differ from R5')
for i, slot in enumerate(slots):
    slot.material_interface = materials[str(slot.material_slot_name)]
    slots[i] = slot
mesh.set_editor_property('materials', slots)
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
editor.set_lod_build_settings(mesh, 0, editor.get_lod_build_settings(donor, 0))
E.set_metadata_tag(mesh, 'Attribution', E.get_metadata_tag(donor, 'Attribution'))
E.set_metadata_tag(mesh, 'SVCHRevision', 'R8 surface refinement; original interfaces and native V9 arms retained')
save(mesh)
runpy.run_path(str(O.parent / 'install_arm_correctives.py'), init_globals={
    'TARGET_MESH': MESH, 'RECEIPT_PATH': O / 'arm_correctives_receipt.json'})

# Re-read immediately before the narrow table addition to preserve parallel work.
table = P / 'Content/ColdSteelData/modular_outfits.json'
data = json.loads(table.read_text(encoding='utf-8-sig'))
entry = copy.deepcopy(data['profiles'][donor.get_path_name()])
arm_slots = [i for i, slot in enumerate(slots) if str(slot.material_slot_name).startswith('MI_Manny_')]
entry['hide_source_materials'] = arm_slots
data['profiles'][mesh.get_path_name()] = entry
table.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
receipt.update(complete=True, mesh=mesh.get_path_name(), profile=PROFILE,
               materials=[str(slot.material_slot_name) for slot in slots], arm_slots=arm_slots,
               outfit_profile=entry,
               fbx_sha256=hashlib.sha256((O / 'SK_SVCH_R8Surface.fbx').read_bytes()).hexdigest())
checkpoint()
print('SVCH_R8_ASSETS_SAVED', mesh.get_path_name(), flush=True)
