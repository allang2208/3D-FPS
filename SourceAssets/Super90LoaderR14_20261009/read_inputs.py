"""Read installed loader inputs for this repair; does not run gameplay or save assets."""
import unreal as u
import json
from pathlib import Path
O=Path(__file__).parent
out={}
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
for branch in ('normal','empty'):
    for count in (1,7):
        name=f'A_Super90_loader_{branch}_{count}'
        a=u.load_asset('/Game/Weapons/Super90/Speedloader20261007/Animations/'+name)
        row={'length':a.get_play_length(),'source':u.EditorAssetLibrary.get_metadata_tag(a,'Super90SpeedloaderSource'),'poses':{}}
        for mode in ('SOURCE','COMPRESSED'):
            opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=getattr(u.AnimDataEvalType,mode);opt.optional_skeletal_mesh=mesh
            poses=[]
            for f in (74,86,90,100,110,114,122):
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,min(f/60,a.get_play_length()),opt)
                points={}
                for n in ('hand_l','WPN_root','WPN_Shell','WPN_SOCKET_Magazine'):
                    t=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
                    points[n]=[t.translation.x,t.translation.y,t.translation.z]
                poses.append({'frame':f,'points':points})
            row['poses'][mode]=poses
        out[name]=row
(O/'installed_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:{'length':v['length'],'source':v['source'],'source_wrist_86_114':[p['points']['hand_l'] for p in v['poses']['SOURCE'] if p['frame'] in (86,114)],'compressed_wrist_86_114':[p['points']['hand_l'] for p in v['poses']['COMPRESSED'] if p['frame'] in (86,114)]} for k,v in out.items()}))
