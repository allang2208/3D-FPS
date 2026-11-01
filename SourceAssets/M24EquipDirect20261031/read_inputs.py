"""Read production equip/idle motion and current grip layers for this edit."""
import unreal as u,json,ast
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
names=list(source['rest']);D={'names':names,'parents':source['parents'],'profiles':{},'clips':{}}
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
    asset=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name)
    if any(c.get_editor_property('retained') for c in asset.get_editor_property('clips')):raise RuntimeError('Retained animation needs its own source')
    D['profiles'][family]=packed(asset,family)
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for role,folder in [('idle','Hold20261027'),('equip','MotionMagazine20261027')]:
    a=u.load_asset('/Game/Weapons/M24/'+folder+'/Animations/A_M24_'+role)
    dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator
    D['clips'][role]={'path':a.get_path_name(),'fps':fps,'keys':dm.get_number_of_keys(),'poses':{str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(dm.get_number_of_keys())}}
(O/'before.json').write_text(json.dumps(D),encoding='utf-8')
print('M24_EQUIP_INPUTS_READ')
