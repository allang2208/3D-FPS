"""Save separate female animation revisions, retaining timing and all other tracks."""
import gzip,hashlib,json,time
from pathlib import Path
import unreal as u
W=Path(__file__).resolve().parent
DEST='/Game/Characters/KaitlinPlayer20261023/WeaponContacts20261024/Animations'
E=u.EditorAssetLibrary
receipt=W/'saved_assets.json'
saved=json.loads(receipt.read_text()) if receipt.exists() else {}
plan=json.loads((W/'selected.json').read_text())
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
finish=lambda:u.SystemLibrary.execute_console_command(world,'Editor.AsyncAssetCompilationFinishAll')
started=time.monotonic();written=0
for key,spec in plan.items():
    if key in saved:continue
    source=u.load_asset(spec['target'])
    name='KGrip_'+key+'_'+spec['roles'][0].replace('.','_')
    path=DEST+'/'+name
    if E.does_asset_exist(path):raise RuntimeError('Unreceipted output already exists: '+path)
    clip=u.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,DEST,source)
    if not clip:raise RuntimeError('Cannot duplicate '+spec['target'])
    finish()
    with gzip.open(W/'Authored'/(key+'.json.gz'),'rt',encoding='utf-8') as f:data=json.load(f)
    controller=clip.get_editor_property('controller')
    controller.open_bracket('Fit native female weapon contacts',False)
    try:
        if spec['kind']=='pair':
            for i,bone in enumerate(data['names']):
                keys=[f[i] for f in data['frames']]
                if not controller.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],
                    [u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                    raise RuntimeError('Cannot save arm track '+bone)
        else:
            for curve,(times,values) in data['curves'].items():
                # Recreate this duplicate's transformed contact keys only.
                u.AnimationLibrary.remove_curve(clip,curve,False)
                u.AnimationLibrary.add_curve(clip,curve,u.RawCurveTrackTypes.RCT_FLOAT,False)
                u.AnimationLibrary.add_float_curve_keys(clip,curve,times,values)
    finally:controller.close_bracket(False)
    E.set_metadata_tag(clip,'KaitlinWeaponContactRevision','20261024_V1')
    E.set_metadata_tag(clip,'MaleContactSource',spec['source'])
    E.set_metadata_tag(clip,'PreviousFemaleSource',spec['target'])
    finish()
    if not E.save_loaded_asset(clip,False):raise RuntimeError('Cannot save '+path)
    finish()
    saved[key]={'asset':clip.get_path_name(),'previous':spec['target'],'male':spec['source'],
                'roles':spec['roles'],'keys':data['keys'],'rate':data['rate'],
                'authored_sha256':hashlib.sha256((W/'Authored'/(key+'.json.gz')).read_bytes()).hexdigest()}
    receipt.write_text(json.dumps(saved,indent=2),encoding='utf-8')
    written+=1
    if time.monotonic()-started>70:break
finish()
(W/'save_status.json').write_text(json.dumps({'remaining':len(plan)-len(saved),'complete':len(plan)==len(saved)}))
print('WEAPON_CONTACT_ASSETS_SAVED',written,'remaining',len(plan)-len(saved))
