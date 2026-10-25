"""Read native female arm locals for a bounded contact correction."""
import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022')/globals().get('FURNITURE_REVISION','MeshyBedSupportedHands20261024')
saved=json.loads((OUT/'assets_saved.json').read_text());base=json.loads((OUT/'baseline_routes.json').read_text())
mesh=u.load_asset(base['variants']['kaitlin']['mesh']);opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
names=[n+'_'+s for s in ('l','r') for n in ('upperarm','lowerarm','hand')];clips={}
for role,path in saved['variants']['kaitlin'].items():
    if role.endswith('.Idle'):continue
    clip=u.load_asset(path);frames=[]
    for j in range(round(clip.get_play_length()*30)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,j/30,opt);frame=[]
        for n in names:
            t=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)
            frame.append([t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z])
        frames.append(frame)
    clips[role]={'source':path,'frames':frames}
(OUT/'kaitlin_arm_locals.json').write_text(json.dumps({'names':names,'clips':clips},separators=(',',':')))
print('KAITLIN_BED_ARM_LOCALS_READ')
