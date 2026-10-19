"""Save new, private Saiga inspection layers without touching a playing profile."""
import unreal as u
import json
from pathlib import Path

O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KInspect20261018')
ROOT='/Game/Weapons/Saiga12K/Inspect20261018/Profiles'
E=u.EditorAssetLibrary
receipt={'complete':False,'saved':[],'runtime_tested':False}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for family in ('base','angled','vertical','canted','prism'):
    spec=json.loads((O/'Profiles'/('DA_'+family+'.json')).read_text())
    path=ROOT+'/DA_'+family
    if path in dirty:raise RuntimeError('Unsaved private profile: '+path)
    # This batch creates five new packages. Existing packages belong to a
    # previous save or another task and must not be overwritten by this entry.
    if E.does_asset_exist(path):
        raise RuntimeError('Private profile already exists; preserve it: '+path)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
    asset=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_'+family,ROOT,u.WeaponGripProfile,factory)
    if not asset:raise RuntimeError('Profile creation failed: '+path)
    kept=[c for c in spec['clips'] if c.get('retained')]
    shared={'family':family,'clips':[c for c in spec['clips'] if not c.get('retained')]}
    if not asset.set_shared_clips_from_json(json.dumps(shared)):raise RuntimeError('Sparse layer import failed: '+path)
    for c in kept:asset.keep_clip(u.load_asset(c['base']),u.load_asset(c['retained']))
    E.set_metadata_tag(asset,'SaigaInspectAuthor','Tools/Saiga12KInspect/author_profiles.py')
    E.set_metadata_tag(asset,'SaigaInspectRevision','20261018: installed support contact throughout inspection; native arm chain')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed: '+path)
    receipt['saved'].append({'family':family,'path':asset.get_path_name(),'clips':len(spec['clips'])})
    (O/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('SAIGA_INSPECT_SAVED',family,flush=True)
receipt['complete']=True
(O/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
