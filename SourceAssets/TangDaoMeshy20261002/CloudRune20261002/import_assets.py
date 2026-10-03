"""Author and save the cloud rune while preserving every existing blade atlas."""
from pathlib import Path
import json, runpy, shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
EXT = runpy.run_path(str(P/'catalog_extension.py'),run_name='cloud_rune_extension')
D = EXT['UE_ROOT']
REVISION = EXT['REVISION']
E,L = u.MaterialEditingLibrary,u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Cloud rune authoring requires FPSGAME')
receipt={'revision':REVISION,'complete':False,'assets':[],
         'geometry_changed':False,'shared_rune_material_modified':False,'runtime_tested':False}

def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def save(asset):
    L.set_metadata_tag(asset,'TangDaoCloudRuneRevision',REVISION)
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Cloud rune package save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    record()

def duplicate(source,path):
    current=u.load_asset(path)
    if current:
        if L.get_metadata_tag(current,'TangDaoCloudRuneRevision')!=REVISION:
            raise RuntimeError('Preserved an unowned cloud asset at '+path)
        return current
    folder,name=path.rsplit('/',1)
    asset=A.duplicate_asset(name,folder,source)
    if not asset:raise RuntimeError('Cloud rune material duplication failed: '+path)
    L.set_metadata_tag(asset,'TangDaoCloudRuneRevision',REVISION)
    return asset

def imported(file,path):
    existing=u.load_asset(path)
    if existing and L.get_metadata_tag(existing,'TangDaoCloudRuneRevision')!=REVISION:
        raise RuntimeError('Preserved an unowned cloud texture at '+path)
    folder,name=path.rsplit('/',1)
    task=u.AssetImportTask()
    task.filename=str(file)
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.save=False
    task.factory=u.TextureFactory()
    A.import_asset_tasks([task])
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Cloud texture import failed: '+path)
    return asset

mask=imported(P/'Artwork/TangDao_CloudRune_Mask.png',D+'/Textures/T_Mask_auspicious_cloud_rune')
mask.set_editor_property('srgb',False)
mask.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
mask.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
mask.set_editor_property('never_stream',True)
mask.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
mask.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
save(mask)

prefix=(P/'cloud_emission.hlsl').read_text(encoding='utf-8')+'\n'
for source_path,name in zip(EXT['SOURCE_PATHS'],EXT['MATERIAL_NAMES']):
    source=u.load_asset(source_path)
    if not source:raise RuntimeError('Missing the current blade surface '+source_path)
    original=next(n for n in E.get_material_expressions(source)
                  if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
    code=prefix+original.get_editor_property('code')
    path=D+'/Materials/'+name
    material=duplicate(source,path)
    for n in E.get_material_expressions(material):
        if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'):
            n.set_editor_property('code',code)
        elif isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='RuneTexture':
            n.set_editor_property('texture',mask)
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        elif isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='RuneMode':
            n.set_editor_property('default_value',-1.)
    errors=list(E.recompile_material(material) or [])
    if errors:raise RuntimeError('Cloud blade material compile failed: '+str(errors))
    save(material)
    temporal=duplicate(material,path+'_Whirlwind')
    for n in E.get_material_expressions(temporal):
        if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'):
            n.set_editor_property('code',code)
    nodes=E.get_material_expressions(temporal)
    if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in nodes):
        responsive=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
        one=E.create_material_expression(temporal,u.MaterialExpressionConstant)
        one.set_editor_property('r',1.)
        if not E.connect_material_expressions(one,'',responsive,''):
            raise RuntimeError('Cloud temporal response connection failed')
    errors=list(E.recompile_material(temporal) or [])
    if errors:raise RuntimeError('Cloud temporal material compile failed: '+str(errors))
    save(temporal)

icon_name='ue_tang_dao_blade_2_auspicious_cloud_rune'
target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon_name+'.png')
shutil.copy2(P/'Icons'/(icon_name+'.png'),target)
icon=imported(target,'/Game/ColdSteelData/AttachmentIcons20260913/'+icon_name)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('srgb',True)
icon.set_editor_property('never_stream',True)
save(icon)
receipt.update(complete=True,material_bindings=EXT['MATERIALS'],
               native_draw_path='opaque Substrate blade emission',
               mask_source='Artwork/CloudRune_Alpha.png',icon_source='Icons/'+icon_name+'.png')
record()
EXT['install']()
print('TANGDAO_CLOUD_RUNE_ASSETS_SAVED '+str(len(receipt['assets'])),flush=True)
