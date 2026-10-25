"""Read compiled exit samples for Jason and Kaitlin, without running a game."""
import copy
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/FurnitureRest20261022/ArmrestExit20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
data=read(OUT/'authored.json')
old_rig=copy.deepcopy(data)
saved=read(OUT/'assets_saved.json')
baseline=read(OUT/'baseline_routes.json')
report={}
bones=[n+'_'+side for side in ('l','r') for n in ('upperarm','lowerarm','hand')]

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]


variants={'default':{'mesh':data['mesh'],'clips':baseline['default']},**baseline['variants']}
for variant,spec in variants.items():
    mesh=u.load_asset(spec['mesh'])
    opt=u.AnimPoseEvaluationOptions()
    opt.optional_skeletal_mesh=mesh
    opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
    routes=saved['default'] if variant=='default' else saved['variants'][variant]
    report[variant]={'mesh':mesh.get_path_name(),'bones':bones,'previous':{},'current':{}}
    for label,clips in [('previous',spec['clips']),('current',routes)]:
        for role,path in clips.items():
            clip=u.load_asset(path)
            if not clip or clip.get_editor_property('skeleton')!=mesh.skeleton:
                raise RuntimeError('Exit/native skeleton mismatch: '+variant+'/'+role)
            duration=clip.get_play_length()
            frames=[];samples=[]
            count=round(duration*30)+1
            for i in range(count):
                time=duration*i/(count-1)
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opt)
                samples.append({'time':time,
                    'local':[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in bones],
                    'world':[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones]})
                if variant=='default':
                    frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['names']])
            report[variant][label][role]={'asset':path,'duration':duration,'rate':30,'samples':samples}
            if frames:
                rig=data if label=='current' else old_rig
                rig['clips'][role]={'asset':path,'duration':duration,'rate':30,'frames':frames,'evaluation':'compressed'}
            print('ARMREST_EXIT_READ',variant,label,role,flush=True)
dest=OUT/'ReviewSaved';dest.mkdir(exist_ok=True)
(dest/'saved_poses.json').write_text(json.dumps(data,separators=(',',':')))
before=OUT/'BeforeSaved';before.mkdir(exist_ok=True)
(before/'saved_poses.json').write_text(json.dumps(old_rig,separators=(',',':')))
(OUT/'saved_arm_samples.json').write_text(json.dumps(report,separators=(',',':')))
print('ARMREST_EXIT_COMPRESSED_READ_COMPLETE',flush=True)
