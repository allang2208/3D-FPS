"""Headless production import: engraving, framed icon, blade light and original audio."""
from pathlib import Path
import json, os
import unreal as u
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
DEST='/Game/Weapons/HighlandClaymore20260922/OathRune20261106'
E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'complete':False,'tested':False,'pid':os.getpid(),'assets':[]}
def record():
    (P/'saved-assets.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Unable to save '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()
def compile_material(asset):
    errors=E.recompile_material(asset)
    if errors:raise RuntimeError('Material compile failed: '+asset.get_path_name()+' '+str(errors))
def import_file(path,name,folder):
    task=u.AssetImportTask();task.filename=str(path);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    return asset
mask=import_file(P/'Textures/T_Mask_highland_oath_rune.png','T_Mask_highland_oath_rune',DEST)
mask.set_editor_property('srgb',False);mask.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
mask.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_EFFECTS)
mask.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);mask.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
save(mask)
icon_name='ue_highland_claymore_blade_2_highland_oath_rune'
icon=import_file(P/'Icons'/(icon_name+'.png'),icon_name,'/Game/ColdSteelData/AttachmentIcons20260913')
icon.set_editor_property('srgb',True);icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property('never_stream',True)
save(icon)
target=DEST+'/M_SilverRuneSurface_HighlandOath'
mat=u.load_asset(target) or L.duplicate_asset('/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2',target)
nodes=list(E.get_material_expressions(mat))
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
custom.set_editor_property('code',(P/'oath_surface.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description','Highland oath: gold engraving, true-aspect crest and three sequential seals')
pins=list(custom.get_editor_property('inputs'));names={str(p.get_editor_property('input_name')) for p in pins}
for name in ['OathCharge','OathReady','OathRelease']:
    if name not in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
custom.set_editor_property('inputs',pins)
for name in ['OathCharge','OathReady','OathRelease']:
    param=next((n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))==name),None)
    if param is None:param=E.create_material_expression(mat,u.MaterialExpressionScalarParameter);param.set_editor_property('parameter_name',name)
    param.set_editor_property('default_value',0.)
    if not E.connect_material_expressions(param,'',custom,name):raise RuntimeError('Missing oath input '+name)
for n in nodes:
    if isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='RuneTexture':n.set_editor_property('texture',mask)
    if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='RuneMode':n.set_editor_property('default_value',11.)
compile_material(mat);save(mat)

# Native blue ink is neutral silver only while this rune is selected. The
# opt-in parameter preserves the original finish for every other assembly.
for name in ['M_HighlandClaymoreSurface','M_HighlandClaymoreSurface_Whirlwind']:
    native=u.load_asset('/Game/Weapons/HighlandClaymore20260922/Materials/'+name)
    if not native:continue
    ns=list(E.get_material_expressions(native))
    param=next((n for n in ns if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='NativeOath'),None)
    if param is None:
        param=E.create_material_expression(native,u.MaterialExpressionScalarParameter)
        param.set_editor_property('parameter_name','NativeOath');param.set_editor_property('default_value',0.)
    for n in ns:
        if not isinstance(n,u.MaterialExpressionCustom):continue
        description=n.get_editor_property('description')
        if description not in ['Native UV ink tint','Native blue ink or golden breathing']:continue
        code=n.get_editor_property('code')
        if 'HIGHLAND_OATH_NATIVE' in code:continue
        before=P/'BeforeNative';before.mkdir(exist_ok=True)
        (before/(name+('_base.hlsl' if description=='Native UV ink tint' else '_glow.hlsl'))).write_text(code,encoding='utf-8')
        pins=list(n.get_editor_property('inputs'));pin=u.CustomInput();pin.set_editor_property('input_name','Oath');pins.append(pin)
        n.set_editor_property('inputs',pins)
        prefix='// HIGHLAND_OATH_NATIVE\nif(Oath>.5){float ink=saturate((min(Tex.g,Tex.b)-Tex.r-.045)*14.)*saturate((Tex.b-.12)*8.);'
        prefix+=('return lerp(Tex,float3(.52,.56,.60)*max(.22,dot(Tex,float3(.2126,.7152,.0722))),ink);}\n' if description=='Native UV ink tint' else 'return float3(.15,.18,.22)*ink;}\n')
        n.set_editor_property('code',prefix+code);E.connect_material_expressions(param,'',n,'Oath')
    compile_material(native);save(native)

# A thin, translucent emissive ribbon. Existing depth testing remains enabled.
light=u.load_asset(DEST+'/M_OathLight') or A.create_asset('M_OathLight',DEST,u.Material,u.MaterialFactoryNew())
E.delete_all_material_expressions(light)
light.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
light.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
light.set_editor_property('two_sided',True)
color=E.create_material_expression(light,u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(2.4,1.65,.62,1))
uv=E.create_material_expression(light,u.MaterialExpressionTextureCoordinate)
custom=E.create_material_expression(light,u.MaterialExpressionCustom)
pin=u.CustomInput();pin.set_editor_property('input_name','UV');custom.set_editor_property('inputs',[pin])
custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
custom.set_editor_property('code','return pow(saturate(1-abs(UV.y*2-1)),1.7)*.68;')
E.connect_material_expressions(uv,'',custom,'UV')
E.connect_material_property(custom,'',u.MaterialProperty.MP_OPACITY)
E.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
compile_material(light);save(light)
attenuation=u.load_asset(DEST+'/A_OathImpact') or A.create_asset('A_OathImpact',DEST,u.SoundAttenuation,u.SoundAttenuationFactory())
settings=attenuation.get_editor_property('attenuation')
settings.set_editor_property('attenuate',True);settings.set_editor_property('spatialize',True)
settings.set_editor_property('attenuation_shape',u.AttenuationShape.SPHERE)
settings.set_editor_property('attenuation_shape_extents',u.Vector(140,0,0))
settings.set_editor_property('falloff_distance',1100.)
attenuation.set_editor_property('attenuation',settings);save(attenuation)
for name in ['S_OathReady','S_OathImpact']:
    sound=import_file(P/'Audio'/(name+'.wav'),name,DEST)
    if name=='S_OathImpact':sound.set_editor_property('attenuation_settings',attenuation)
    sound.set_editor_property('volume',.8);save(sound)
import runpy
runpy.run_path(str(P/'apply_gold.py'),run_name='__main__')
receipt['complete']=True;record()
print('OATH_ASSETS_SAVED')
