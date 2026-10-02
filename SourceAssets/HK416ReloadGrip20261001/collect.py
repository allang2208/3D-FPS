"""Read current HK416 source poses and export geometry for grip authoring only."""
import gzip, hashlib, json, time
from pathlib import Path
import unreal as u

O=Path('D:/FPS3D/FPSGAME/SourceAssets/HK416ReloadGrip20261001')
P=O.parents[1]; I=O/'Inputs'; I.mkdir(parents=True,exist_ok=True)
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=P.resolve():
 raise RuntimeError('Wrong project; no source read or exported')
H='/Game/Weapons/HK416/Reworked20260930'
FAMILIES=globals().get('families',('base','vertical','canted','prism','angled'))
index_path=O/'inputs.json'
index=json.loads(index_path.read_text()) if index_path.exists() else {'clips':{}}
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
mesh=u.load_asset(H+'/SK_HK416_Manny')
if 'bind' not in index:
 dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 _,rows=u.GeometryScript_BoneWeights.get_all_bones_info(dm);rows=sorted(rows,key=lambda x:x.index)
 names=[str(b.name) for b in rows];parents=[b.parent_index for b in rows]
 bind={'names':names,'parents':parents,'rest':[pack(b.world_transform) for b in rows]}
 (I/'bind.json').write_text(json.dumps(bind))
 # Include immediate ancestors so unchanged arm translations can be reconstructed exactly.
 chosen={n for n in names if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))}
 chosen.update(('WPN_root','WPN_SOCKET_Magazine'))
 for n in list(chosen):
  j=parents[names.index(n)]
  if j>=0:chosen.add(names[j])
 index.update({'mesh':mesh.get_path_name().split('.')[0],'mesh_sha256':hashlib.sha256(disk(mesh.get_path_name()).read_bytes()).hexdigest(),'bind':str(I/'bind.json'),'bones':[n for n in names if n in chosen]})
 index_path.write_text(json.dumps(index,indent=1))
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.RAW
for family in FAMILIES:
 for kind in ('reload','reload_empty','drum_reload','drum_reload_empty'):
  key=H+'/Animations/'+family+'/A_HK416_'+family+'_'+kind
  digest=hashlib.sha256(disk(key).read_bytes()).hexdigest()
  if key in index['clips'] and index['clips'][key]['sha256']==digest:continue
  a=u.load_asset(key);n=u.AnimationLibrary.get_num_frames(a)
  times=[u.AnimationLibrary.get_time_at_frame(a,f) for f in range(n+1)]
  world=[];local=[]
  for t in times:
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opts)
   world.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in index['bones']])
   local.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.LOCAL)) for b in index['bones']])
  file=I/(family+'__'+kind+'.json.gz')
  with gzip.open(file,'wt',encoding='utf8') as f:json.dump({'asset':key,'bones':index['bones'],'sha256':digest,'times':times,'world':world,'local':local,'seconds':a.get_play_length()},f,separators=(',',':'))
  index['clips'][key]={'file':str(file),'sha256':digest,'keys':len(times),'seconds':a.get_play_length(),'family':family,'kind':kind}
  index_path.write_text(json.dumps(index,indent=1));print('HK416_GRIP_SOURCE',family,kind,len(times),flush=True)
if globals().get('export_geometry',False):
 assets={'HK416':H+'/SK_HK416_Manny','factory':H+'/Attachments/SM_HK416_factory_magazine','extended':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_ext_mag','drum':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_large_drum'}
 for name,path in assets.items():
  file=I/(name+'.fbx')
  if file.exists():continue
  task=u.AssetExportTask();task.object=u.load_asset(path);task.filename=str(file);task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption()
  if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Geometry export failed '+path)
  print('HK416_GRIP_GEOMETRY',name,flush=True)
 print('HK416_GRIP_SOURCE_READY',len(index['clips']),flush=True)
