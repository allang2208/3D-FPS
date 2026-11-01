"""Author/save the owner-local physical scope material. Original mesh is untouched."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
D = '/Game/Weapons/M24/PhysicalScope20261030'
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
report = {'complete': False, 'saved': [], 'runtime_tested': False, 'original_mesh_changed': False}

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    (O / 'install_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

dirty = {str(p.get_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):
    raise RuntimeError('Unsaved physical lens authoring exists; preserving it')

task = u.AssetImportTask()
task.filename = str(O / 'T_M24_MilLabels.png')
task.destination_path = D
task.destination_name = 'T_M24_MilLabels'
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
labels = u.load_asset(D + '/T_M24_MilLabels')
labels.srgb = False
labels.compression_settings = u.TextureCompressionSettings.TC_MASKS
labels.lod_group = u.TextureGroup.TEXTUREGROUP_WEAPON
labels.address_x = u.TextureAddress.TA_CLAMP
labels.address_y = u.TextureAddress.TA_CLAMP
save(labels)

path = D + '/M_M24_PhysicalLens'
material = u.load_asset(path) if E.does_asset_exist(path) else A.create_asset('M_M24_PhysicalLens', D, u.Material, u.MaterialFactoryNew())
L.delete_all_material_expressions(material)

def node(cls, **props):
    n = L.create_material_expression(material, cls)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n

def wire(source, output, target, pin):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Material input failed: ' + pin)

def custom(code, inputs, result=u.CustomMaterialOutputType.CMOT_FLOAT1):
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    n = node(u.MaterialExpressionCustom, code=code, output_type=result,
             inputs=pins)
    for name, (source, output) in inputs.items():
        wire(source, output, n, name)
    return n

def scalar(name, value):
    return node(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)

screen = node(u.MaterialExpressionScreenPosition)
scale = node(u.MaterialExpressionVectorParameter, parameter_name='ScreenToLens', default_value=u.LinearColor(4, 2.25, 0, 0))
fov = scalar('CaptureTanHalfFOV', .025)
blend = scalar('LensBlend', 0)
scene = node(u.MaterialExpressionTextureObjectParameter, parameter_name='ScopeScene', texture=u.load_asset('/Engine/EngineResources/Black'))
numbers = node(u.MaterialExpressionTextureObjectParameter, parameter_name='MilLabels', texture=labels)
picture = custom((O / 'lens.hlsl').read_text(encoding='utf-8'), {
    'ScreenUV': (screen, 'ViewportUV'), 'ScreenToLens': (scale, 'RGB'),
    'CaptureTanHalfFOV': (fov, ''), 'Scene': (scene, ''), 'Labels': (numbers, '')
}, u.CustomMaterialOutputType.CMOT_FLOAT3)
local = node(u.MaterialExpressionPreSkinnedPosition)
interpolated = node(u.MaterialExpressionVertexInterpolator)
wire(local, '', interpolated, 'VS')
# Both lens ends share the original material slot. Only the rear glass displays
# the capture; the objective retains its coating. Native mesh local Y is -forward.
alpha = custom('return saturate(Blend) * step(-20.0, LocalPosition.y);',
               {'Blend': (blend, ''), 'LocalPosition': (interpolated, '')})
fresnel = node(u.MaterialExpressionFresnel, exponent=4.0, base_reflect_fraction=0.0)
opacity = custom('return lerp(lerp(.018,.22,Fresnel),1,Alpha);', {'Fresnel': (fresnel, ''), 'Alpha': (alpha, '')})
emissive = custom('return Picture * Alpha / max(Opacity,.001);',
                  {'Picture': (picture, ''), 'Alpha': (alpha, ''), 'Opacity': (opacity, '')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
base = custom('return float3(.08,.18,.20) * (1-Alpha);', {'Alpha': (alpha, '')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
spec = custom('return .5 * (1-Alpha);', {'Alpha': (alpha, '')})
rough = node(u.MaterialExpressionConstant, r=.045)
zero = node(u.MaterialExpressionConstant, r=0)
normal = node(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(0, 0, 1, 1))
for n, output, prop in [
    (emissive, '', u.MaterialProperty.MP_EMISSIVE_COLOR),
    (base, '', u.MaterialProperty.MP_BASE_COLOR),
    (opacity, '', u.MaterialProperty.MP_OPACITY),
    (rough, '', u.MaterialProperty.MP_ROUGHNESS),
    (spec, '', u.MaterialProperty.MP_SPECULAR),
    (zero, '', u.MaterialProperty.MP_METALLIC),
    (normal, '', u.MaterialProperty.MP_NORMAL),
]:
    if not L.connect_material_property(n, output, prop):
        raise RuntimeError('Material output failed: ' + str(prop))
material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property('two_sided', True)
material.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
material.set_editor_property('automatically_set_usage_in_editor', False)
# Before DOF, so the physical gun and lens share depth, exposure and resolution.
material.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
errors = L.recompile_material(material)
if errors:
    raise RuntimeError('Physical lens material compile failed: ' + str(errors))
save(material)
report['complete'] = True
(O / 'install_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('M24_PHYSICAL_LENS_SAVED', json.dumps(report), flush=True)
