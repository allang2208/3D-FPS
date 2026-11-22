"""Save the bakery's fitted joinery, repainted village sign and food display poses."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT/'SourceAssets/HillsVillageBakery/Furnishings'
DEST = '/Game/WorldGeneration/TemperateHills/VillageBakery/Furnishings'
TAVERN_SIGN = '/Game/WorldGeneration/VillageTavern/Sign/'
E = u.EditorAssetLibrary
M = u.MaterialEditingLibrary
API = u.AssetToolsHelpers.get_asset_tools()
E.make_directory(DEST)
saved = []

def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save ' + obj.get_path_name())
    saved.append(obj.get_path_name())

def require(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing source ' + path)
    return obj

def duplicate(source, dest):
    path = DEST+'/'+dest
    obj = u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)
    if not obj:
        raise RuntimeError('Could not copy ' + source)
    return obj

def bring(name, suffix, options=None):
    task = u.AssetImportTask()
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.destination_path = DEST
    task.destination_name = name
    task.filename = str(SOURCE/(name+suffix))
    if options:
        task.options = options
        task.factory = u.FbxFactory()
    API.import_asset_tasks([task])
    return require(DEST+'/'+name)

textures = {}
for suffix in ('Color','Normal','ORM'):
    texture = bring('T_BakerySign_'+suffix,'.png')
    texture.srgb = suffix == 'Color'
    if suffix != 'Color':
        texture.compression_settings = (u.TextureCompressionSettings.TC_NORMALMAP
                                        if suffix == 'Normal' else u.TextureCompressionSettings.TC_MASKS)
    textures[suffix] = texture
    save(texture)
mat = duplicate(TAVERN_SIGN+'M_TavernSign','M_BakerySign')
for expr in M.get_material_expressions(mat):
    if isinstance(expr,u.MaterialExpressionTextureSample) and expr.texture:
        suffix = expr.texture.get_name().rsplit('_',1)[-1]
        expr.texture = textures[suffix]
mat.set_editor_property('used_with_instanced_static_meshes', True)
M.recompile_material(mat)
save(mat)
sign = duplicate(TAVERN_SIGN+'SM_TavernSign','SM_BakerySign')
sign.set_material(0, mat)
save(sign)

# These scans were built upright for the character's hand. Bake the placement
# of each donor LOD into a shop-only display mesh, retaining its actual finish.
G = u.GeometryScript_AssetUtils
mesh_api = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for label in ('Bread','Baguette'):
    donor_path = f'/Game/Items/Consumables/{label}20261003/SM_{label}'
    donor = require(donor_path)
    target = duplicate(donor_path, f'SM_BakeryCounter{label}')
    for lod in range(mesh_api.get_lod_count(donor)):
        read = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod)
        dynamic,status = G.copy_mesh_from_static_mesh(donor,u.DynamicMesh(),
                u.GeometryScriptCopyMeshFromAssetOptions(),read)
        if status != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError(f'Could not read {label} LOD {lod}')
        u.GeometryScript_MeshTransforms.rotate_mesh(dynamic, u.Rotator(pitch=90))
        opts = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True, replace_materials=True,
                new_materials=[s.material_interface for s in donor.static_materials],
                new_material_slot_names=[s.material_slot_name for s in donor.static_materials])
        _,status = G.copy_mesh_to_static_mesh(dynamic,target,opts,u.GeometryScriptMeshWriteLOD(lod_index=lod))
        if status != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError(f'Could not save {label} LOD {lod}')
    mesh_api.remove_collisions(target)
    save(target)

HILLS = '/Game/WorldGeneration/TemperateHills/'
surfaces = {
    'Oak': HILLS+'VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak',
    'Endgrain': HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterCut',
    'Sawn': HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterSawn',
    'OiledOak': '/Game/WorldGeneration/VillageTavern/Furniture/M_TavernOiledOak',
    'Iron': HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterIron',
}
for name in ('SM_BakeryCoolingBoard','SM_BakeryPeelHanger'):
    opts = u.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_mesh = True
    opts.import_as_skeletal = False
    opts.import_materials = False
    opts.import_textures = False
    data = opts.static_mesh_import_data
    data.combine_meshes = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.auto_generate_collision = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh = bring(name,'.fbx',opts)
    for i, slot in enumerate(mesh.static_materials):
        key = str(slot.get_editor_property('imported_material_slot_name'))
        mesh.set_material(i, require(surfaces[key]))
    save(mesh)
(SOURCE/'saved.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
u.log('BAKERY_FURNISHING_PACKAGES_SAVED')
