"""Build only the independent wall relief materials through the shared UE bridge."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Dungeons/AtmosphereV2/WallRelief'
CFG = json.loads((ROOT/'Config/surface.json').read_text())
MAN = json.loads((ROOT/'Authored/material-manifest.json').read_text())
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if not editor or editor.get_game_world():
    raise RuntimeError('Use the editor outside gameplay for wall authoring')
dirty = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
RESUME_GRAPH = globals().get('WALL_RESUME_MATERIAL_GRAPH', False)
owned_graph = BASE+'/Materials/M_WallMortarRelief'
if any(p.startswith(BASE+'/') and not (RESUME_GRAPH and p == owned_graph) for p in dirty):
    raise RuntimeError('Preserve unsaved wall-relief edits before rebuilding')
(ROOT/'Receipts').mkdir(exist_ok=True)
receipt = dict(saved=[], tests_run=False, stage='authoring_materials')


def write():
    (ROOT/'Receipts/materials.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Unable to save '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name())
    write()


textures = {}
samplers = {}
for channel, filename in MAN['channels'].items():
    name = 'T_WallMortar_'+channel
    task = u.AssetImportTask()
    task.filename = filename
    task.destination_path = BASE+'/Textures'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    if not RESUME_GRAPH:
        A.import_asset_tasks([task])
    tex = u.load_asset(task.destination_path+'/'+name)
    if not tex:
        raise RuntimeError('Import failed '+name)
    tex.set_editor_property('srgb', channel == 'BaseColor')
    if channel == 'Normal':
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel', True)
        samplers[channel] = u.MaterialSamplerType.SAMPLERTYPE_NORMAL
    elif channel == 'Height':
        # The authored 16-bit height remains a scalar float texture rather than
        # block-compressed colour, which would staircase shallow wall relief.
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_HALF_FLOAT)
        samplers[channel] = u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    elif channel == 'Surface':
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
        samplers[channel] = u.MaterialSamplerType.SAMPLERTYPE_MASKS
    else:
        samplers[channel] = u.MaterialSamplerType.SAMPLERTYPE_COLOR
    save(tex)
    textures[channel] = tex

name = 'M_WallMortarRelief'
mat = u.load_asset(BASE+'/Materials/'+name)
if not mat:
    mat = A.create_asset(name, BASE+'/Materials', u.Material, u.MaterialFactoryNew())
mat.modify()
L.delete_all_material_expressions(mat)


def node(cls):
    return L.create_material_expression(mat, cls)


def wire(source, target, pin='', output=''):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Unable to connect '+pin)


def output(source, prop, pin=''):
    if not L.connect_material_property(source, pin, getattr(u.MaterialProperty, 'MP_'+prop)):
        raise RuntimeError('Unable to connect output '+prop)


def scalar(name, value):
    n = node(u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', value)
    return n


def custom(code, inputs, width):
    n = node(u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT'+str(width)))
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for key, source in inputs.items():
        wire(source, n, key)
    return n


objects = {}
for channel, tex in textures.items():
    n = node(u.MaterialExpressionTextureObjectParameter)
    n.set_editor_property('parameter_name', channel+'Texture')
    n.set_editor_property('texture', tex)
    n.set_editor_property('sampler_type', samplers[channel])
    objects[channel] = n
uv = node(u.MaterialExpressionTextureCoordinate)
camera = node(u.MaterialExpressionCameraVectorWS)
view = node(u.MaterialExpressionTransform)
view.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
view.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
wire(camera, view)
position = node(u.MaterialExpressionWorldPosition)
camera_pos = node(u.MaterialExpressionCameraPositionWS)
distance = node(u.MaterialExpressionDistance)
wire(position, distance, 'A')
wire(camera_pos, distance, 'B')
depth = scalar('WallReliefDepthCm', CFG['relief_depth_cm'])
shifted = custom((ROOT/'Scripts/wall_relief.hlsl').read_text(), dict(
    UV=uv, View=view, HeightTex=objects['Height'], DistanceCm=distance, DepthCm=depth,
    TileCm=scalar('WallTileSizeCm', CFG['tile_size_cm']), Steps=scalar('WallReliefSteps', CFG['relief_steps']),
    RefineSteps=scalar('WallReliefRefineSteps', CFG['relief_refine_steps']),
    FadeStart=scalar('WallReliefFadeStartCm', CFG['relief_fade_start_cm']),
    FadeEnd=scalar('WallReliefFadeEndCm', CFG['relief_fade_end_cm'])), 2)
sample = 'Texture2DSampleGrad(Tex,TexSampler,UV,ddx(GradUV),ddy(GradUV))'
base = custom('return '+sample+'.rgb;', dict(Tex=objects['BaseColor'], UV=shifted, GradUV=uv), 3)
surface = custom('return '+sample+'.rgb;', dict(Tex=objects['Surface'], UV=shifted, GradUV=uv), 3)
normal = custom('float3 n=UnpackNormalMap('+sample+'); return normalize(float3(n.xy*Strength,n.z));',
                dict(Tex=objects['Normal'], UV=shifted, GradUV=uv, Strength=scalar('WallNormalStrength', 1)), 3)
color = custom('float variation=sin(P.x*.0037+P.z*.0013)*sin(P.y*.0043-P.z*.0021); '
               'return Base*(1+variation*MacroAmount);',
               dict(P=position, Base=base, MacroAmount=scalar('WallMacroAmount', .035)), 3)
output(color, 'BASE_COLOR')
output(normal, 'NORMAL')
output(custom('return Surface.r;', dict(Surface=surface), 1), 'ROUGHNESS')
output(custom('return Surface.g;', dict(Surface=surface), 1), 'AMBIENT_OCCLUSION')
output(scalar('WallSpecular', .27), 'SPECULAR')
L.layout_material_expressions(mat)
L.recompile_material(mat)
save(mat)

receipt['instances'] = {}
import sys
sys.path.insert(0,str(ROOT.parents[1]/'Tools/AssetPipeline'))
import dungeon_wall_release
for name, relief, normal_strength in [('Bed', CFG['relief_depth_cm'], 1), ('Finish', .065, .10)]:
    asset_name = 'MI_WallMortar_'+name
    mi = u.load_asset(BASE+'/Materials/'+asset_name)
    if not mi:
        mi = A.create_asset(asset_name, BASE+'/Materials', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    mi.modify()
    L.set_material_instance_parent(mi, mat)
    L.set_material_instance_scalar_parameter_value(mi, 'WallReliefDepthCm', relief)
    L.set_material_instance_scalar_parameter_value(mi, 'WallNormalStrength', normal_strength)
    dungeon_wall_release.apply_instance(mi,save_asset=False)
    L.update_material_instance(mi)
    save(mi)
    receipt['instances'][name] = mi.get_path_name()
receipt.update(stage='materials_saved', saved_at=datetime.now().isoformat())
write()
print('WALL_RELIEF_MATERIALS_SAVED '+json.dumps(receipt))
