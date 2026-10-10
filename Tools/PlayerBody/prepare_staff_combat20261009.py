"""Retarget local CC0 combat donors to Jason and read their source pose tracks."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonStaffCombat20261009'
DEST = '/Game/Characters/JasonPlayer20261003/StaffPunch20261009/Donors'
OUT.mkdir(parents=True, exist_ok=True)
lib = u.EditorAssetLibrary
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
target = u.load_asset(cfg['body_mesh'])
ref = target.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
comp = u.new_object(u.SkeletalMeshComponent)
comp.set_skeletal_mesh_asset(target)
parents = [names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names]

def pack(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]

def read(clip):
    opt = u.AnimPoseEvaluationOptions()
    opt.optional_skeletal_mesh = target
    opt.evaluation_type = u.AnimDataEvalType.SOURCE
    length = clip.get_play_length()
    frames = []
    for i in range(round(length*60)+1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/60,length),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    return dict(asset=clip.get_path_name(),duration=length,rate=60,frames=frames)

data = dict(mesh=target.get_path_name(),names=names,parents=parents,
    reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],clips={})
sets = [
    ('KayKit',ROOT/'SourceAssets/ThirdPersonSwordFree20261005/imported-sources.json',
     '/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Rig/RTG_KayKit_Jason_Sword',
     {'Punch':'Melee_Unarmed_Attack_Punch_A','Chop':'Melee_1H_Attack_Chop'}),
    ('UAL2',ROOT/'SourceAssets/ThirdPersonSwordDonorRepair20261006/imported-sources.json',
     '/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source/Rig/RTG_UAL2_Jason_Sword',
     {'Hook':'Melee_Hook','HookRecover':'Melee_Hook_Rec'})]
for label,file,rig,selection in sets:
    info = json.loads(file.read_text())
    if label=='KayKit': info=info[label]
    for key,suffix in selection.items():
        path=next(p for n,p in info['clips'].items() if n.endswith('_'+suffix))
        source=u.load_asset(path)
        saved=DEST+'/J_'+source.get_name()
        clip=u.load_asset(saved) if lib.does_asset_exist(saved) else None
        if not clip:
            inputs=u.IKRetargetBatchOperationInputs()
            inputs.assets_to_retarget=[lib.find_asset_data(path)]
            inputs.source_mesh=u.load_asset(info['mesh'])
            inputs.target_mesh=target
            inputs.ik_retarget_asset=u.load_asset(rig)
            inputs.prefix='J_'
            inputs.target_path=DEST
            inputs.include_referenced_assets=False
            inputs.overwrite_existing_files=False
            clip=next(a.get_asset() for a in u.IKRetargetBatchOperation.run_batch_retarget(inputs) if isinstance(a.get_asset(),u.AnimSequence))
            if not lib.save_loaded_asset(clip,False): raise RuntimeError('Cannot save '+saved)
        data['clips'][label+'.'+key]=read(clip)
        data['clips'][label+'.'+key]['source']=path
data['idle']=read(u.load_asset(cfg['clips']['Unarmed.Idle']))
(OUT/'donors.json').write_text(json.dumps(data,separators=(',',':')))
print('STAFF_COMBAT_DONORS_SAVED '+str(OUT/'donors.json'))
