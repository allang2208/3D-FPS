"""Read saved compressed bed motion before publication; no game is started."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','MeshyBed20261024')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
source=read(OUT/'authored.json');saved=read(OUT/'assets_saved.json');baseline=read(OUT/'baseline_routes.json')
rig={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};rig['clips']={};reports={}
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
body=read(ROOT/'Content/ColdSteelData/player_body.json')
variants={'default':{'mesh':source['mesh'],'clips':{r:saved['default'].get(r,body['clips'].get(r)) for r in source['clips']}},**{
    n:{'mesh':v['mesh'],'clips':{r:saved['variants'][n].get(r,body['body_variants'][n]['clips'].get(r)) for r in source['clips']}} for n,v in baseline['variants'].items()}}
nodes=['pelvis','head','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','thigh_l','calf_l','foot_l','thigh_r','calf_r','foot_r']
nodes.extend(digit+'_01_'+side for side in ('l','r') for digit in ('middle','index','pinky'))
for variant,spec in variants.items():
    mesh=u.load_asset(spec['mesh']);opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
    reports[variant]={'mesh':mesh.get_path_name(),'names':nodes,'clips':{}}
    for role,path in spec['clips'].items():
        clip=u.load_asset(path)
        if clip.get_editor_property('skeleton')!=mesh.skeleton:raise RuntimeError('Bed/native skeleton mismatch '+variant+'/'+role)
        duration=clip.get_play_length();count=round(duration*30)+1;frames=[];samples=[]
        for i in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/(count-1),opt)
            if variant=='default':frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in source['names']])
            samples.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in nodes])
        reports[variant]['clips'][role]={'asset':path,'duration':duration,'rate':30,'world':samples}
        if frames:rig['clips'][role]={'asset':path,'duration':duration,'rate':30,'frames':frames,'evaluation':'compressed'}
        print('MESHY_BED_READ',variant,role,flush=True)
dest=OUT/'ReviewSaved';dest.mkdir(exist_ok=True)
(dest/'saved_poses.json').write_text(json.dumps(rig,separators=(',',':')))
(OUT/'native_saved_samples.json').write_text(json.dumps(reports,separators=(',',':')))
print('MESHY_BED_COMPRESSED_READ_COMPLETE',flush=True)
