"""Headless or current-editor batch: save mask, framed icon, sutra HUD and native blade branches."""
from pathlib import Path
import json,runpy,shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
EXT=runpy.run_path(str(P/'catalog_extension.py'));D=EXT['UE']
E,L=u.MaterialEditingLibrary,u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Exit PIE before importing Jingang assets')
receipt={'complete':False,'runtime_tested':False,'saved_assets':[],'bindings':{}}
def save(asset):
    L.set_metadata_tag(asset,'JingangRevision','JingangRune20261006')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def texture(file,path,icon=False):
    folder,name=path.rsplit('/',1)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory()
    A.import_asset_tasks([task]);t=u.load_asset(path)
    if not t:raise RuntimeError('Import failed '+path)
    t.set_editor_property('srgb',icon)
    t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_GRAYSCALE)
    t.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);t.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    if icon or 'Hud' in path:
        t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);t.set_editor_property('never_stream',True)
        t.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    save(t);return t
mask=texture(P/'Artwork/Jingang_Blade_Mask.png',D+'/Textures/T_Mask_jingang_rune')
atlas=texture(P/'Artwork/Jingang_Hud_Atlas.png',D+'/Textures/T_JingangHudAtlas')
icon_key='blade_2_jingang_rune'
icon_file=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon_key+'.png')
shutil.copy2(P/'Artwork/Jingang_Icon.png',icon_file)
texture(icon_file,'/Game/ColdSteelData/AttachmentIcons20260913/'+icon_key,True)

def duplicate(source,path):
    result=u.load_asset(path) or L.duplicate_asset(source.get_path_name(),path)
    if not result:raise RuntimeError('Cannot duplicate '+path)
    return result
modules=json.loads((ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
sources=sorted({v for row in modules['slots']['blade_1'].values() for v in row.get('materials',{}).values()})
prefix=(P/'jingang_emission.hlsl').read_text(encoding='utf-8')+'\n'
replace_jingang_branch=runpy.run_path(str(P/'rune_code.py'))['replace_jingang_branch']
temporal={}
for source_path in sources:
    source=u.load_asset(source_path)
    if not source:raise RuntimeError('Missing blade '+source_path)
    path=source_path.split('.')[0] if source_path.startswith(D+'/Materials/') else D+'/Materials/'+source.get_name()+'_Jingang'
    for is_temporal in [False,True]:
        target=path+('_Whirlwind' if is_temporal else '')
        mat=duplicate(u.load_asset(path) if is_temporal else source,target)
        found=False
        for n in E.get_material_expressions(mat):
            if isinstance(n,u.MaterialExpressionCustom):
                code=n.get_editor_property('code')
                if 'RuneMode' in code and 'RuneTexture' in code:
                    n.set_editor_property('code',replace_jingang_branch(code,prefix))
                    found=True
        if not found:raise RuntimeError('Rune custom expression absent '+target)
        if is_temporal and not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in E.get_material_expressions(mat)):
            out=E.create_material_expression(mat,u.MaterialExpressionTemporalResponsivenessOutput)
            one=E.create_material_expression(mat,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
            E.connect_material_expressions(one,'',out,'')
        errors=E.recompile_material(mat)
        if errors:raise RuntimeError('Material compilation '+str(errors))
        save(mat)
        if is_temporal:temporal[u.load_asset(path).get_path_name()]=mat.get_path_name()
        else:receipt['bindings'][source_path]=mat.get_path_name()

name='M_JingangSutraHud';path=D+'/Materials/'+name
mat=u.load_asset(path) or A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
for n in list(E.get_material_expressions(mat)):E.delete_material_expression(mat,n)
mat.set_editor_property('material_domain',u.MaterialDomain.MD_UI)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
def node(cls,**props):
    n=E.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
inputs={'UV':node(u.MaterialExpressionTextureCoordinate),
 'Sutra':node(u.MaterialExpressionTextureObject,texture=atlas,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)}
for key,value in [('State',0.),('PreviousState',0.),('Blend',1.),('Age',0.),('Leech',0.)]:
    inputs[key]=node(u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value)
c=node(u.MaterialExpressionCustom,code=(P/'sutra_hud.hlsl').read_text(),output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pins=[]
for key in inputs:
    pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
c.set_editor_property('inputs',pins)
for key,n in inputs.items():E.connect_material_expressions(n,'',c,key)
for alpha,prop in [(False,u.MaterialProperty.MP_EMISSIVE_COLOR),(True,u.MaterialProperty.MP_OPACITY)]:
    out=node(u.MaterialExpressionComponentMask,r=not alpha,g=not alpha,b=not alpha,a=alpha)
    E.connect_material_expressions(c,'',out,str(E.get_material_expression_input_names(out)[0]))
    E.connect_material_property(out,'',prop)
errors=E.recompile_material(mat)
if errors:raise RuntimeError('HUD material compilation '+str(errors))
save(mat)
def modules_update(root):
    for row in root['slots']['blade_1'].values():
        for key,value in row.get('materials',{}).items():
            if value in receipt['bindings']:row['materials'][key]=receipt['bindings'][value]
    root['jingang_rune_revision']='JingangRune20261006'
EXT['update'](ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json',modules_update)
EXT['update'](ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json',lambda root:root.get('materials',root).update(temporal))
EXT['install']()
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('JINGANG_ASSETS_SAVED '+str(len(receipt['saved_assets'])),flush=True)
