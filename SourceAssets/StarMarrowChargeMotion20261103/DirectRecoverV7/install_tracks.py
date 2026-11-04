"""Save the authored native tracks without a second endpoint/IK correction pass."""
from pathlib import Path
import json,math,hashlib
import unreal as u
P=Path(__file__).resolve().parent
DEST='/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeMotion20261103'
E=u.EditorAssetLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before saving charge animation')
if any(p.get_name().startswith(DEST+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved charge animation changes')
mesh=u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
receipt={'revision':7,'assets':[],'second_ik_pass':False,'editor_gui_started':False,'gameplay_tested':False}
folders={'Standard':'/Game/Weapons/AzureRunesword20260913',
         'LongGrip':'/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'}
prepared=[]
for variant,folder in folders.items():
    source=P/variant/'tracks.json';data=json.loads(source.read_text());names=list(data['tracks'])
    idle=u.load_asset(folder+'/A_RuneSword_Idle');seq=u.load_asset(DEST+'/'+variant+'/A_StarMarrow_Charge')
    if not idle or not seq:raise RuntimeError('Missing installed clip '+variant)
    model=seq.get_editor_property('data_model_interface');rate=model.get_frame_rate()
    if model.get_number_of_keys() not in (205,337,265) or rate.numerator/rate.denominator!=120:
        raise RuntimeError('Unexpected charge clip clock '+variant)
    # Stop if another edit changed the actual idle used as our solve boundary.
    for n,t in zip(names,u.AnimationLibrary.get_bone_poses_for_time(idle,names,0.,False,mesh)):
        for k in [data['tracks'][n][0],data['tracks'][n][-1]]:
            p,q,s=t.translation,t.rotation,t.scale3d
            error=max(abs(a-b) for a,b in zip(k['p']+k['s'],[p.x,p.y,p.z,s.x,s.y,s.z]))
            dot=abs(sum(a*b for a,b in zip(k['q'],[q.x,q.y,q.z,q.w])))
            if error>.002 or dot<.99999:raise RuntimeError('Idle changed or endpoint differs: '+variant+' '+n)
    prepared.append((variant,seq,data,hashlib.sha256(source.read_bytes()).hexdigest()))
for variant,seq,data,digest in prepared:
    controller=seq.get_editor_property('controller')
    controller.open_bracket('StarMarrow V7 direct idle recovery',False)
    try:
        controller.set_frame_rate(u.FrameRate(data['fps'],1),False)
        controller.set_number_of_frames(u.FrameNumber(round(data['seconds']*data['fps'])),False)
        for n,keys in data['tracks'].items():
            if not controller.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],
                    [u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Cannot write charge track '+variant+' '+n)
    finally:controller.close_bracket(False)
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    if not E.save_loaded_asset(seq,False):raise RuntimeError('Cannot save charge '+variant)
    receipt['assets'].append(dict(variant=variant,path=seq.get_path_name(),saved=True,
        frames=round(data['seconds']*data['fps'])+1,fps=data['fps'],seconds=data['seconds'],tracks_sha256=digest))
    (P/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
    (P.parent/'import-receipt.json').write_text(json.dumps(receipt,indent=2))
    print('ANATOMICAL_CHARGE_SAVED',variant,seq.get_path_name())
print('ANATOMICAL_CHARGE_INSTALLED',len(receipt['assets']))
