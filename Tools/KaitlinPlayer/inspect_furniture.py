"""Read configured and existing live furniture animation state; no gameplay input."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME'); W=P/'SourceAssets/KaitlinFurniture20261024'; W.mkdir(exist_ok=True)
body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
female=body['body_variants']['kaitlin']; mesh=u.load_asset(female['body_mesh'])
catalog={}
for filename in ('furniture_rest.json','apartment_furniture_rest.json'):
    catalog.update(json.loads((P/'Content/ColdSteelData'/filename).read_text(encoding='utf-8-sig'))['clips'])
report={'clips':{},'live':[]}

def prop(obj,key):
    try:
        value=obj.get_editor_property(key)
        if hasattr(value,'export_text'): return value.export_text()
        if hasattr(value,'items'): return {str(k):v.get_path_name() if v else None for k,v in value.items()}
        return str(value)
    except Exception as exc: return {'unavailable':str(exc)}

for component in u.ObjectIterator(u.FPSPlayerBodyComponent):
    owner=component.get_owner()
    if not owner or not component.get_world(): continue
    sk=component.get_body_mesh()
    anim=sk.get_anim_instance() if sk else None
    if not anim: continue
    state={'owner':owner.get_path_name(),'body_type':str(component.get_body_type()),
           'animation_class':anim.get_class().get_name(),'clips':prop(anim,'clips')}
    for other in owner.get_components_by_class(u.ActorComponent):
        if other.get_class().get_name()=='FPSFurnitureRestComponent':
            state['rest_state']=prop(other,'state')
    report['live'].append(state)
opt=u.AnimPoseEvaluationOptions(); opt.optional_skeletal_mesh=mesh; opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
names=['root','pelvis','head','hand_l','hand_r','foot_l','foot_r']
for role,expected in catalog.items():
    path=female['clips'].get(role)
    clip=u.load_asset(path) if path else None
    source=u.load_asset(body['clips'][role])
    if not clip:
        report['clips'][role]={'missing':path}; continue
    length=clip.get_play_length(); samples=[]
    for fraction in (0,.25,.5,.75,1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*fraction,opt)
        sample={}
        for name in names:
            t=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)
            sample[name]=[t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]
        samples.append(sample)
    report['clips'][role]={'asset':path,'duration':length,'source_duration':source.get_play_length(),
                          'clock_duration':expected['duration'],'correct_skeleton':clip.get_editor_property('skeleton')==mesh.skeleton,
                          'samples':samples}
(W/'initial_readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(P/'SourceAssets/KaitlinPlayer20261023/inspect_furniture_status.json').write_text(json.dumps({'remaining':0,'complete':True}),encoding='utf-8')
print('FEMALE_FURNITURE_READ',len(report['clips']),'clips',len(report['live']),'live bodies')
