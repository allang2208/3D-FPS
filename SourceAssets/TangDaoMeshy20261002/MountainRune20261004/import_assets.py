"""Background authoring: preserve each current blade material, add mountain mode."""
from pathlib import Path
import json, runpy, shutil
import unreal as u

P=Path(__file__).resolve().parent
EXT=runpy.run_path(str(P/'catalog_extension.py'),run_name='mountain_catalog')
ROOT,D,REVISION=EXT['ROOT'],EXT['UE_ROOT'],EXT['REVISION']
E,L=u.MaterialEditingLibrary,u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
receipt={'revision':REVISION,'complete':False,'assets':[],
         'material_bindings':{},'temporal_bindings':{},'runtime_tested':False}

def record():
    (P/'Records/import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def save(asset):
    L.set_metadata_tag(asset,'TangDaoMountainRevision',REVISION)
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()

def duplicate(source,path):
    asset=u.load_asset(path)
    if asset:
        if L.get_metadata_tag(asset,'TangDaoMountainRevision')!=REVISION:
            raise RuntimeError('Preserved unowned asset '+path)
        return asset
    folder,name=path.rsplit('/',1)
    asset=A.duplicate_asset(name,folder,source)
    if not asset:raise RuntimeError('Duplicate failed: '+path)
    L.set_metadata_tag(asset,'TangDaoMountainRevision',REVISION)
    return asset

def texture(file,path,is_icon=False):
    old=u.load_asset(path)
    if old and L.get_metadata_tag(old,'TangDaoMountainRevision')!=REVISION:
        raise RuntimeError('Preserved unowned texture '+path)
    folder,name=path.rsplit('/',1)
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory()
    A.import_asset_tasks([t]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed: '+path)
    asset.set_editor_property('srgb',is_icon)
    asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON if is_icon else u.TextureCompressionSettings.TC_GRAYSCALE)
    asset.set_editor_property('never_stream',True)
    if is_icon:asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    else:
        asset.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
        asset.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
        asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    save(asset);return asset

mask=texture(P/'Artwork/TangDao_MountainRune_Mask.png',D+'/Textures/T_Mask_mountain_rune')
modules=json.loads((ROOT/'Content/ColdSteelData/tang-dao-modules.json').read_text(encoding='utf-8-sig'))
sources=sorted({v for row in modules['slots']['blade_1'].values() for v in row.get('materials',{}).values()})
prefix=(P/'mountain_emission.hlsl').read_text(encoding='utf-8')+'\n'
for source_path in sources:
    source=u.load_asset(source_path)
    if not source:raise RuntimeError('Missing current blade material '+source_path)
    base=source_path.split('.')[0].rsplit('/',1)[-1]
    path=D+'/Materials/'+base+'_Mountain'
    if source_path.startswith(D+'/Materials/'):
        path=source_path.split('.')[0]
    material=duplicate(source,path)
    for n in E.get_material_expressions(material):
        if isinstance(n,u.MaterialExpressionCustom):
            code=n.get_editor_property('code')
            if 'RuneTexture' in code and 'RuneMode' in code and 'TangDao mode 7:' not in code:
                n.set_editor_property('code',prefix+code)
    errors=list(E.recompile_material(material) or [])
    if errors:raise RuntimeError('Material compile: '+str(errors))
    save(material)
    temporal=duplicate(material,path+'_Whirlwind')
    expressions=E.get_material_expressions(temporal)
    if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in expressions):
        response=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
        one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
        if not E.connect_material_expressions(one,'',response,''):raise RuntimeError('Temporal response connection failed')
    errors=list(E.recompile_material(temporal) or [])
    if errors:raise RuntimeError('Temporal material compile: '+str(errors))
    save(temporal)
    receipt['material_bindings'][source_path]=material.get_path_name()
    receipt['temporal_bindings'][material.get_path_name()]=temporal.get_path_name()
icon_name='ue_tang_dao_blade_2_mountain_rune'
target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon_name+'.png')
shutil.copy2(P/'Icons'/(icon_name+'.png'),target)
texture(target,'/Game/ColdSteelData/AttachmentIcons20260913/'+icon_name,True)
receipt['complete']=True;record();EXT['install']()
print('TANGDAO_MOUNTAIN_ASSETS_SAVED '+str(len(receipt['assets'])),flush=True)
