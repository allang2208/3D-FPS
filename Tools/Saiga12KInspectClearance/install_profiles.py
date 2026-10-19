"""Create six private layers; existing shared clips and old profiles are untouched."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KInspectClearance20261018');D='/Game/Weapons/Saiga12K/InspectClearance20261018/Profiles';E=u.EditorAssetLibrary
if not (O/'Receipts/production-ready.json').exists():raise RuntimeError('Authoring still in progress; do not save provisional layers')
receipt={'complete':False,'saved':[],'runtime_tested':False,'execution_mode':'authorized_isolated_commandlet','dirty_before':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
for family in ('base','drum','angled','vertical','canted','prism'):
    path=D+'/DA_'+family;spec=json.loads((O/'Profiles'/('DA_'+family+'.json')).read_text())
    if E.does_asset_exist(path):raise RuntimeError('Preserve existing '+path)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
    asset=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_'+family,D,u.WeaponGripProfile,factory)
    if not asset:raise RuntimeError('Create failed '+path)
    shared={'family':family,'clips':[c for c in spec['clips'] if not c.get('retained')]}
    if not asset.set_shared_clips_from_json(json.dumps(shared)):raise RuntimeError('Layer import failed '+family)
    for c in spec['clips']:
        if c.get('retained'):asset.keep_clip(u.load_asset(c['base']),u.load_asset(c['retained']))
    E.set_metadata_tag(asset,'SaigaInspectClearanceAuthor','Tools/Saiga12KInspectClearance/author_clearance.py')
    E.set_metadata_tag(asset,'SaigaInspectClearanceRevision',('Inspect support-arm clearance; fixed palm and fingers; other clips retained' if family in ('vertical','prism','canted') else 'Original profile retained for complete Saiga family routing'))
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
    receipt['saved'].append({'family':family,'path':asset.get_path_name(),'clips':len(spec['clips'])});(O/'Receipts/profiles-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print('SAIGA_INSPECT_CLEARANCE_PROFILE_SAVED',family,flush=True)
receipt['complete']=True;(O/'Receipts/profiles-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')


# Publish the source route only once all six new assets are on disk.
header=Path('D:/FPS3D/FPSGAME/Source/FPSGAME/Weapons/Saiga12KAttachments.h')
source=header.read_text(encoding='utf8')
old='/Game/Weapons/Saiga12K/Drum20261018/Profiles/DA_'
new='/Game/Weapons/Saiga12K/InspectClearance20261018/Profiles/DA_'
if old not in source and new not in source:raise RuntimeError('Saiga profile routing changed in parallel; preserve it')
header.write_text(source.replace(old,new),encoding='utf8')
(O/'Receipts/source-promoted.json').write_text(json.dumps({'complete':True,'profile_root':D}),encoding='utf8')
