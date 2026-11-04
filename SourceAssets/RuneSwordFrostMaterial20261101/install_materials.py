"""Install transferred donor PBR as mode 6 on both native-rune masters."""
from pathlib import Path
import json,shutil
import unreal as u
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
REVISION='RuneSwordFrost20261101V1'
DEST='/Game/Weapons/AzureRunesword20260913/FrostFinish20261101'
MASTERS=['/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
 '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold']
textures={}
for kind in ['BaseColor','Normal','Roughness','Metallic']:
    name='T_RuneSword_Frost_'+kind
    task=u.AssetImportTask()
    for key,value in dict(filename=str(P/'Textures'/(name+'.png')),destination_path=DEST,
                         destination_name=name,automated=True,replace_existing=True,save=False).items():
        task.set_editor_property(key,value)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(DEST+'/'+name)
    if not tex:raise RuntimeError('Frost texture import failed: '+kind)
    tex.set_editor_property('srgb',kind=='BaseColor')
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WORLD)
    if kind=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif kind!='BaseColor':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    if not E.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed: '+kind)
    textures[kind]=tex
saved=[]
for path in MASTERS:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing master: '+path)
    if E.get_metadata_tag(mat,'RuneSwordFrostRevision')==REVISION:
        saved.append({'asset':path,'already_current':True});continue
    source=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/source.relative_to(ROOT/'Content')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    finishes=[n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom)
              and str(n.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    if len(finishes)!=4:raise RuntimeError('Existing PBR finish nodes missing: '+path)
    for field,kind in [('MP_BASE_COLOR','BaseColor'),('MP_NORMAL','Normal'),('MP_ROUGHNESS','Roughness'),('MP_METALLIC','Metallic')]:
        finish=next(n for n in finishes if field+':' in str(n.get_editor_property('desc')))
        sample=L.create_material_expression(mat,u.MaterialExpressionTextureSample)
        sample.set_editor_property('texture',textures[kind])
        sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        sample.set_editor_property('sampler_type',sampler)
        sample.set_editor_property('desc',REVISION+' '+kind)
        inputs=list(finish.get_editor_property('inputs'))
        pin=u.CustomInput();pin.set_editor_property('input_name','FrostSurface');inputs.append(pin)
        finish.set_editor_property('inputs',inputs)
        if not L.connect_material_expressions(sample,'RGB' if kind in ['BaseColor','Normal'] else 'R',finish,'FrostSurface'):
            raise RuntimeError('Frost input connection failed: '+kind)
        value='FrostSurface'
        if kind=='Normal':value='normalize(float3(Base.xy+FrostSurface.xy,Base.z*FrostSurface.z))'
        result='lerp(Base,'+value+',1-saturate(Mask*3.0))'
        if kind=='Normal':result='normalize('+result+')'
        code='// '+REVISION+'\nif(Mode>5.5 && Mode<6.5) return '+result+';\n'
        finish.set_editor_property('code',code+finish.get_editor_property('code'))
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Frost material compilation failed: '+str(errors))
    E.set_metadata_tag(mat,'RuneSwordFrostRevision',REVISION)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Master save failed: '+path)
    saved.append({'asset':path,'saved':True,'mode':6})
# Reuse the accepted grayscale framed donor blade icon for this extracted finish.
icons=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
name='ue_rune_sword_blade_material_frost_crystal'
source=icons/'ue_frost_crystal_sword_blade_1_false.png'
destination=icons/(name+'.png')
shutil.copy2(source,destination)
task=u.AssetImportTask()
task.filename=str(destination);task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913'
task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
icon=u.load_asset(task.destination_path+'/'+name)
if not icon:raise RuntimeError('Frost icon import failed')
for key,value in [('lod_group',u.TextureGroup.TEXTUREGROUP_UI),('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON),
                  ('srgb',True),('never_stream',True),('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)]:
    icon.set_editor_property(key,value)
if not E.save_loaded_asset(icon,False):raise RuntimeError('Frost icon save failed')
(P/'material-receipt.json').write_text(json.dumps({'revision':REVISION,'materials':saved,
    'textures':[t.get_path_name() for t in textures.values()],'icon':icon.get_path_name(),
    'gameplay_tested':False},indent=2)+'\n',encoding='utf8')
print('FROST_MATERIALS_SAVED',json.dumps(saved))
