"""Background import/save: dedicated gold Bagua decal and native blade rune branch."""
from pathlib import Path
import json,shutil,runpy
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
EXT=runpy.run_path(str(P/'catalog_extension.py'));D=EXT['UE']
E,L=u.MaterialEditingLibrary,u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools();REV='ZhenmoRune20261005'
receipt={'complete':False,'assets':[],'runtime_tested':False,'material_bindings':{}}
if (P/'import_receipt.json').exists():
    receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'));receipt['complete']=False
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Exit PIE before saving Zhenmo assets')
def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    L.set_metadata_tag(asset,'ZhenmoRevision',REV)
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()
def texture(file,path,icon=False):
    existing=u.load_asset(path)
    if existing and existing.get_path_name() in receipt['assets']:return existing
    folder,name=path.rsplit('/',1)
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory()
    A.import_asset_tasks([t]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed '+path)
    asset.set_editor_property('srgb',icon)
    asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_GRAYSCALE)
    if icon:
        asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
        asset.set_editor_property('never_stream',True)
        asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    else:
        asset.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);asset.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    save(asset);return asset
mask=texture(P/'Artwork/Zhenmo_Blade_Rune.png',D+'/Textures/T_Mask_zhenmo_rune')
field=texture(P/'Artwork/Zhenmo_Bagua_Field.png',D+'/Textures/T_ZhenmoBaguaField')
def dup(source,path):
    asset=u.load_asset(path)
    if asset:return asset
    asset=L.duplicate_asset(source.get_path_name(),path)
    if not asset:raise RuntimeError('Duplicate failed '+path)
    return asset

# A private material branch preserves the current silver relief/POM and all older modes.
modules=json.loads((ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
sources=sorted({v for row in modules['slots']['blade_1'].values() for v in row.get('materials',{}).values()})
prefix=(P/'zhenmo_emission.hlsl').read_text(encoding='utf-8')+'\n'
temporal_bindings={}
for source_path in sources:
    source=u.load_asset(source_path)
    if not source:raise RuntimeError('Missing current blade surface '+source_path)
    name=source.get_name()
    path=source_path.split('.')[0] if source_path.startswith(D+'/Materials/') else D+'/Materials/'+name+'_Zhenmo'
    material=dup(source,path)
    saved_temporal=u.load_asset(path+'_Whirlwind')
    if material.get_path_name() in receipt['assets'] and saved_temporal and saved_temporal.get_path_name() in receipt['assets']:
        receipt['material_bindings'][source_path]=material.get_path_name()
        temporal_bindings[material.get_path_name()]=saved_temporal.get_path_name()
        continue
    for node in E.get_material_expressions(material):
        if isinstance(node,u.MaterialExpressionCustom):
            code=node.get_editor_property('code')
            if 'RuneTexture' in code and 'RuneMode' in code and 'Zhenmo mode 8:' not in code:node.set_editor_property('code',prefix+code)
    errors=list(E.recompile_material(material) or [])
    if errors:raise RuntimeError('Blade material compile '+str(errors))
    save(material)
    temporal=dup(material,path+'_Whirlwind')
    for node in E.get_material_expressions(temporal):
        if isinstance(node,u.MaterialExpressionCustom):
            code=node.get_editor_property('code')
            if 'RuneTexture' in code and 'RuneMode' in code and 'Zhenmo mode 8:' not in code:node.set_editor_property('code',prefix+code)
    if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in E.get_material_expressions(temporal)):
        response=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
        one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
        E.connect_material_expressions(one,'',response,'')
    errors=list(E.recompile_material(temporal) or [])
    if errors:raise RuntimeError('Temporal material compile '+str(errors))
    save(temporal);receipt['material_bindings'][source_path]=material.get_path_name()
    temporal_bindings[material.get_path_name()]=temporal.get_path_name()

# Ground-only V3 replaces the tall projected decal; retain its original mask.
ground_result=runpy.run_path(str(P/'SoftGroundV3/author_soft_ground.py'),run_name='__main__')
for ground_asset in ground_result['SAVED']:
    if ground_asset not in receipt['assets']:receipt['assets'].append(ground_asset)
record()

icon_key='ue_xuanchi_zhenyue_blade_2_zhenmo_rune'
icon_file=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon_key+'.png')
shutil.copy2(P/'zhenmo_rune_icon.png',icon_file)
texture(icon_file,'/Game/ColdSteelData/AttachmentIcons20260913/'+icon_key,True)
def update_modules(root):
    for row in root['slots']['blade_1'].values():
        for key,value in row.get('materials',{}).items():
            if value in receipt['material_bindings']:row['materials'][key]=receipt['material_bindings'][value]
    root['zhenmo_rune_revision']=REV
def update_temporal(root):
    # Same schema as the existing map of opaque blade materials to reactive copies.
    target=root.get('materials',root)
    target.update(temporal_bindings)
EXT['update'](ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json',update_modules)
EXT['update'](ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json',update_temporal)
EXT['install']()
# This final overwrite also upgrades installations with an old completed receipt.
runpy.run_path(str(P/'BladeTalismanV4/install_assets.py'),run_name='__main__')
# Restore the field's accompanying particles with the same complete asset recipe.
runpy.run_path(str(P/'RisingMotes/author_rising_motes.py'),run_name='__main__')
runpy.run_path(str(P/'SoftGroundV3/author_soft_ground.py'),run_name='__main__')
receipt['complete']=True;record()
print('ZHENMO_ASSETS_SAVED '+json.dumps({'count':len(receipt['assets']),'complete':True,'runtime_tested':False}),flush=True)
