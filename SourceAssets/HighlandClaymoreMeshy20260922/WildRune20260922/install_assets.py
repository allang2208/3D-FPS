"""Create the Highland-exclusive red rune, tint native ink, and install its option."""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT/'Content/ColdSteelData'
DEST = '/Game/Weapons/HighlandClaymore20260922/WildRune'
E, L, A = u.MaterialEditingLibrary, u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:
    raise RuntimeError('End PIE before saving wild-rune assets.')
production = json.loads((P/'production.json').read_text(encoding='utf-8'))
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
before = P/'Before'/stamp
before.mkdir(parents=True,exist_ok=True)
receipt = {'time':stamp,'editor_pid':os.getpid(),'assets':[],'complete':False,'tested':False}


def record():
    (P/'install_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')


def save(asset):
    if not L.save_loaded_asset(asset,False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    record()


def texture(file,name,folder,icon=False):
    task = u.AssetImportTask()
    task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task])
    tex=u.load_asset(folder+'/'+name)
    if not tex or not task.imported_object_paths:
        raise RuntimeError('Texture import failed: '+str(file))
    tex.set_editor_property('srgb',icon)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_GRAYSCALE)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI if icon else u.TextureGroup.TEXTUREGROUP_EFFECTS)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS if icon else u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
    tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
    tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    save(tex)
    return tex


mask=texture(P/production['mask'],'T_Mask_wild_rune',DEST)
source='/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2'
target=DEST+'/M_SilverRuneSurface_HighlandWild'
mat=u.load_asset(target) or L.duplicate_asset(source,target)
if not mat:raise RuntimeError('Cannot create wild-rune material.')
nodes=list(E.get_material_expressions(mat))
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
parameters={**production['colors_linear'],**production['scalars']}
inputs=list(custom.get_editor_property('inputs'))
names={str(pin.get_editor_property('input_name')) for pin in inputs}
for name in parameters:
    if name not in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
custom.set_editor_property('inputs',inputs)
custom.set_editor_property('code',(P/'wild_rune.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description','Highland wild rune: crimson hooked fangs, feathered edges and soft heartbeat')
for name,value in parameters.items():
    color=isinstance(value,list)
    cls=u.MaterialExpressionVectorParameter if color else u.MaterialExpressionScalarParameter
    param=next((n for n in nodes if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==name),None)
    if param is None:
        param=E.create_material_expression(mat,cls);param.set_editor_property('parameter_name',name)
    param.set_editor_property('default_value',u.LinearColor(*value) if color else value)
    param.set_editor_property('group','Highland wild rune')
    if not E.connect_material_expressions(param,'RGB' if color else '',custom,name):
        raise RuntimeError('Cannot connect wild parameter '+name)
for node in nodes:
    if isinstance(node,u.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name'))=='RuneMode':
        node.set_editor_property('default_value',5.)
    if isinstance(node,u.MaterialExpressionTextureObjectParameter) and str(node.get_editor_property('parameter_name'))=='RuneTexture':
        node.set_editor_property('texture',mask)
errors=list(E.recompile_material(mat))
if errors:raise RuntimeError('Wild rune shader build failed: '+str(errors))
E.get_statistics(mat)
save(mat)

# Add an opt-in native-ink tint to the two existing Highland surface graphs.
# Default zero exactly retains every other configuration; the blade MID alone
# enables this parameter while the exclusive wild rune is installed.
native_folder='/Game/Weapons/HighlandClaymore20260922/Materials/'
for name in ['M_HighlandClaymoreSurface','M_HighlandClaymoreSurface_Whirlwind']:
    native=u.load_asset(native_folder+name)
    if not native:raise RuntimeError('Highland surface missing: '+name)
    native_file=ROOT/'Content'/(native_folder.removeprefix('/Game/')+name+'.uasset')
    shutil.copy2(native_file,before/native_file.name)
    native_nodes=list(E.get_material_expressions(native))
    wild=next((n for n in native_nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='NativeWild'),None)
    if wild is None:
        wild=E.create_material_expression(native,u.MaterialExpressionScalarParameter)
        wild.set_editor_property('parameter_name','NativeWild');wild.set_editor_property('default_value',0.)
    for suffix,description in [('base','Native UV ink tint'),('glow','Native blue ink or golden breathing')]:
        node=next(n for n in native_nodes if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')==description)
        old=node.get_editor_property('code')
        (before/(name+'_'+suffix+'.hlsl')).write_text(old,encoding='utf-8')
        pins=list(node.get_editor_property('inputs'))
        if 'Wild' not in {str(pin.get_editor_property('input_name')) for pin in pins}:
            pin=u.CustomInput();pin.set_editor_property('input_name','Wild');pins.append(pin)
            node.set_editor_property('inputs',pins)
        if 'HIGHLAND_WILD_NATIVE' not in old:
            prefix='// HIGHLAND_WILD_NATIVE\nif(Wild>0.5){float nativeMask=saturate((min(Tex.g,Tex.b)-Tex.r-0.045)*14.0)*saturate((Tex.b-0.12)*8.0); '
            prefix+=('return lerp(Tex,float3(.42,.013,.008)*max(.28,dot(Tex,float3(.2126,.7152,.0722))),nativeMask);}\n' if suffix=='base'
                     else 'float breath=.70+.18*sin(Clock*1.85);return float3(1.0,.025,.007)*nativeMask*breath*.72;}\n')
            node.set_editor_property('code',prefix+old)
        if not E.connect_material_expressions(wild,'',node,'Wild'):
            raise RuntimeError('Cannot connect native wild tint: '+name)
    errors=list(E.recompile_material(native))
    if errors:raise RuntimeError('Native tint build failed: '+str(errors))
    E.get_statistics(native)
    save(native)

png=DATA/'AttachmentIcons20260913'/production['icon']
if png.exists():shutil.copy2(png,before/png.name)
shutil.copy2(P/'Icons'/production['icon'],png)
texture(png,png.stem,'/Game/ColdSteelData/AttachmentIcons20260913',True)

catalog_path=DATA/'melee-gunsmith.json'
old=catalog_path.read_bytes()
catalog=json.loads(old.decode('utf-8-sig'))
column=next(c for c in catalog['columns'] if c['key']=='blade_2')
option={'id':'wild_rune','name':'蛮荒符文','weapons':['ue_highland_claymore'],
        'description':'高地双手剑专属。赤红獠牙刻纹沿剑脊缓缓明灭，蛮荒之力强化削韧并穿透敌人的物理防护。',
        'effects':[{'text':'攻击韧性伤害 +30%','benefit':1},{'text':'物理防御穿透 +20%','benefit':1}],
        'stats':production['stats']}
index=next((i for i,o in enumerate(column['options']) if o['id']=='wild_rune'),None)
if index is None:column['options'].append(option)
else:column['options'][index]=option
if catalog_path.read_bytes()!=old:raise RuntimeError('Melee catalog changed during import; current file preserved.')
(before/catalog_path.name).write_bytes(old)
temp=catalog_path.with_suffix('.wild-rune.tmp')
temp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
temp.replace(catalog_path)
receipt.update(complete=True,catalog=str(catalog_path),option=option,backup=str(before))
record()
print('HIGHLAND_WILD_RUNE_ASSETS_AND_CATALOG_INSTALLED')
