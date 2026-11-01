import unreal as u,json,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
names=list(source['rest'])
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
data=dict(profiles={},clips={},names=names,parents=source['parents'],dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
          pie=bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()))
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
    p=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name)
    if any(c.get_editor_property('retained') for c in p.get_editor_property('clips')):raise RuntimeError('Retained clip requires separate editing')
    data['profiles'][family]=packed(p,family)
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
def tr(t):
    p=t.translation;q=t.rotation;s=t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for role in ('idle','reload','reload_mag10','reload_empty','reload_empty_mag10'):
    folder='Hold20261027' if role=='idle' else 'MotionMagazine20261027'
    path='/Game/Weapons/M24/'+folder+'/Animations/A_M24_'+role.removesuffix('_mag10')
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator;count=dm.get_number_of_keys()
    data['clips'][role]=dict(path=a.get_path_name(),fps=fps,keys=count,
        poses={str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(count)})
(O/'before.json').write_text(json.dumps(data),encoding='utf-8')
print('M24_EMPTY_RELOAD_SOURCE_READ',json.dumps({'pie':data['pie'],'clips':list(data['clips'])}),flush=True)
