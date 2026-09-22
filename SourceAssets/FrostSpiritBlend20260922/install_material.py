"""Update only spirit-burst shading; preserve its graph, projection and gameplay."""
from pathlib import Path
from datetime import datetime
import json,shutil
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
E=u.MaterialEditingLibrary
ASSET='/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving the spirit material')
mat=u.load_asset(ASSET)
if not mat:raise RuntimeError('Installed spirit material missing')
nodes=list(E.get_material_expressions(mat))
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
backup=P/'Before';backup.mkdir(exist_ok=True)
asset_file=ROOT/'Content'/(ASSET.removeprefix('/Game/')+'.uasset')
if not (backup/asset_file.name).exists():
    shutil.copy2(asset_file,backup/asset_file.name)
    (backup/'spirit_previous.hlsl').write_text(custom.get_editor_property('code'),encoding='utf-8')
    old={}
    for n in nodes:
        if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):
            value=n.get_editor_property('default_value')
            old[str(n.get_editor_property('parameter_name'))]=[value.r,value.g,value.b,value.a] if isinstance(value,u.LinearColor) else value
    (backup/'parameters.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
palette=json.loads((P/'palette.json').read_text(encoding='utf-8'))
parameters={**palette['colors_linear'],**palette['scalars']}
inputs=list(custom.get_editor_property('inputs'))
names={str(pin.get_editor_property('input_name')) for pin in inputs}
for name in parameters:
    if name not in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
custom.set_editor_property('inputs',inputs)
custom.set_editor_property('code',(P/'spirit_blend.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description','Spirit burst: soft ice-blue subsurface-like light, rounded fading echoes')
for name,value in parameters.items():
    color=isinstance(value,list)
    cls=u.MaterialExpressionVectorParameter if color else u.MaterialExpressionScalarParameter
    n=next((n for n in nodes if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==name),None)
    if n is None:
        n=E.create_material_expression(mat,cls);n.set_editor_property('parameter_name',name)
    n.set_editor_property('default_value',u.LinearColor(*value) if color else value)
    n.set_editor_property('group','Frost spirit blend')
    if not E.connect_material_expressions(n,'RGB' if color else '',custom,name):
        raise RuntimeError('Cannot connect '+name)
errors=list(E.recompile_material(mat))
if errors:raise RuntimeError('Material build failed: '+str(errors))
u.EditorAssetLibrary.set_metadata_tag(mat,'RuneAppearanceRevision','FrostSpiritBlend20260922')
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Could not save spirit material')
(P/'install_receipt.json').write_text(json.dumps({
    'time':datetime.now().isoformat(),'material':mat.get_path_name(),'palette':palette,
    'shader_compile_errors':errors,'runtime_tests':'not run; user will test'
},indent=2),encoding='utf-8')
print('FROST_SPIRIT_BLEND_SAVED')
