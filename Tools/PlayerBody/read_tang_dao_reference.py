"""Read Tang Dao's actual donor mesh and configured two-hand idle."""
import json
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME')
def tf(t):
    return {'p':[t.translation.x,t.translation.y,t.translation.z],
            'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
            's':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
bones=['WPN_root']+[a+'_'+s for s in ('r','l') for a in ('upperarm','lowerarm','hand','middle_01','index_01','pinky_01')]
report={}
cfg=json.loads((root/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
body=u.load_asset(cfg['body_mesh'])
post=body.get_editor_property('post_process_anim_blueprint')
report['body']={'mesh':body.get_path_name(),'post_process':post.get_path_name() if post else None,
                'parents':{b:str(body.get_bone_parent(b)) for b in bones if b!='WPN_root'}}
if post:
    default=u.get_default_object(post)
    report['body']['post_defaults']={}
    for n in dir(default):
        if n.startswith('_'):continue
        try:
            v=default.get_editor_property(n)
            report['body']['post_defaults'][n]=str(v)
        except Exception:pass
for label,path in [('tang','/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms'),('azure','/Game/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms')]:
    mesh=u.load_asset(path)
    options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
    idle=u.load_asset('/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle')
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0,options)
    report[label]={'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),
       'idle':{b:tf(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones},
       'mesh_methods':[x for x in dir(mesh) if 'ref' in x or 'bone' in x]}
out=root/'SourceAssets/ThirdPersonTwoHandSword20261003/tang-reference.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(str(out))
