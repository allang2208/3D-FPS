"""Capture current M24 idle/strike profiles and assembly inputs for authoring."""
import unreal as u,json,gzip,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;X=O/'Inputs';X.mkdir(exist_ok=True)
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'profile serializer','exec'))
prior=json.loads((O.parent/'M24ArmContact20261104/publish_receipt.json').read_text())
paths={v['family']:v['asset'].split('.')[0] for v in prior['saved']}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def digest(path):return hashlib.sha256((Path(u.Paths.project_content_dir())/(path[6:].split('.')[0]+'.uasset')).read_bytes()).hexdigest()
profiles={};assets={}
for family,path in paths.items():
    if path in dirty:raise RuntimeError('Unsaved input preserved '+path)
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing input '+path)
    profiles[family]=packed(a,str(a.get_editor_property('family')))
    profiles[family]['clips']=[c for c in profiles[family]['clips'] if c['base'].split('.')[-1] in ('A_M24_idle','A_M24_quick_melee')]
    assets[family]={'path':path,'sha256':digest(path)}
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
names=list(source['rest']);host_path='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9';host=u.load_asset(host_path)
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
clips={};hashes={host_path:digest(host_path)}
for path in sorted({c['base'] for p in profiles.values() for c in p['clips'] if c['base'].split('.')[-1] in ('A_M24_idle','A_M24_quick_melee')}):
    if path.split('.')[0] in dirty:raise RuntimeError('Unsaved animation preserved '+path)
    a=u.load_asset(path);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator
    clips[path]={'path':path,'fps':fps,'keys':dm.get_number_of_keys(),'poses':{str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,host)] for i in range(dm.get_number_of_keys())}}
    hashes[path]=digest(path)
with gzip.open(O/'input_motion.json.gz','wt',compresslevel=1) as f:json.dump({'names':names,'parents':source['parents'],'profiles':profiles,'clips':clips},f,separators=(',',':'))
assembly={
 'stock':'/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Advanced',
 'front':'/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_AdvancedFront_ForIndependentGrip',
 'stock_native':'/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Native',
 'carbon':'/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Advanced',
 'carbon_native':'/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Native'}
for variant in ('Default','balanced','phantom','stable'):assembly['grip_'+variant]='/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_PistolGrip_'+variant
exports={}
for key,path in assembly.items():
    if path in dirty:raise RuntimeError('Unsaved assembly preserved '+path)
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing assembly '+path)
    file=X/(key+'.fbx');task=u.AssetExportTask();task.object=mesh;task.filename=str(file);task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Assembly export failed '+path)
    exports[key]={'path':path,'fbx':str(file),'sha256':digest(path)}
(O/'input_assets.json').write_text(json.dumps(assets,indent=2))
(O/'input_dependency_hashes.json').write_text(json.dumps(hashes,indent=2))
(O/'assembly.json').write_text(json.dumps(exports,indent=2))
print('M24_MELEE_INPUTS_SAVED',len(profiles),len(clips),flush=True)
