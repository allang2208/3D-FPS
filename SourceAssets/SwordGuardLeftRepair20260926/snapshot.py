"""Read the installed guard family for the user-requested left-arm diagnosis."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=Path(u.Paths.project_dir()).resolve()
families={'Standard':'/Game/Weapons/AzureRunesword20260913',
          'LongGrip':'/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'}
mesh=u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
comp=u.SkeletalMeshComponent();comp.set_skeletal_mesh_asset(mesh)
names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
parents={n:str(comp.get_parent_bone(n)) for n in names}
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
def pack(t):
    p=t.translation;q=t.rotation;s=t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
def sample(asset,t):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
    return {n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
for variant,folder in families.items():
    out=P/'Before'/variant;out.mkdir(parents=True,exist_ok=True)
    data={'variant':variant,'parents':parents,'clips':{}}
    for clip in ('Idle','Guard','GuardHit','GuardBreak'):
        path=folder+'/A_RuneSword_'+clip;asset=u.load_asset(path)
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        count=asset.get_editor_property('data_model_interface').get_number_of_frames();seconds=asset.get_play_length()
        samples=[{'seconds':i*seconds/count,'world':sample(asset,i*seconds/count)} for i in range(count+1)] if clip!='Idle' else [{'seconds':0.,'world':sample(asset,0.)}]
        data['clips'][clip]={'asset':path,'intervals':count,'seconds':seconds,'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),'samples':samples}
        if clip!='Idle':
            shutil.copy2(disk,out/disk.name)
    (out/'installed.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('GUARD_SNAPSHOT_SAVED',variant,flush=True)
