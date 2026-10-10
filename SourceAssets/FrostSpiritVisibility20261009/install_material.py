"""Repair and save only the installed Frost Spirit rune material; no play or capture."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import unreal as u
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
E,L=u.MaterialEditingLibrary,u.EditorAssetLibrary
ASSET='/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit'
REV='FrostSpiritVisibility20261009'
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Preserve active play; save this material after PIE ends.')
m=u.load_asset(ASSET)
if not m:raise RuntimeError('Installed Frost Spirit material missing')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if m.get_outermost().get_path_name() in {x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved spirit material edits')
nodes=list(E.get_material_expressions(m))
shader=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
state=json.loads((P/'state_before.json').read_text(encoding='utf-8'))
previous=next(n['code'] for n in state['nodes'] if n['class']=='MaterialExpressionCustom' and 'RuneTexture' in n.get('code',''))
code=(P/'spirit_visible.hlsl').read_text(encoding='utf-8')
if shader.get_editor_property('code') not in (previous,code):
    raise RuntimeError('Intervening spirit material edits preserved')
front=E.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
if front and (shader.get_editor_property('code')!=code or not isinstance(front,u.MaterialExpressionSubstrateShadingModels)):
    raise RuntimeError('Intervening front-material edit preserved')
asset_file=ROOT/'Content/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit.uasset'
before=P/'Before';before.mkdir(exist_ok=True)
if not (before/asset_file.name).exists():
    shutil.copy2(asset_file,before/asset_file.name)
    shutil.copy2(P/'state_before.json',before/'state_before.json')
params=json.loads((P/'parameters.json').read_text(encoding='utf-8'))
inputs=list(shader.get_editor_property('inputs'))
names={str(x.get_editor_property('input_name')) for x in inputs}
for name in params:
    if name not in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
shader.set_editor_property('inputs',inputs)
shader.set_editor_property('code',code)
shader.set_editor_property('description','Frost Spirit: readable ice fractures and soft paired echoes')
for name,value in params.items():
    p=next((n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))==name),None)
    if p is None:
        p=E.create_material_expression(m,u.MaterialExpressionScalarParameter)
        p.set_editor_property('parameter_name',name)
    p.set_editor_property('default_value',value)
    if not E.connect_material_expressions(p,'',shader,name):raise RuntimeError('Cannot connect '+name)
# Keep all existing projection/mask/exposure nodes. Explicitly carry their
# authored emission and coverage into the current Substrate surface output.
emission=E.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
opacity=E.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)
if emission is None or opacity is None:raise RuntimeError('Missing diagnosed rune outputs')
if front is None:
    front=E.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
front.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_UNLIT)
for source,prop,pin in [(emission,u.MaterialProperty.MP_EMISSIVE_COLOR,'Emissive Color'),(opacity,u.MaterialProperty.MP_OPACITY,'Opacity')]:
    output=E.get_material_property_input_node_output_name(m,prop)
    if not E.connect_material_expressions(source,output,front,pin):raise RuntimeError('Cannot connect Substrate '+pin)
if not E.connect_material_property(front,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Cannot connect Substrate surface')
errors=list(E.recompile_material(m))
if errors:raise RuntimeError('Spirit material compilation failed: '+str(errors))
# Finish the material's shader jobs before treating a save as a completed build.
statistics=E.get_statistics(m)
if statistics.get_editor_property('num_pixel_shader_instructions') <= 0:
    raise RuntimeError('No compiled pixel shader; inspect the material build log')
L.set_metadata_tag(m,'RuneAppearanceRevision',REV)
if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):
    raise RuntimeError('Could not save spirit material')
receipt={'complete':True,'time':datetime.now().isoformat(),'asset':m.get_path_name(),'revision':REV,
         'parameters':params,'front_material':front.get_class().get_name(),'compile_errors':errors,
         'shader_compilation_finished':True,'command_line':u.SystemLibrary.get_command_line(),'saved_file_sha256':hashlib.sha256(asset_file.read_bytes()).hexdigest(),
         'runtime_tested':False,'screenshots_or_render_acceptance':False}
(P/'install_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FROST_SPIRIT_VISIBILITY_SAVED '+m.get_path_name())
