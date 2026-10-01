"""Derive and save the wall's Fab ice material and four meshes. No game/preview."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SRC = ROOT / 'SourceAssets/IceWall20260930/FabIceV3'
DEST = '/Game/Skills/IceWall/FabIceV3'
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
saved = []
EAL.make_directory(DEST)

def save(asset):
    if not asset or not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Ice wall save failed: ' + str(asset))
    saved.append(asset.get_path_name())

path = DEST + '/M_IceWall'
mat = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset('/Game/Ice/Materials/M_Ice6', path)
if not mat:
    raise RuntimeError('The imported Fab M_Ice6 material is required')
mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_SUBSURFACE)
LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
# Rebuild only the project clone, using the imported material's original maps.
# This also makes an interrupted import safe to resume without stacking nodes.
source = u.load_asset('/Game/Ice/Materials/M_Ice6')
source_samples = [(e.get_editor_property('texture'), e.get_editor_property('sampler_type'))
                  for e in LIB.get_material_expressions(source) if isinstance(e, u.MaterialExpressionTextureSample)]
color_path = DEST + '/T_IceSurfaceColor'
color_texture = u.load_asset(color_path) if EAL.does_asset_exist(color_path) else EAL.duplicate_asset('/Game/Ice/Textures/T_Ice6_basecolor', color_path)
color_texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
color_texture.set_editor_property('srgb', True)
save(color_texture)
LIB.delete_all_material_expressions(mat)
samples = {}
for texture, sampler_type in source_samples:
    source_name = texture.get_name()
    if source_name == 'T_Ice6_basecolor':
        texture = color_texture
        sampler_type = u.MaterialSamplerType.SAMPLERTYPE_COLOR
    sample = LIB.create_material_expression(mat, u.MaterialExpressionTextureSample)
    sample.set_editor_property('texture', texture)
    sample.set_editor_property('sampler_type', sampler_type)
    samples[source_name] = sample

def node(cls):
    return LIB.create_material_expression(mat, cls)

def wire(source, channel, target, pin):
    if not LIB.connect_material_expressions(source, channel, target, pin):
        raise RuntimeError('Ice material input failed: ' + pin)

def output(source, channel, prop):
    if not LIB.connect_material_property(source, channel, prop):
        raise RuntimeError('Ice material output failed: ' + str(prop))

def custom(code, inputs, kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    n = node(u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    n.set_editor_property('output_type', kind)
    pins = []
    for key in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', key)
        pins.append(p)
    n.set_editor_property('inputs', pins)
    for key, (expr, channel) in inputs.items():
        wire(expr, channel, n, key)
    return n

def scalar(name, value):
    n = node(u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', value)
    return n

uv = node(u.MaterialExpressionTextureCoordinate)
random = node(u.MaterialExpressionPerInstanceRandom)
tiling = scalar('IceTextureScale', 1.05)
ice_uv = custom('return UV * Scale + float2(R*.73, R*1.31);',
                {'UV': (uv, ''), 'Scale': (tiling, ''), 'R': (random, '')}, u.CustomMaterialOutputType.CMOT_FLOAT2)
for sample in samples.values():
    wire(ice_uv, '', sample, 'UVs')
color = samples['T_Ice6_basecolor']
rough_map = samples['T_Ice6_roughness']
normal_map = samples['T_Ice6_normal']
ao_map = samples['T_Ice6_AO']
vertex = node(u.MaterialExpressionVertexColor)
frost_strength = scalar('FrostAmount', .42)
frost = custom('return saturate((V.r+V.g*.45)*Amount + saturate(Rough-.48)*.1);',
               {'V': (vertex, ''), 'Amount': (frost_strength, ''), 'Rough': (rough_map, 'R')})
camera = node(u.MaterialExpressionCameraVectorWS)
tangent = node(u.MaterialExpressionTransform)
tangent.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
tangent.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
wire(camera, '', tangent, '')
depth = scalar('InternalIceDepth', .025)
deep_uv = custom('return UV - clamp(V.xy/max(abs(V.z),.4),-1.5,1.5)*Depth;',
                 {'UV': (ice_uv, ''), 'V': (tangent, ''), 'Depth': (depth, '')}, u.CustomMaterialOutputType.CMOT_FLOAT2)
deep = node(u.MaterialExpressionTextureSample)
deep.set_editor_property('texture', color.get_editor_property('texture'))
deep.set_editor_property('sampler_type', color.get_editor_property('sampler_type'))
wire(deep_uv, '', deep, 'UVs')
base = custom('''float L=dot(C,float3(.2126,.7152,.0722));
float Inner=dot(D,float3(.2126,.7152,.0722));
float Cloud=saturate(pow(max(L,0),.8)*1.25);
float3 Core=lerp(float3(.065,.10,.125),float3(.29,.355,.385),Cloud);
Core*=clamp(1+(Inner-L)*.75,.87,1.08)*lerp(.97,1.03,R);
return lerp(Core,float3(.49,.535,.55),F);''',
              {'C': (color, 'RGB'), 'D': (deep, 'RGB'), 'F': (frost, ''), 'R': (random, '')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
rough = custom('return clamp(.11+R*.28+F*.3,.12,.47);', {'R': (rough_map, 'R'), 'F': (frost, '')})
normal_strength = scalar('IceNormalStrength', .48)
normal = custom('return normalize(float3(N.xy*Strength,N.z));',
                {'N': (normal_map, 'RGB'), 'Strength': (normal_strength, '')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
ao = custom('return .86+A*.14;', {'A': (ao_map, 'R')})
subsurface = custom('return C*float3(.65,.8,.86);', {'C': (base, '')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
output(base, '', u.MaterialProperty.MP_BASE_COLOR)
output(rough, '', u.MaterialProperty.MP_ROUGHNESS)
output(normal, '', u.MaterialProperty.MP_NORMAL)
output(ao, '', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
output(subsurface, '', u.MaterialProperty.MP_SUBSURFACE_COLOR)
for prop, value in ((u.MaterialProperty.MP_METALLIC, 0), (u.MaterialProperty.MP_SPECULAR, .23), (u.MaterialProperty.MP_OPACITY, .62)):
    constant = node(u.MaterialExpressionConstant)
    constant.set_editor_property('r', value)
    output(constant, '', prop)
compile_errors = LIB.recompile_material(mat)
if compile_errors:
    raise RuntimeError('Ice wall material compile failed: ' + '\n'.join(str(e) for e in compile_errors))
save(mat)
for index in range(1, 5):
    name = f'SM_IceBlock_{index:02d}'
    task = u.AssetImportTask()
    task.filename = str(SRC / (name + '.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    options = u.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.automated_import_should_detect_type = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.convert_scene_unit = True
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options = options
    TOOLS.import_asset_tasks([task])
    mesh = u.load_asset(DEST + '/' + name)
    mesh.set_material(0, mat)
    save(mesh)
receipt = ROOT / 'Saved/IceWallFabV3/assets-saved.json'
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps({'saved_assets': saved, 'source_material': '/Game/Ice/Materials/M_Ice6',
                               'source_maps': [s.get_editor_property('texture').get_path_name() for s in samples.values()],
                               'runtime_tested': False}, indent=2), encoding='utf-8')
print('ICE_WALL_FAB_V3_SAVED ' + str(receipt))
