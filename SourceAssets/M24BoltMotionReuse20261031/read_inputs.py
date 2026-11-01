import unreal as u,json,gzip,ast
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text());names=list(source['rest'])
paths={
 'base':'/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip',
 'mag10':'/Game/Weapons/M24/MotionPolish20261027/DA_M24_Mag10',
 'skeleton_base':'/Game/Weapons/M24/ReceiverGripRebuild20261031/Profiles/DA_M24_skeleton_base',
 'skeleton_mag10':'/Game/Weapons/M24/ReceiverGripRebuild20261031/Profiles/DA_M24_skeleton_mag10'}
D={'names':names,'parents':source['parents'],'rest':source['rest'],'profiles':{},'paths':paths,'clips':{}}
for family,path in paths.items():
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing active profile '+path)
 if any(c.get_editor_property('retained') for c in a.get_editor_property('clips')):raise RuntimeError('Retained clip requires authoring input '+path)
 D['profiles'][family]=packed(a,family)
targets={c['base'] for p in D['profiles'].values() for c in p['clips'] if c['base'].split('.')[-1] in ('A_M24_idle','A_M24_fire','A_M24_equip','A_M24_reload_empty')}
host=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
def tr(t):
 p,q,s=t.translation,t.rotation,t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for path in sorted(targets):
 a=u.load_asset(path);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator
 D['clips'][path]={'path':path,'fps':fps,'keys':dm.get_number_of_keys(),'poses':{str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,host)] for i in range(dm.get_number_of_keys())}}
with gzip.open(O/'before.json.gz','wt') as f:json.dump(D,f)
print('M24_BOLT_INPUTS',len(D['profiles']),len(D['clips']),flush=True)
