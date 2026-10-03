"""Read available sword grip/motion references and an existing pawn, without playing."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonTwoHandSword20261003'
OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
def path(a): return a.get_path_name() if a else None
def vec(v): return [v.x,v.y,v.z]
def trans(t): return {'p':vec(t.translation),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':vec(t.scale3d)}
bones=['root','pelvis','spine_03','WPN_root']+[b+'_'+s for s in ('r','l') for b in
       ['clavicle','upperarm','lowerarm','hand']+[d+'_%02d'%j for d in ('thumb','index','middle','ring','pinky') for j in (1,2,3)]]
def poses(p):
    names={str(x) for x in u.AnimPoseExtensions.get_bone_names(p)}
    return {b:trans(u.AnimPoseExtensions.get_bone_pose(p,b,u.AnimPoseSpaces.WORLD)) for b in bones if b in names}
report={'clips':{},'runtime':[],'reference':{}}
body=u.load_asset(cfg['body_mesh'])
native=u.load_asset('/Game/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    if pawn:
        sword=pawn.get_component_by_class(u.RuneSwordComponent)
        if sword:
            source=sword.get_editor_property('viewmodel')
            if source and source.get_skeletal_mesh_asset():native=source.get_skeletal_mesh_asset()
        for m in pawn.get_components_by_class(u.SkeletalMeshComponent):
            a=m.get_skeletal_mesh_asset()
            if not a:continue
            if m==pawn.mesh or (sword and m==source) or m.get_class().get_name()=='FPSBodyWeaponMeshComponent':
                report['runtime'].append({'component':m.get_name(),'class':m.get_class().get_name(),'mesh':path(a),
                    'frame':trans(m.get_world_transform()),'visible':m.is_visible(),
                    'bones':{b:trans(m.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT)) for b in bones if m.does_socket_exist(b)}})
        if sword:
            report['current_clips']={str(k):path(v) for k,v in sword.get_editor_property('animations').items()}
for name,m in [('body',body),('source',native)]:
    report['reference'][name]={'mesh':path(m),'pose':poses(m.skeleton.get_reference_pose())}
paths={'BodyGrip':cfg['clips']['Melee.Grip']}
for variant,folder in [('standard','/Game/Weapons/AzureRunesword20260913'),('long','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations')]:
    for role in ('Idle','Walk','Slash1','Slash2','Thrust','Overhead','Guard','HeavyCharge','HeavyRelease'):
        paths[variant+'.'+role]=folder+'/A_RuneSword_'+role
for key,p in paths.items():
    clip=u.load_asset(p)
    if not isinstance(clip,u.AnimSequence):continue
    options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=body if key=='BodyGrip' else native
    report['clips'][key]={'path':path(clip),'seconds':clip.get_play_length(),
        'samples':[{'t':clip.get_play_length()*i/8,'pose':poses(u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/8,options))} for i in range(9)]}
(OUT/'sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TWO_HAND_SWORD_SOURCES_SAVED '+str(OUT/'sources.json'))
