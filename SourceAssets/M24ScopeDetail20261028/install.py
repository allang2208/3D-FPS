"""Save factory M24 optic finish and coated lenses; no mesh/transform changes."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
D = '/Game/Weapons/M24/ScopeDetail20261028'
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
before = json.loads((O / 'inputs.json').read_text(encoding='utf-8'))
report = {'complete': False, 'saved': [], 'materials': {}, 'runtime_tested': False}
def record():
    (O / 'install_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
def load(path):
    result = u.load_asset(path)
    if not result:
        raise RuntimeError('Missing asset ' + path)
    return result
def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    record()
    return asset
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) or p == before['mesh'] for p in dirty):
    raise RuntimeError('Optic has unsaved edits; preserving them')
mesh = load(before['mesh'])
slots = list(mesh.static_materials)
for slot, old in zip(slots, before['slots']):
    current = slot.material_interface.get_path_name()
    if str(slot.material_slot_name) != old['slot'] or (current != old['material'] and not current.startswith(D)):
        raise RuntimeError('Factory optic material binding changed since input read')

task = u.AssetImportTask()
task.filename = str(O / 'Textures/T_M24_ScopeDetail_Regions.png')
task.destination_path = D + '/Textures'
task.destination_name = 'T_M24_ScopeDetail_Regions'
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
regions = load(task.destination_path + '/' + task.destination_name)
regions.srgb = False
regions.compression_settings = u.TextureCompressionSettings.TC_MASKS
regions.lod_group = u.TextureGroup.TEXTUREGROUP_WEAPON
save(regions)

body_path = D + '/Materials/MI_M24_ScopeSatin'
body = load(body_path) if E.does_asset_exist(body_path) else E.duplicate_asset(before['slots'][0]['material'], body_path)
# Retain the regional WS1 master, source UVs, markings, structural normal and its
# built-in wetness. Only this optic's private instance receives the finer finish.
scalars = {'SourceColorWeight': .16, 'SourceRoughnessWeight': .12,
           'GrainRoughness': .008, 'GrainTileCm': 2.0, 'MottleRoughness': .002,
           'EdgeHighlight': .048, 'EdgeWear': .018, 'EdgeRoughness': .30,
           'CavityDarken': .020, 'CavityRoughness': .022, 'AOStrength': .50,
           'ScratchAmount': 0, 'HandlingPolish': 0, 'WeaponWetness': 0}
for key, value in scalars.items():
    L.set_material_instance_scalar_parameter_value(body, key, value)
L.set_material_instance_vector_parameter_value(body, 'FinishColor', u.LinearColor(.029, .031, .034, 1))
L.set_material_instance_vector_parameter_value(body, 'EdgeColor', u.LinearColor(.072, .078, .083, 1))
L.set_material_instance_texture_parameter_value(body, 'FinishRegions', regions)
L.update_material_instance(body)
save(body)
report['materials'][body.get_path_name()] = {'parent': body.parent.get_path_name(), 'scalars': scalars}

glass_path = D + '/Materials/M_M24_CoatedGlass'
glass = load(glass_path) if E.does_asset_exist(glass_path) else A.create_asset('M_M24_CoatedGlass', D + '/Materials', u.Material, u.MaterialFactoryNew())
L.delete_all_material_expressions(glass)
def node(cls, **values):
    n = L.create_material_expression(glass, cls)
    for key, value in values.items():
        n.set_editor_property(key, value)
    return n
def wire(source, output, target, pin):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Lens graph connection failed: ' + pin)
def output(source, channel, prop):
    if not L.connect_material_property(source, channel, prop):
        raise RuntimeError('Lens output failed: ' + str(prop))
def scalar(name, value):
    return node(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value, group='Coated optic')
coat = node(u.MaterialExpressionVectorParameter, parameter_name='CoatingColor', default_value=u.LinearColor(.08, .18, .20, 1), group='Coated optic')
center = scalar('CenterOpacity', .018)
edge = scalar('GrazingOpacity', .22)
fresnel = node(u.MaterialExpressionFresnel, exponent=4.0, base_reflect_fraction=0.0)
opacity = node(u.MaterialExpressionLinearInterpolate)
wire(center, '', opacity, 'A'); wire(edge, '', opacity, 'B'); wire(fresnel, '', opacity, 'Alpha')
rough = scalar('LensRoughness', .045)
specular = scalar('LensSpecular', .50)
metallic = node(u.MaterialExpressionConstant, r=0)
normal = node(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(0, 0, 1, 1))
# Smooth lens surface; body structural normals must not distort the glass.
for n, channel, prop in [(coat, 'RGB', u.MaterialProperty.MP_BASE_COLOR),
    (opacity, '', u.MaterialProperty.MP_OPACITY), (rough, '', u.MaterialProperty.MP_ROUGHNESS),
    (specular, '', u.MaterialProperty.MP_SPECULAR), (metallic, '', u.MaterialProperty.MP_METALLIC),
    (normal, '', u.MaterialProperty.MP_NORMAL)]:
    output(n, channel, prop)
glass.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
glass.set_editor_property('two_sided', True)
glass.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
glass.set_editor_property('automatically_set_usage_in_editor', False)
# Refraction is deliberately not connected: main-camera optical presentation
# already handles the inside image; this is only the physical lens coating.
errors = L.recompile_material(glass)
if errors:
    raise RuntimeError('Lens material compile failed: ' + str(errors))
save(glass)
replacement = {'M24_Scope': body}
for slot, name, tint, opacity_value in [
    ('M24_ScopeGlass', 'MI_M24_MainLens', (.08, .18, .20), .018),
    ('M24_TopGlass', 'MI_M24_AuxLens', (.12, .17, .19), .012)]:
    path = D + '/Materials/' + name
    material = load(path) if E.does_asset_exist(path) else A.create_asset(name, D + '/Materials', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(material, glass)
    L.set_material_instance_vector_parameter_value(material, 'CoatingColor', u.LinearColor(*tint, 1))
    L.set_material_instance_scalar_parameter_value(material, 'CenterOpacity', opacity_value)
    L.update_material_instance(material)
    replacement[slot] = save(material)
    report['materials'][material.get_path_name()] = {'center_opacity': opacity_value, 'grazing_opacity': .22, 'roughness': .045}
for i, slot in enumerate(slots):
    key = str(slot.material_slot_name)
    if key in replacement:
        slot.material_interface = replacement[key]
        slots[i] = slot
mesh.set_editor_property('static_materials', slots)
E.set_metadata_tag(mesh, 'M24ScopeFinish', 'ScopeDetail20261028: UV0 regional WS1 satin and coated lenses; geometry retained')
save(mesh)
report['slots'] = [{'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name()} for s in mesh.static_materials]
report['geometry_changed'] = False
report['complete'] = True
record()
print('M24_SCOPE_DETAIL_SAVED', flush=True)
