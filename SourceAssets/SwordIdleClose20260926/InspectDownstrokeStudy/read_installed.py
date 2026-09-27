"""User-requested read-only diagnosis: installed Inspect downstroke, both grips."""
import ast,hashlib,json,math
from pathlib import Path
import unreal as u
P=Path(__file__).parent
ROOT=Path(u.Paths.project_dir()).resolve()
tree=ast.parse((P.parent/'author_idle_close.py').read_text(encoding='utf-8'))
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in
    ('add','sub','mul','hadamard','divide','dot','length','unit','cross','inverse','qmul','rotate','unpack','compose')]
exec(compile(ast.Module(body=functions,type_ignores=[]),'pose_math','exec'),globals())
mesh=u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
comp=u.SkeletalMeshComponent();comp.set_skeletal_mesh_asset(mesh)
names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
parents={n:str(comp.get_parent_bone(n)) for n in names}
watch=['WPN_root','upperarm_r','lowerarm_r','hand_r','index_01_r','middle_01_r','pinky_01_r','thumb_01_r','hand_l']
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
identity={'p':(0,0,0),'q':(0,0,0,1),'s':(1,1,1)}
report={'game_run':False,'asset_modified':False,'families':{}}
for variant,folder in [('Standard','/Game/Weapons/AzureRunesword20260913'),
                       ('LongGrip','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations')]:
    path=folder+'/A_RuneSword_Inspect';a=u.load_asset(path)
    disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    before=json.loads((P.parent/variant/'Inspect_before.json').read_text())
    authored=json.loads((P.parent/variant/'Inspect_keys.json').read_text())
    rows=[]
    for frame in range(73):
        t=frame/120.
        options.evaluation_type=u.AnimDataEvalType.SOURCE
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options)
        world={n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
        options.evaluation_type=u.AnimDataEvalType.COMPRESSED
        compressed=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options)
        cw={n:unpack(u.AnimPoseExtensions.get_bone_pose(compressed,n,u.AnimPoseSpaces.WORLD)) for n in watch}
        f=round(t/before['seconds']*before['frames'])
        old=dict(world)
        for n in names:
            if n in before['samples'][f]['bones']:
                old[n]=compose(old.get(parents[n],identity),before['samples'][f]['bones'][n])
        rows.append({'seconds':t,'world':{n:world[n] for n in watch},
                     'max_compression_cm':max(length(sub(world[n]['p'],cw[n]['p'])) for n in watch),
                     'idle_adjustment_cm':max(length(sub(world[n]['p'],old[n]['p'])) for n in ('hand_r','hand_l','WPN_root')),
                     'posture_weight':authored['samples'][f]['posture_weight']})
    m=a.get_editor_property('data_model_interface')
    report['families'][variant]={'asset':path,'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),
        'length':a.get_play_length(),'model_frames':m.get_number_of_frames(),'model_rate':str(m.get_frame_rate()),'samples':rows}
(P/'installed_downstroke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('INSPECT_DOWNSTROKE_READ_ONLY_COMPLETE',flush=True)
