"""Create the dedicated spirit material and its matching icon, via MCP mutex."""
from pathlib import Path
from datetime import datetime
import json,shutil,runpy
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
E=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving spirit assets')
source='/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2'
target='/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit'
mat=u.load_asset(target) or u.EditorAssetLibrary.duplicate_asset(source,target)
if not mat:raise RuntimeError('Could not create dedicated spirit material')
nodes=list(E.get_material_expressions(mat))
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
production=json.loads((P/'production.json').read_text(encoding='utf-8'))
inputs=list(custom.get_editor_property('inputs'))
names={str(pin.get_editor_property('input_name')) for pin in inputs}
parameters={**production['colors_linear'],**production['scalars']}
for name in parameters:
    if name not in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
custom.set_editor_property('inputs',inputs)
custom.set_editor_property('code',(P/'spirit_burst.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description','Frost-exclusive spirit burst: amethyst charge and paired expanding diamond waves')
for name,value in parameters.items():
    is_color=isinstance(value,list)
    cls=u.MaterialExpressionVectorParameter if is_color else u.MaterialExpressionScalarParameter
    param=next((n for n in nodes if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==name),None)
    if param is None:
        param=E.create_material_expression(mat,cls)
        param.set_editor_property('parameter_name',name)
    param.set_editor_property('default_value',u.LinearColor(*value) if is_color else value)
    param.set_editor_property('group','Frost spirit burst')
    if not E.connect_material_expressions(param,'RGB' if is_color else '',custom,name):
        raise RuntimeError('Could not connect '+name)
for n in nodes:
    if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='RuneMode':
        n.set_editor_property('default_value',4.)
    if isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='RuneTexture':
        n.set_editor_property('texture',u.load_asset(production['mask']))
errors=list(E.recompile_material(mat))
if errors:raise RuntimeError('Spirit material build failed: '+str(errors))
u.EditorAssetLibrary.set_metadata_tag(mat,'RuneAppearanceRevision','FrostSpiritBurst20260922')
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Cannot save spirit material')
receipt={'time':datetime.now().isoformat(),'material':mat.get_path_name(),'shader_compile_errors':errors}
(P/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

key='ue_frost_crystal_sword_blade_2_spirit_burst_rune'
png=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
shutil.copy2(P/(key+'.png'),png)
result=u.ModelingService.import_texture(str(png),'/Game/ColdSteelData/AttachmentIcons20260913/'+key,True,'Default',True)
if not result.success:raise RuntimeError(result.message)
tex=u.load_asset('/Game/ColdSteelData/AttachmentIcons20260913/'+key)
tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
tex.set_editor_property('srgb',True)
if not u.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Cannot save spirit icon')
receipt.update({'icon':tex.get_path_name(),'png':str(png),'runtime_tests':'not run; user will test'})
(P/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FROST_SPIRIT_MATERIAL_AND_ICON_SAVED')
runpy.run_path(str(P/'read_loaded_build.py'),run_name='__main__')
