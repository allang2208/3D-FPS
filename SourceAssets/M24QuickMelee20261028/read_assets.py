"""Read current M24 idle/quick-melee, native binding and live profile inputs."""
import unreal as u, json, ast
from pathlib import Path
O=Path(__file__).resolve().parent
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
names=list(source['rest'])
tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
data={'names':names,'profiles':{},'clips':{}}
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
    profile=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name)
    data['profiles'][family]=packed(profile,family)['clips']
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for role,folder in [('idle','Hold20261027'),('quick_melee','MotionMagazine20261027')]:
    path='/Game/Weapons/M24/'+folder+'/Animations/A_M24_'+role
    a=u.load_asset(path);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate()
    fps=rate.numerator/rate.denominator;count=dm.get_number_of_keys()
    data['clips'][role]={'path':a.get_path_name(),'fps':fps,'keys':count,'poses':{
        str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(count)}}
component=u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(mesh)
data['stock_sockets']=[str(s) for s in component.get_all_socket_names() if 'Stock' in str(s)]
if 'WPN_StockContact' in data['stock_sockets']:
    data['stock_socket_transform']=tr(component.get_socket_transform('WPN_StockContact',u.RelativeTransformSpace.RTS_COMPONENT))
(O/'ue_before.json').write_text(json.dumps(data),encoding='utf-8')
print('M24_QUICK_INPUTS',json.dumps({'clips':{k:{n:v[n] for n in ('path','fps','keys')} for k,v in data['clips'].items()},'sockets':data['stock_sockets']}),flush=True)
