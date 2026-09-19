"""Author relief-mapped river ground and small, embedded round-stone variants.

Uses already-local scan maps and the existing WaterMaterials round rock mesh.
Run with the updated FPSGAMEEditor module; no map or gameplay is launched.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
CACHE = ROOT.parent / 'VaultCache/FabLibrary'
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE + '/PebbleShore'
OUT = ROOT / 'Saved/PebbleShore20260914'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / ('BeforeAuthoring-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
REPORT = {'scope': 'Asset authoring and integration; no gameplay or visual tests',
          'sources': [], 'saved': [], 'pebbles': []}
EAL.make_directory(DEST)


def load(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Missing pebble shore source: ' + path)
    return obj


def backup(path):
    source = ROOT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    if source.exists():
        target = BACKUP / source.relative_to(ROOT / 'Content')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def copy(source, target):
    backup(target)
    obj = load(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source, target)
    if obj is None:
        raise RuntimeError('Unable to duplicate ' + source)
    return obj


def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Unable to save ' + obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())
    return obj


def node(mat, cls):
    return LIB.create_material_expression(mat, cls)


def wire(source, target, pin):
    if not LIB.connect_material_expressions(source, '', target, pin):
        raise RuntimeError('Material connection failed: ' + pin)


def prop(source, name):
    if not LIB.connect_material_property(source, '', getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Material output failed: ' + name)


def custom(mat, code, inputs, width=3):
    expr = node(mat, u.MaterialExpressionCustom)
    expr.set_editor_property('code', code)
    expr.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    expr.set_editor_property('inputs', pins)
    for name, source in inputs.items():
        wire(source, expr, name)
    return expr


def scalar(mat, name, value):
    expr = node(mat, u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name', name)
    expr.set_editor_property('default_value', value)
    return expr


def sample(mat, texture, uv, normal=False):
    expr = node(mat, u.MaterialExpressionTextureSample)
    expr.set_editor_property('texture', texture)
    expr.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else
                             u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.get_editor_property('srgb') else
                             u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    expr.set_editor_property('sampler_source', u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    wire(uv, expr, 'UVs')
    return expr


def import_map(folder, prefix, kind):
    source = next((CACHE / folder).rglob('*_' + kind + '.jpg'))
    path = DEST + '/T_' + prefix + '_' + kind
    backup(path)
    if EAL.does_asset_exist(path):
        tex = load(path)
    else:
        task = u.AssetImportTask()
        task.set_editor_property('filename', str(source))
        task.set_editor_property('destination_path', DEST)
        task.set_editor_property('destination_name', 'T_' + prefix + '_' + kind)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', False)
        TOOLS.import_asset_tasks([task])
        tex = load(path)
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('max_texture_size', 2048)
    REPORT['sources'].append({'file': str(source), 'asset': path})
    return save(tex)


maps = []
for folder, prefix in [('Shoreline_Beach_Rocks-1a759058', 'RiverShore'),
                       ('Small_Pebbles_Ground-a0e6a70f', 'RiverPebbles')]:
    maps.append({**{kind: load(BASE + '/Rivers/T_' + prefix + '_' + kind)
                    for kind in ('BaseColor', 'Normal', 'Roughness')},
                 **{kind: import_map(folder, prefix, kind) for kind in ('Displacement', 'AO')}})

config_path = BASE + '/DA_TemperateHillsStreaming'
assets = load(config_path)
ground_source = assets.get_editor_property('ground_material')
ground = copy(ground_source.get_path_name(), DEST + '/M_PebbleShoreGround')

# Retain the current hill/grass/soil/weather graph outside the river. The
# existing three outputs have explicit A=hill, B=river, M=vertex-mask inputs.
old = {}
outputs = {}
for name in ('BASE_COLOR', 'NORMAL', 'ROUGHNESS'):
    output = LIB.get_material_property_input_node(ground, getattr(u.MaterialProperty, 'MP_' + name))
    pins = [str(n) for n in LIB.get_material_expression_input_names(output)]
    upstream = LIB.get_inputs_for_material_expression(ground, output)
    if pins != ['A', 'B', 'M']:
        raise RuntimeError('River ground output is not the expected hill/river blend: ' + name)
    old[name] = upstream[0]
    outputs[name] = output

world = node(ground, u.MaterialExpressionWorldPosition)
view = node(ground, u.MaterialExpressionCameraVectorWS)
camera = node(ground, u.MaterialExpressionCameraPositionWS)
mask = node(ground, u.MaterialExpressionVertexColor)
wet = scalar(ground, 'Wetness', 0)
blend = custom(ground, 'return lerp(.88,.12,saturate(M.b*1.2));', {'M': mask}, 1)
height_objects = []
for texset in maps:
    obj = node(ground, u.MaterialExpressionTextureObject)
    obj.set_editor_property('texture', texset['Displacement'])
    obj.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    height_objects.append(obj)

# Bounded, distance-faded height-field ray marching, using explicit derivatives
# inside the loop. The 2 m world projection matches both scans' physical size.
uv = custom(ground, '''
float2 base=P.xy/200.0;
float2 gx=ddx(base), gy=ddy(base);
float amount=saturate(M.r)*saturate(1-smoothstep(900,1800,length(Camera-P)))*smoothstep(.08,.28,V.z);
float relief=HeightCm*amount;
if(relief<.001) return base;
float2 travel=V.xy/max(V.z,.12)*relief/200.0;
int steps=(int)lerp(20.0,8.0,saturate(V.z));
float dt=1.0/steps;
float ray=0, previousRay=0, previousGap=1, gap=1;
[loop] for(int i=0;i<=20;++i)
{
    float2 at=base-travel*ray;
    float a=Texture2DSampleGrad(H0,H0Sampler,at,gx,gy).r;
    float b=Texture2DSampleGrad(H1,H1Sampler,at,gx,gy).r;
    float weight=saturate((Blend+(b-a)*.28-.43)/.14);
    gap=1-lerp(a,b,weight)-ray;
    if(gap<=0 || i==steps) break;
    previousRay=ray;previousGap=gap;ray+=dt;
}
float hit=lerp(previousRay,ray,saturate(previousGap/max(previousGap-gap,.0001)));
return base-travel*hit;
''', {'P': world, 'Camera': camera, 'V': view, 'M': mask, 'Blend': blend,
      'HeightCm': scalar(ground, 'PebbleReliefDepthCm', 5.0),
      'H0': height_objects[0], 'H1': height_objects[1]}, 2)

samples = [{kind: sample(ground, texture, uv, normal=kind == 'Normal') for kind, texture in texset.items()}
           for texset in maps]
height_blend = custom(ground, 'return saturate((Blend+(B.r-A.r)*.28-.43)/.14);',
                      {'Blend': blend, 'A': samples[0]['Displacement'], 'B': samples[1]['Displacement']}, 1)
ao = custom(ground, 'return clamp(lerp(A.r,B.r,T),.30,1);',
            {'A': samples[0]['AO'], 'B': samples[1]['AO'], 'T': height_blend}, 1)
bank_color = custom(ground, '''
float damp=max(M.g,saturate(Wet));
float macro=.95+.05*sin(P.x*.00073+sin(P.y*.00053));
return lerp(A,B,T)*macro*lerp(1.0,.62,damp)*lerp(.88,1.0,AO);
''', {'A': samples[0]['BaseColor'], 'B': samples[1]['BaseColor'], 'T': height_blend,
      'M': mask, 'Wet': wet, 'P': world, 'AO': ao})
bank_normal = custom(ground, 'float3 n=normalize(lerp(A,B,T)); return normalize(float3(n.xy*Strength,n.z));',
                     {'A': samples[0]['Normal'], 'B': samples[1]['Normal'], 'T': height_blend,
                      'Strength': scalar(ground, 'PebbleNormalStrength', 1.10)})
bank_rough = custom(ground, 'return lerp(clamp(lerp(A.r,B.r,T),.53,.94),.25,max(M.g,saturate(Wet)));',
                    {'A': samples[0]['Roughness'], 'B': samples[1]['Roughness'], 'T': height_blend,
                     'M': mask, 'Wet': wet}, 1)
for name, bank in [('BASE_COLOR', bank_color), ('NORMAL', bank_normal), ('ROUGHNESS', bank_rough)]:
    wire(bank, outputs[name], 'B')
prop(custom(ground, 'return lerp(1.0,AO,saturate(M.r));', {'AO': ao, 'M': mask}, 1), 'AMBIENT_OCCLUSION')
LIB.recompile_material(ground)
save(ground)

source_mesh = load('/Game/WaterMaterials/Meshes/SM_River_Rock')
source_material = source_mesh.get_editor_property('static_materials')[0].material_interface
mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
pebbles = []
for name, tint, roughness in [('Wet', (.54,.55,.52), .26), ('Grey', (.77,.78,.74), .68), ('Warm', (.83,.75,.64), .72)]:
    mat = copy(source_material.get_path_name(), DEST + '/M_RoundPebble_' + name)
    mat.set_editor_property('used_with_instanced_static_meshes', True)
    original_color = LIB.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
    if original_color.get_editor_property('desc') != 'PebbleColourVariation':
        colored = custom(mat, 'return C*Tint;', {'C': original_color,
            'Tint': custom(mat, 'return float3(%s,%s,%s);' % tint, {})})
        colored.set_editor_property('desc', 'PebbleColourVariation')
        prop(colored, 'BASE_COLOR')
    prop(scalar(mat, 'PebbleRoughness', roughness), 'ROUGHNESS')
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED)
    prop(node(mat, u.MaterialExpressionPerInstanceFadeAmount), 'OPACITY_MASK')
    LIB.recompile_material(mat)
    save(mat)
    mesh = copy(source_mesh.get_path_name(), DEST + '/SM_RoundPebble_' + name)
    mesh.set_material(0, mat)
    mesh_editor.remove_collisions(mesh)
    reduction = u.StaticMeshReductionOptions()
    reduction.set_editor_property('auto_compute_lod_screen_size', False)
    settings = []
    for percent, screen in ((1.0, 1.0), (.50, .15), (.20, .045)):
        setting = u.StaticMeshReductionSettings()
        setting.set_editor_property('percent_triangles', percent)
        setting.set_editor_property('screen_size', screen)
        settings.append(setting)
    reduction.set_editor_property('reduction_settings', settings)
    mesh_editor.set_lods(mesh, reduction)
    save(mesh)
    pebbles.append(mesh)
    REPORT['pebbles'].append({'source': source_mesh.get_path_name(), 'copy': mesh.get_path_name(), 'variant': name})

backup(config_path)
assets.set_editor_property('ground_material', ground)
assets.set_editor_property('river_pebbles', pebbles)
assets.set_editor_property('river_bank_relief_cm', 22.0)
assets.set_editor_property('river_pebble_spacing_cm', 85.0)
assets.set_editor_property('river_pebble_coverage', .78)
save(assets)
REPORT['configuration'] = assets.get_path_name()
REPORT['parameters'] = {'bank_relief_cm': 22, 'pebble_candidate_spacing_cm': 85,
                        'pebble_coverage': .78, 'parallax_depth_cm': 5,
                        'parallax_fade_m': [9,18], 'individual_stone_length_cm': [7,22]}
(OUT / 'authoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('PEBBLE_SHORE_AUTHORING_COMPLETE')
