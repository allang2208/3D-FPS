"""Read the reported crouch deformation: loaded clips and baked leg transforms only."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonCrouch20261005'
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mesh = u.load_asset(cfg['body_mesh'])
ref = mesh.skeleton.get_reference_pose()
bones = [str(b) for b in u.AnimPoseExtensions.get_bone_names(ref)
         if str(b) in ('root','pelvis') or str(b).startswith(('thigh','calf','foot','ball'))]
def pack(t):
    p,q=t.translation,t.rotation
    return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w]}
def pose_data(pose):
    return {b:pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
report={'mesh':mesh.get_path_name(),'reference':pose_data(ref),'clips':{},'runtime':[]}
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
for key,path in cfg['clips'].items():
    if not key.startswith('Crouch.'):continue
    clip=u.load_asset(path)
    report['clips'][key]={'path':path,'samples':[
        {'t':clip.get_play_length()*i/32,'bones':pose_data(u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/32,options))}
        for i in range(33)]}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    for pawn in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        body=pawn.mesh;anim=body.get_anim_instance()
        report['runtime'].append({'pawn':pawn.get_path_name(),'anim':anim.get_path_name() if anim else None,
            'crouched':pawn.get_editor_property('is_crouched'),
            'bones':{b:pack(body.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT)) for b in bones}})
(OUT/'joint-diagnosis.json').write_text(json.dumps(report),encoding='utf-8')
print('CROUCH_JOINTS '+json.dumps({'clips':len(report['clips']),'bones':len(bones),'runtime':[{'anim':r['anim'],'crouched':r['crouched']} for r in report['runtime']]}))
