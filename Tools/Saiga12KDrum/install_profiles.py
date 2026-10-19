"""Create six private layers; existing shared clips and old profiles are untouched."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KDrum20261018');D='/Game/Weapons/Saiga12K/Drum20261018/Profiles';E=u.EditorAssetLibrary
receipt={'complete':False,'saved':[],'runtime_tested':False}
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
    E.set_metadata_tag(asset,'SaigaDrumAuthor','Tools/Saiga12KDrum/author_profiles.py')
    E.set_metadata_tag(asset,'SaigaDrumRevision','20-round forward drum; fitted native support chain; source free-drop and grip release; existing inspect retained')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
    receipt['saved'].append({'family':family,'path':asset.get_path_name(),'clips':len(spec['clips'])});(O/'Receipts/profiles-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print('SAIGA_DRUM_PROFILE_SAVED',family,flush=True)
receipt['complete']=True;(O/'Receipts/profiles-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
