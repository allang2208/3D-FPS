"""Background import into an independent security namespace; no game/preview tests."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
DEST='/Game/Monsters/FacelessResearcher'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is active; researcher import not started')

report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8')) if (ROOT/'ue_delivery.json').exists() else {'stage':'importing','saved':[],'runtime_tested':False}
def record():
    (ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
def copy_asset(source,name):
    path=DEST+'/'+name
    asset=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source,path)
    if not asset:raise RuntimeError('Copy source unavailable: '+source)
    return asset
def import_one(file,folder,name,options=None):
    path=folder+'/'+name
    if LIB.does_asset_exist(path):return u.load_asset(path)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed '+path)
    return asset
def connect(source,output,dest,pin):
    names=MEL.get_material_expression_input_names(dest)
    normalize=lambda s:''.join(c.lower() for c in str(s) if c.isalnum())
    match=next((p for p in names if normalize(p)==normalize(pin)),None)
    if match is None:match=next((p for p in names if normalize(p).startswith(normalize(pin))),None)
    if match is None or not MEL.connect_material_expressions(source,output,dest,match):raise RuntimeError('Material pin '+pin+' in '+str(names))
skeleton=copy_asset('/Game/ZombieFemale/Asset/Meshes/SK_ZombieFemale','SKEL_FacelessResearcher')
physics=copy_asset('/Game/ZombieFemale/Asset/Meshes/PA_ZombieFemale','PA_FacelessResearcher')
save(skeleton);save(physics)
textures={}
for file in sorted((ROOT/'Textures').glob('*.png')):
    name='T_FRS1_'+file.stem;tex=import_one(file,DEST+'/Textures',name)
    is_normal='_Normal' in file.stem or file.stem=='Source_normal'
    is_data=is_normal or '_ORM' in file.stem or 'metallic_roughness' in file.stem
    tex.set_editor_property('srgb',not is_data);tex.set_editor_property('never_stream',False)
    if is_normal:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif is_data:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);textures[file.stem]=tex
materials={}
for family in ['Skin','Coat','Trousers','Trim','Hardware','Leather']:
    name='M_FRS1_'+family;path=DEST+'/Materials/'+name
    if LIB.does_asset_exist(path):mat=u.load_asset(path)
    else:
        mat=AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        cloth=family in ['Coat','Trousers','Trim','Insignia']
        slab=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF if cloth else u.MaterialExpressionSubstrateShadingModels,450,0)
        keys=['Source_texture_0','Source_normal','Source_texture_0_metallic_roughness'] if family=='Skin' else ['Researcher_'+family+'_'+s for s in ['BaseColor','Normal','ORM']]
        for i,(key,pin,channel,sampler) in enumerate([
            (keys[0],'DiffuseAlbedo' if cloth else 'BaseColor','RGB',u.MaterialSamplerType.SAMPLERTYPE_COLOR),
            (keys[1],'Normal','RGB',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
            (keys[2],'Roughness','G',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
            node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSample,0,i*180)
            node.texture=textures[key];node.sampler_type=sampler;connect(node,channel,slab,pin)
            if i==0 and cloth:connect(node,'RGB',slab,'FuzzColor')
            if i==2 and not cloth:connect(node,'B',slab,'Metallic')
        if cloth:
            for pin,value in [('F0',.022),('FuzzAmount',.14 if family=='Coat' else .10),('FuzzRoughness',.84)]:
                node=MEL.create_material_expression(mat,u.MaterialExpressionConstant,220,0);node.r=value;connect(node,'',slab,pin)
        if not MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output failed')
    mat.set_editor_property('two_sided',False);MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);mat.set_editor_property('used_with_morph_targets',True)
    errors=MEL.recompile_material(mat)
    if errors:raise RuntimeError('Material compile error '+str(errors))
    save(mat);materials['Researcher_'+family]=mat

print('RESEARCHER_MATERIALS_SAVED',flush=True)
