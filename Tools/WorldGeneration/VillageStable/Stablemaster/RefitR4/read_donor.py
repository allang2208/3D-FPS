"""Read the village NPCs' actual standing sequences for fitting on the Meshy skeleton."""
import unreal as u
import json
from pathlib import Path
p=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
out=p/'SourceAssets/HillsVillageStable/StablemasterMeshyR4'
data={}
for mesh_path,seq_path in [
 ('/Game/Characters/VillageTavernKeeper/SK_TavernKeeper','/Game/Characters/VillageTavernKeeper/A_TavernKeeper_Idle'),
 ('/Game/Characters/VillageHerbalist/SK_VillageHerbalist','/Game/Characters/VillageHerbalist/A_VillageHerbalist_Idle')]:
    mesh=u.load_asset(mesh_path);seq=u.load_asset(seq_path)
    if mesh is None or seq is None:raise RuntimeError(seq_path)
    names=['pelvis','spine_01','spine_02','spine_03','neck_01','head','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r','foot_l','foot_r','ball_l','ball_r']
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh
    def frame(pose):
        points=[]
        for n in names:
            v=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
            q=v.rotation;points.append([*v.translation.to_tuple(),q.x,q.y,q.z,q.w])
        return points
    rate=30;count=round(seq.get_play_length()*rate)
    frames=[frame(u.AnimPoseExtensions.get_anim_pose_at_time(seq,i/rate,opts)) for i in range(count+1)]
    data[seq.get_name()]=dict(path=seq_path,names=names,rate=rate,reference=frame(mesh.skeleton.get_reference_pose()),frames=frames)
(out/'npc_standing.json').write_text(json.dumps(data,separators=(',',':')))
print([(k,len(d['frames'])) for k,d in data.items()])
