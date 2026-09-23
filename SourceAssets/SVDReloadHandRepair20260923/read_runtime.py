"""Read current SVD reload references and imported poses without changing play state."""
import unreal as u
import json
from pathlib import Path

O = Path('D:/FPS3D/FPSGAME/SourceAssets/SVDReloadHandRepair20260923')
auth = json.loads((O.parent/'SVDContactWrap20260923/authoring.json').read_text())
mesh = u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
bones = ['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l',
         'lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','WPN_root','WPN_SOCKET_Magazine']
for digit in ['thumb','index','middle','ring','pinky']:
    if digit != 'thumb': bones.append(digit+'_metacarpal_l')
    bones.extend(digit+'_'+suffix+'_l' for suffix in ['01','02','03'])

def transform(t):
    return {'p':[getattr(t.translation,k) for k in 'xyz'],
            'q':[getattr(t.rotation,k) for k in 'xyzw'],
            's':[getattr(t.scale3d,k) for k in 'xyz']}

report = {'mesh':mesh.get_path_name(),'clips':{},'runtime':[]}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['PIE_active'] = bool(world)
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for comp in actor.get_components_by_class(u.SkeletalMeshComponent):
            sk = comp.get_skinned_asset()
            if not sk or '/SVDDragunov' not in sk.get_path_name(): continue
            entry = {'actor':actor.get_name(),'component':comp.get_name(),'mesh':sk.get_path_name()}
            try:
                data=comp.get_editor_property('animation_data')
                entry['animation_data']=str(data)
                anim=data.get_editor_property('anim_to_play')
                entry['animation']=anim.get_path_name() if anim else None
            except Exception as exc: entry['animation_read_note']=str(exc)
            entry['bones']={n:transform(comp.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in bones}
            report['runtime'].append(entry)

for key,info in auth.items():
    a=u.load_asset(info['path'])
    data=a.get_editor_property('asset_import_data')
    row={'asset':a.get_path_name(),'source':data.get_first_filename(),'seconds':a.get_play_length(),'poses':{}}
    if key == 'base/reload':
        for mode in ['SOURCE','COMPRESSED']:
            opt=u.AnimPoseEvaluationOptions()
            opt.evaluation_type=getattr(u.AnimDataEvalType,mode)
            opt.optional_skeletal_mesh=mesh
            row['poses'][mode]={}
            for f in [0,49,80,120,160,200,220,240,252,268,284,302]:
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,opt)
                row['poses'][mode][str(f)]={n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in bones}
    report['clips'][key]=row

(O/'runtime_before.json').write_text(json.dumps(report,indent=2))
print('SVD_HAND_RUNTIME_READ',json.dumps({'PIE':report['PIE_active'],'runtime':[{k:v for k,v in r.items() if k!='bones'} for r in report['runtime']],
      'sources':{k:v['source'] for k,v in report['clips'].items()}},ensure_ascii=True))
