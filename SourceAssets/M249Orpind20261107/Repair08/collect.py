from pathlib import Path
import unreal as u,pickle,json
r=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
geometry=pickle.load(open(r.parent/'Repair06/geometry.pkl','rb'));names=geometry['names']
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for mode in ('RAW','COMPRESSED'):
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=getattr(u.AnimDataEvalType,mode)
    for role in ('idle','quick_melee'):
        clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role)
        count=round(clip.get_play_length()*240) if role!='idle' else 0
        frames=[]
        for i in range(count+1):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,i/240,opts)
            frames.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names])
        with (r/(mode+'_'+role+'.pkl')).open('wb') as f:pickle.dump(dict(names=names,duration=clip.get_play_length(),fps=240,frames=frames),f)
        print('M249_MELEE_CAPTURE',mode,role,count+1,flush=True)
