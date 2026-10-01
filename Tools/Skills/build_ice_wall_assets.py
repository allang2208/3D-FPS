"""Import and save IceWall/BlockV1 through Unreal's Python commandlet. No gameplay/render."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SRC = ROOT / 'SourceAssets/IceWall20260930'
DEST = '/Game/Skills/IceWall/BlockV1'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
EAL.make_directory(DEST)
saved = []

def save(asset):
    if not asset or not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('IceWall asset save failed: ' + str(asset))
    saved.append(asset.get_path_name())

def material(name):
    path = DEST + '/' + name
    asset = u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(asset)
    return asset

def node(mat, cls):
    return LIB.create_material_expression(mat, cls)

def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('IceWall material pin failed: ' + pin)

def output(source, prop):
    if not LIB.connect_material_property(source, '', prop):
        raise RuntimeError('IceWall material output failed: ' + str(prop))

def custom(mat, code, inputs, vector=False):
    n = node(mat, u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    n.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3 if vector else u.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for name in inputs:
        pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    n.set_editor_property('inputs', pins)
    for name, (src, channel) in inputs.items():
        wire(src, channel, n, name)
    return n

ice = material('M_IceWall')
ice.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
ice.set_editor_property('shading_model', u.MaterialShadingModel.MSM_SUBSURFACE)
LIB.set_material_usage(ice, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
uv = node(ice, u.MaterialExpressionTextureCoordinate)
texture = node(ice, u.MaterialExpressionTextureObject)
texture.set_editor_property('texture', u.load_asset('/Game/Skills/IceSpike/T_IceCracks'))
vertex = node(ice, u.MaterialExpressionVertexColor)
crack = custom(ice, 'return saturate(Texture2DSample(T,TSampler,UV*2.1).r*.65+Texture2DSample(T,TSampler,UV*2.1+.017).g*.35);', {'T': (texture, ''), 'UV': (uv, '')})
tint = custom(ice, 'return lerp(float3(.115,.275,.34),float3(.61,.77,.81),saturate(C*.7+F*.28));', {'C': (crack, ''), 'F': (vertex, 'R')}, True)
output(tint, u.MaterialProperty.MP_BASE_COLOR)
rough = custom(ice, 'return lerp(.31,.48,saturate(C*.8+F*.3));', {'C': (crack, ''), 'F': (vertex, 'R')})
output(rough, u.MaterialProperty.MP_ROUGHNESS)
normal = custom(ice, '''float2 p=UV*2.1; float e=.0015;
float a=Texture2DSample(T,TSampler,p+float2(e,0)).r-Texture2DSample(T,TSampler,p-float2(e,0)).r;
float b=Texture2DSample(T,TSampler,p+float2(0,e)).r-Texture2DSample(T,TSampler,p-float2(0,e)).r;
return normalize(float3(a*.16,b*.16,1));''', {'T': (texture, ''), 'UV': (uv, '')}, True)
output(normal, u.MaterialProperty.MP_NORMAL)
for prop, value in [(u.MaterialProperty.MP_SPECULAR, .3), (u.MaterialProperty.MP_OPACITY, .23)]:
    n = node(ice, u.MaterialExpressionConstant); n.set_editor_property('r', value); output(n, prop)
sub = node(ice, u.MaterialExpressionConstant3Vector); sub.set_editor_property('constant', u.LinearColor(.34,.66,.75,1)); output(sub, u.MaterialProperty.MP_SUBSURFACE_COLOR)
LIB.recompile_material(ice); save(ice)

preview = material('M_IceWallPreview')
preview.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
preview.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
preview.set_editor_property('two_sided', True)
preview.set_editor_property('output_translucent_velocity', False)
preview.set_editor_property('disable_depth_test', False)
LIB.set_material_usage(preview, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
tint = node(preview, u.MaterialExpressionVectorParameter)
tint.set_editor_property('parameter_name', 'Tint'); tint.set_editor_property('default_value', u.LinearColor(.08,.8,.38,1))
output(tint, u.MaterialProperty.MP_EMISSIVE_COLOR)
alpha = node(preview, u.MaterialExpressionConstant); alpha.set_editor_property('r', .36); output(alpha, u.MaterialProperty.MP_OPACITY)
LIB.recompile_material(preview); save(preview)

for index in range(1, 5):
    name = f'SM_IceBlock_{index:02d}'
    task = u.AssetImportTask(); task.filename = str(SRC / (name + '.fbx'))
    task.destination_path = DEST; task.destination_name = name; task.automated = True; task.replace_existing = True; task.save = True
    options = u.FbxImportUI(); options.import_mesh = True; options.import_materials = False; options.import_textures = False
    options.automated_import_should_detect_type = False
    options.import_as_skeletal = False; options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data; data.combine_meshes = True; data.auto_generate_collision = False
    data.convert_scene_unit = True
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options = options; TOOLS.import_asset_tasks([task])
    mesh = u.load_asset(DEST + '/' + name)
    if not mesh: raise RuntimeError('IceWall block import failed: ' + name)
    mesh.set_material(0, ice)
    save(mesh)

# Original cast audio is retained as a local migration dependency.
sound = SRC / 'icewall.wav'
if sound.exists():
    task = u.AssetImportTask(); task.filename = str(sound); task.destination_path = DEST
    task.destination_name = 'S_IceWallCast'; task.automated = True; task.replace_existing = True; task.save = True
    TOOLS.import_asset_tasks([task]); save(u.load_asset(DEST + '/S_IceWallCast'))

receipt = ROOT / 'Saved/IceWall20260930/assets-saved.json'
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps({'saved_assets': saved, 'runtime_tested': False}, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('ICE_WALL_ASSETS_SAVED ' + str(receipt))
