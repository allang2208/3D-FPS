import unreal as u
import json
from pathlib import Path
OUT = Path(__file__).resolve().parent
BASE = '/Game/Monsters/HundredEyedSlag/V1'
LIB = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary
if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('Preserving active PIE; run the background installation after the editor closes')
DEST = '/Game/Monsters/HundredEyedSlag/PolishV2'
material = u.load_asset(DEST + '/Materials/M_HundredEyedSlag_Skin_V2')
if material is None:
    material = u.AssetToolsHelpers.get_asset_tools().create_asset('M_HundredEyedSlag_Skin_V2', DEST + '/Materials', u.Material, u.MaterialFactoryNew())
mesh = u.load_asset(DEST + '/SK_HundredEyedSlag_V2')
report = {'substrate_live': u.SystemLibrary.get_console_variable_int_value('r.Substrate'),
    'before_textures': [t.get_path_name() for t in MEL.get_material_used_textures(material)]}
expressions=list(MEL.get_material_expressions(material))
material.set_editor_property('used_with_skeletal_mesh', True)
material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
surface = next((n for n in expressions if isinstance(n,u.MaterialExpressionSubstrateShadingModels)),None)
if surface is None:surface = MEL.create_material_expression(material, u.MaterialExpressionSubstrateShadingModels)
surface.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
for index, (semantic, pin, output, prop) in enumerate((
    ('BaseColor', 'BaseColor', 'RGB', u.MaterialProperty.MP_BASE_COLOR),
    ('Metallic', 'Metallic', 'R', u.MaterialProperty.MP_METALLIC),
    ('Roughness', 'Roughness', 'R', u.MaterialProperty.MP_ROUGHNESS),
    ('Normal', 'Normal', 'RGB', u.MaterialProperty.MP_NORMAL))):
    texture = u.load_asset(BASE + '/Textures/T_HundredEyedSlag_' + semantic)
    if texture is None: raise RuntimeError('Missing skin texture ' + semantic)
    node = next((n for n in expressions if isinstance(n,u.MaterialExpressionTextureSample)
        and n.get_editor_property('texture')==texture),None)
    if node is None:node = MEL.create_material_expression(material, u.MaterialExpressionTextureSample, -500, index * 180)
    node.set_editor_property('texture', texture)
    node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic == 'Normal'
        else u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic == 'BaseColor'
        else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if not MEL.connect_material_property(node, output, prop): raise RuntimeError('Missing legacy pin ' + semantic)
    if not MEL.connect_material_expressions(node, output, surface, pin): raise RuntimeError('Missing surface pin ' + semantic)
if not MEL.connect_material_property(surface, '', u.MaterialProperty.MP_FRONT_MATERIAL): raise RuntimeError('Missing surface output')
MEL.recompile_material(material)
if not u.PoisonMaggotMonster.compile_material_assets([material]): raise RuntimeError('Native skin compilation failed')
slots = list(mesh.get_editor_property('materials'))
for index, slot in enumerate(slots):
    slot.material_interface = material
    slots[index] = slot
mesh.set_editor_property('materials', slots)
for asset in (material, mesh):
    if not LIB.save_loaded_asset(asset, False): raise RuntimeError('Save failed ' + asset.get_path_name())
report['after_textures'] = [t.get_path_name() for t in MEL.get_material_used_textures(material)]
if len(report['after_textures']) != 4: raise RuntimeError('Skin is still missing the four PBR texture dependencies')
report['saved'] = [material.get_path_name(), mesh.get_path_name()]
(OUT / 'material_fix.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('SLAG_SKIN_FIXED ' + json.dumps(report))
