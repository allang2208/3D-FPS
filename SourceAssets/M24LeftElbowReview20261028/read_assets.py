"""Read only: saved V9 meshes and native data-model poses; no AnimPose cold-load evaluation."""
import unreal as u,json,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
data=json.loads((O/'ue_before.json').read_text())
names=list(json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['rest'])
tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'pack','exec'))
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
 data['profiles'][family]=packed(u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name),family)['clips']
paths={'m24':'/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9','baseline':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'}
receipt={'meshes':{},'clips':{},'runtime_game_tested':False}
for label,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 task=u.AssetExportTask();task.object=mesh;task.filename=str(O/(label+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.SkeletalMeshExporterFBX()
 opt=u.FbxExportOption();opt.set_editor_property('export_morph_targets',True);opt.set_editor_property('level_of_detail',False);task.options=opt
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+label)
 file=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
 receipt['meshes'][label]={'path':mesh.get_path_name(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'skeleton':mesh.skeleton.get_path_name(),'morphs':[m.get_name() for m in mesh.get_editor_property('morph_targets')],
 'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]}
mesh=u.load_asset(paths['m24'])
def tr(t):
 p=t.translation;q=t.rotation;s=t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for role,desc in data['clips'].items():
 a=u.load_asset(desc['path']);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator;count=dm.get_number_of_keys()
 rows={str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(count)}
 data['clips'][role]={'path':desc['path'],'fps':fps,'keys':count,'poses':rows,'evaluation':'Sequence data model by time'}
 receipt['clips'][role]={'keys':count,'fps':fps}
data['snapshot_origin']='Fresh saved UE data-model poses and active profiles, 2026-10-28'
(O/'ue_before.json').write_text(json.dumps(data));(O/'read_receipt.json').write_text(json.dumps(receipt,indent=2))
print('M24_ELBOW_READ_COMPLETE',json.dumps({k:len(v['morphs']) for k,v in receipt['meshes'].items()}),flush=True)
