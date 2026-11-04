"""Read the first delivered animation backup without replacing live runtime packages."""
import unreal as u,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
c=u.SkeletalMeshComponent();c.set_skeletal_mesh_asset(mesh)
names=[str(c.get_bone_name(i)) for i in range(c.get_num_bones())]
parents={n:str(c.get_parent_bone(n)) for n in names}
def pack(t):
    p=t.translation;q=t.rotation;s=t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])
result=dict(names=names,parents=parents,variants={})
for variant,folder in {'Standard':'/Game/Weapons/AzureRunesword20260913','LongGrip':'/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'}.items():
    seq=u.load_asset('/Game/Developers/CodexStarMarrowFirstVersion/'+variant+'/A_StarMarrow_Charge')
    idle=u.load_asset(folder+'/A_RuneSword_Idle')
    if not seq or not idle:raise RuntimeError('Missing first version or idle '+variant)
    model=seq.get_editor_property('data_model_interface');rate=model.get_frame_rate();fps=rate.numerator/rate.denominator;count=model.get_number_of_keys()
    result['variants'][variant]=dict(fps=fps,seconds=(count-1)/fps,
        source_sha256=hashlib.sha256((P.parent/'AuditV1/Before'/('A_StarMarrow_Charge_'+variant+'.uasset')).read_bytes()).hexdigest(),
        idle=[pack(t) for t in u.AnimationLibrary.get_bone_poses_for_time(idle,names,0.,False,mesh)],
        frames=[[pack(t) for t in u.AnimationLibrary.get_bone_poses_for_time(seq,names,k/fps,False,mesh)] for k in range(count)])
    print('FIRST_CHARGE_READ',variant,count,fps,(count-1)/fps)
(P/'first-version.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
