import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;source=json.loads((O/'source_before.json').read_text());names=list(source['rest'])
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
def tr(t):
 p=t.translation;q=t.rotation;s=t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
R={'clips':{},'profiles':{}}
for role,desc in source['clips'].items():
 if role.endswith('_mag10'):continue
 folder='Hold20261027' if role in ('idle','aim') else 'MotionMagazine20261027'
 a=u.load_asset('/Game/Weapons/M24/'+folder+'/Animations/A_M24_'+role)
 dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();count=dm.get_number_of_keys()
 fps=rate.numerator/rate.denominator
 frames=sorted(set([0, min(count-1,round(count*.3)),min(count-1,round(count*.5)),count-1]))
 R['clips'][role]={'path':a.get_path_name(),'fps':fps,'keys':count,'poses':{str(f):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,f/fps,False,mesh)] for f in frames}}
for family,name in [('base','DA_M24_SupportGrip'),('mag10','DA_M24_Mag10')]:
 p=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name)
 R['profiles'][family]=[{'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]} for c in p.get_editor_property('clips')]
(O/'ue_before.json').write_text(json.dumps(R),encoding='utf-8');print('M24_RAW_SOURCE_SNAPSHOT_SAVED',len(R['clips']),flush=True)
