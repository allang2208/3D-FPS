"""Replace only the Wild Rune visual resources, preserving live asset references."""
import json,shutil,os
from pathlib import Path
from datetime import datetime
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
spec=json.loads((P/'production.json').read_text(encoding='utf-8'))
D='/Game/Weapons/HighlandClaymore20260922/WildRune'
E,L,A=u.MaterialEditingLibrary,u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:raise RuntimeError('End active play before changing Wild Rune resources.')
state=P/'install_receipt.json'
if state.exists():
    receipt=json.loads(state.read_text(encoding='utf-8'));before=Path(receipt['backup'])
else:
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S');before=P/'Before'/stamp;before.mkdir(parents=True,exist_ok=True)
    receipt={'time':stamp,'editor_pid':os.getpid(),'assets':[],'complete':False,'tested':False,'native_build_required':False,'backup':str(before)}
before.mkdir(parents=True,exist_ok=True)
def record():(P/'install_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def backup(path):
    file=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if file.exists() and not (before/file.name).exists():shutil.copy2(file,before/file.name)
def save(obj):
    if not L.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    if obj.get_path_name() not in receipt['assets']:receipt['assets'].append(obj.get_path_name())
    record()
def compile_material(mat):
    errors=list(E.recompile_material(mat))
    if errors:raise RuntimeError('Material compilation failed: '+str(errors))
    E.get_statistics(mat);save(mat)

mask_path=D+'/T_Mask_wild_rune';mat_path=D+'/M_SilverRuneSurface_HighlandWild'
backup(mask_path);backup(mat_path)
mat=u.load_asset(mat_path)
if not mat:raise RuntimeError('Installed Wild Rune material is missing.')
task=u.AssetImportTask();task.filename=spec['mask'];task.destination_path=D;task.destination_name='T_Mask_wild_rune'
task.automated=True;task.replace_existing=True;task.save=False
if mask_path+'.T_Mask_wild_rune' not in receipt['assets']:A.import_asset_tasks([task])
mask=u.load_asset(mask_path)
if not mask:raise RuntimeError('Wild Rune texture import failed.')
mask.set_editor_property('srgb',False)
mask.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
mask.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
mask.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);mask.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
save(mask)
nodes=list(E.get_material_expressions(mat))
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
if not (before/'previous_wild_rune.hlsl').exists():(before/'previous_wild_rune.hlsl').write_text(custom.get_editor_property('code'),encoding='utf-8')
parameters={**spec['colors_linear'],**spec['scalars'],'ArtUVRect':spec['art_uv_rect']}
inputs=list(custom.get_editor_property('inputs'));names={str(pin.get_editor_property('input_name')) for pin in inputs}
for name in parameters:
    if name not in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
custom.set_editor_property('inputs',inputs)
custom.set_editor_property('code',(P/'wild_totem_v2.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description','Wild Totem V2: one asymmetric beast jaw, unique claw cuts and bone spear')
for name,value in parameters.items():
    vector=isinstance(value,list);cls=u.MaterialExpressionVectorParameter if vector else u.MaterialExpressionScalarParameter
    param=next((n for n in nodes if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==name),None)
    if param is None:param=E.create_material_expression(mat,cls);param.set_editor_property('parameter_name',name)
    param.set_editor_property('default_value',u.LinearColor(*value) if vector else value)
    param.set_editor_property('group','Wild Totem V2')
    if name=='ArtUVRect':
        # VectorParameter's unnamed output is RGB. Explicitly append A for the
        # crop height before passing the four-channel rectangle to Custom HLSL.
        append=next((n for n in nodes if isinstance(n,u.MaterialExpressionAppendVector) and n.get_editor_property('desc')=='Wild Totem full UV rectangle'),None)
        if append is None:
            append=E.create_material_expression(mat,u.MaterialExpressionAppendVector);append.set_editor_property('desc','Wild Totem full UV rectangle')
        for source,pin,target,input_name in [(param,'RGB',append,'A'),(param,'A',append,'B'),(append,'',custom,name)]:
            if not E.connect_material_expressions(source,pin,target,input_name):raise RuntimeError('Cannot connect full UV rect')
    elif not E.connect_material_expressions(param,'RGB' if vector else '',custom,name):raise RuntimeError('Cannot connect '+name)
for n in nodes:
    if isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='RuneTexture':n.set_editor_property('texture',mask)
compile_material(mat)

# Original UV rune ink becomes a quiet underlayer, so the new composition owns
# the silhouette. Only the already opt-in NativeWild branch is changed.
for name in ['M_HighlandClaymoreSurface','M_HighlandClaymoreSurface_Whirlwind']:
    path='/Game/Weapons/HighlandClaymore20260922/Materials/'+name;native=u.load_asset(path)
    if not native:raise RuntimeError('Missing Highland material '+name)
    backup(path)
    for suffix,description in [('base','Native UV ink tint'),('glow','Native blue ink or golden breathing')]:
        n=next(n for n in E.get_material_expressions(native) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')==description)
        old=n.get_editor_property('code');(before/(name+'_'+suffix+'.hlsl')).write_text(old,encoding='utf-8')
        marker='// HIGHLAND_WILD_NATIVE\n'
        start=old.index(marker);body=old.index('if(Wild>0.5){',start);tail=old.index('}\n',body)+2
        branch=marker+'if(Wild>0.5){float nativeMask=saturate((min(Tex.g,Tex.b)-Tex.r-0.045)*14.0)*saturate((Tex.b-0.12)*8.0); '
        if suffix=='base':branch+='return lerp(Tex,float3(.11,.007,.004)*max(.28,dot(Tex,float3(.2126,.7152,.0722))),nativeMask);}\n'
        else:branch+='float breath=.72+.10*sin(Clock*1.12);return float3(1.0,.019,.005)*nativeMask*breath*.10;}\n'
        n.set_editor_property('code',old[:start]+branch+old[tail:])
    compile_material(native)

path=ROOT/'Content/ColdSteelData/melee-gunsmith.json';old=path.read_bytes();catalog=json.loads(old.decode('utf-8-sig'))
option=next(o for c in catalog['columns'] if c['key']=='blade_2' for o in c['options'] if o['id']=='wild_rune')
receipt['preserved_stats']=dict(option['stats']);receipt['preserved_effects']=option['effects']
option['description']='高地双手剑专属。兽颚主印与破甲爪痕连成错落战纹，赤红裂隙沿剑脊缓缓明灭，强化削韧并穿透物理防护。'
if path.read_bytes()!=old:raise RuntimeError('Concurrent catalog edit preserved.')
(before/path.name).write_bytes(old);tmp=path.with_suffix('.wild-totem-v2.tmp')
tmp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
receipt['complete']=True;receipt['material']=mat_path;receipt['mask']=mask_path;record()
print('HIGHLAND_WILD_TOTEM_V2_INSTALLED '+mat_path)
