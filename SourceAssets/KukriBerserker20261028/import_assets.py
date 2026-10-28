"""Save the wolf-blood HUD, six blade surfaces and the standard framed icon."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
PROJECT=P.parents[1]
DEST='/Game/Weapons/Kukri20261020/Berserker20261028'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active game')
receipt={'complete':False,'saved_assets':[],'surface_materials':{},'runtime_tested':False}
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(path.startswith(DEST) for path in dirty):raise RuntimeError('Preserve unsaved berserker packages')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    (P/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return asset
def texture(path,name,icon=False):
    dest='/Game/ColdSteelData/AttachmentIcons20260913' if icon else DEST+'/Textures'
    if dest+'/'+name in dirty:raise RuntimeError('Preserve dirty icon')
    task=u.AssetImportTask();task.filename=str(path);task.destination_path=dest;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=u.load_asset(dest+'/'+name)
    if not tex:raise RuntimeError('Import failed '+name)
    tex.set_editor_properties({'srgb':icon,'never_stream':icon,
        'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_MASKS,
        'lod_group':u.TextureGroup.TEXTUREGROUP_UI if icon else u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,
        'max_texture_size':1024 if icon else 2048})
    if icon:tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    return save(tex)
def duplicate(source,path):
    if E.does_asset_exist(path):return u.load_asset(path)
    obj=E.duplicate_asset(source,path)
    if not obj:raise RuntimeError('Cannot duplicate '+source)
    return obj
def node(mat,cls,**props):
    value=L.create_material_expression(mat,cls)
    for key,item in props.items():value.set_editor_property(key,item)
    return value
def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
wolf=texture(P/'Art/WolfSigil.png','T_BerserkerWolf')
icon=texture(P/'Icons/ue_kukri_blade_2_berserker_rune.png','ue_kukri_blade_2_berserker_rune',True)
receipt['icon']=icon.get_path_name()
hud=duplicate('/Game/Weapons/RuneboundWarhammer20261022/HudSymmetricCapsV3/M_RuneboundEnergyHud',DEST+'/M_BerserkerEnergyHud')
custom=next(n for n in L.get_material_expressions(hud) if isinstance(n,u.MaterialExpressionCustom))
inputs=list(custom.get_editor_property('inputs'))
if not any(str(x.get_editor_property('input_name'))=='WolfTex' for x in inputs):
    pin=u.CustomInput();pin.set_editor_property('input_name','WolfTex');inputs.append(pin);custom.set_editor_property('inputs',inputs)
    obj=node(hud,u.MaterialExpressionTextureObjectParameter,parameter_name='WolfTex',texture=wolf)
    link(obj,'',custom,'WolfTex')
custom.set_editor_property('code',(P/'BerserkerEnergyHud.hlsl').read_text('utf-8'))
E.set_metadata_tag(hud,'SourceAuthoring','KukriBerserker20261028')
L.recompile_material(hud)
materials=[hud]
modules=json.loads((PROJECT/'Content/ColdSteelData/kukri-modules.json').read_text('utf-8-sig'))
donors=modules['slots']['blade_2']['knife_mark_wing']['surface_materials']
for source in json.loads((P/'blade-layout-source.json').read_text('utf-8')):
    kind=source['kind'];slot='M_Kukri' if kind=='Factory' else 'M_Kukri_'+kind
    mask=texture(P/'Textures'/('T_KukriMask_'+kind+'_Berserker.png'),'T_KukriMask_'+kind+'_Berserker')
    donor=u.load_asset(donors[slot]);parent=donor.get_editor_property('parent')
    while isinstance(parent,u.MaterialInstanceConstant):parent=parent.get_editor_property('parent')
    mat=duplicate(parent.get_path_name(),DEST+'/Materials/M_Berserker_'+kind)
    if E.get_metadata_tag(mat,'BerserkerEmission')!='1':
        expressions=L.get_material_expressions(mat)
        ink=next(n for n in expressions if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='RuneMask')
        inputs=[]
        for key in ('Mask','Time'):
            pin=u.CustomInput();pin.set_editor_property('input_name',key);inputs.append(pin)
        glow=node(mat,u.MaterialExpressionCustom,code='return Mask*float3(.85,.012,.022)*(.85+.15*sin(Time*1.7));',inputs=inputs,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
        link(ink,'R',glow,'Mask');link(node(mat,u.MaterialExpressionTime),'',glow,'Time')
        L.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        slab=next(n for n in expressions if isinstance(n,u.MaterialExpressionSubstrateShadingModels))
        link(glow,'',slab,'Emissive Color')
        E.set_metadata_tag(mat,'BerserkerEmission','1')
    L.recompile_material(mat);materials.append(mat)
    instance=duplicate(donor.get_path_name(),DEST+'/Materials/MI_Berserker_'+kind)
    L.set_material_instance_parent(instance,mat)
    L.set_material_instance_texture_parameter_value(instance,'RuneMask',mask)
    L.set_material_instance_vector_parameter_value(instance,'RuneTint',u.LinearColor(.30,.012,.018,1))
    L.update_material_instance(instance)
    materials.append(instance);receipt['surface_materials'][slot]=instance.get_path_name()
if not u.PoisonMaggotMonster.compile_material_assets(materials):raise RuntimeError('Material compilation failed')
for mat in materials:save(mat)
receipt['hud']=hud.get_path_name();receipt['complete']=True
(P/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('BERSERKER_ASSETS_SAVED '+str(len(receipt['saved_assets'])))
# Keep local blade projection and the retained lower HUD with its wolf-head crown.
# Both rejected HUD revisions are excluded from the active import path.
refine=P/'VolumeRefine/install_refine.py'
if refine.exists() and (P/'WolfHeadComposite/Art/WolfHead_Crown.png').exists():
    exec(compile(refine.read_text('utf-8'),str(refine),'exec'),{'__file__':str(refine),'__name__':'__main__'})
