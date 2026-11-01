"""Read production inputs for the new bipod action; no gameplay or preview."""
import unreal as u, json, ast, hashlib, shutil
from pathlib import Path
O=Path(__file__).resolve().parent
names=list(json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['rest'])
tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
data={'names':names,'profiles':{},'clips':{}}
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
    data['profiles'][family]=packed(u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name),family)['clips']
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
path='/Game/Weapons/M24/Hold20261027/Animations/A_M24_idle'
a=u.load_asset(path);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator
data['clips']['idle']={'path':a.get_path_name(),'fps':fps,'keys':dm.get_number_of_keys(),'poses':{
 str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(dm.get_number_of_keys())}}
(O/'ue_before.json').write_text(json.dumps(data))
targets=['A_M24_Bipod_base','A_M24_Bipod_mag10','DA_M24_Bipod']
before=O/'Before';before.mkdir(exist_ok=True)
manifest={}
for name in targets:
    path=O.parents[1]/'Content/Weapons/M24/Bipod20261029'/(name+'.uasset')
    manifest[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    shutil.copy2(path,before/path.name)
(O/'input_manifest.json').write_text(json.dumps(manifest,indent=2))
print('M24_BIPOD_INPUTS_SAVED',flush=True)
