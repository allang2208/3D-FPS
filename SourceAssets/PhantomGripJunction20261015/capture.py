"""Read current runtime grips and nearby receivers in the actual attachment frame."""
import unreal as u,json,array,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];I=O/'Input';I.mkdir(parents=True,exist_ok=True)
old=json.loads((P/'SourceAssets/PhantomGripSurface20261015/capture.json').read_text());G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;M=u.GeometryScript_Materials
hosts={'M4':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative','QBZ191':'/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny','M16':'/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny','HK416':'/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny','A762':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny','PKM':'/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular','LMG201':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','Super90':'/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'}
R={'assets':{},'hosts':{},'complete':False,'gameplay_tested':False};lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
def read(mesh,skeletal=False):
 fn=G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh;dm,status=fn(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),lod)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(mesh.get_path_name())
 _,p,_=Q.get_all_vertex_positions(dm,False);p=L.convert_vector_list_to_array(p);_,t,_=Q.get_all_triangle_indices(dm,False);t=L.convert_triangle_list_to_array(t);mid=next(v for v in M.get_all_triangle_material_i_ds(dm) if isinstance(v,u.GeometryScriptIndexList));mid=L.convert_index_list_to_array(mid)
 return dm,p,t,mid
def sha(path):return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
for key,row in old['assets'].items():
 grip=u.load_asset(row['path']);dm,p,t,mids=read(grip);slots=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in grip.static_materials]
 lo=[min(getattr(v,a) for v in p) for a in ['x','y','z']];hi=[max(getattr(v,a) for v in p) for a in ['x','y','z']]
 target={'path':row['path'],'sha256':sha(row['path']),'slots':slots,'bounds_cm':[lo,hi]};R['assets'][key]=target
 task=u.AssetExportTask();task.object=grip;task.filename=str(I/(key+'_grip.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+key)
 target['fbx']=task.filename
 host=u.load_asset(hosts[key]);hdm,hp,ht,hm=read(host,True);sm=u.SkeletonModifier()
 if not sm.set_skeletal_mesh(host):raise RuntimeError('Cannot read skeleton '+key)
 bind=sm.get_bone_transform('WPN_root',True);frame='bind' if key in ['HK416','Super90'] else 'WPN_root with 0.01 scale compensation'
 def position(p):
  if key in ['HK416','Super90']:return [p.x,p.y,p.z]
  v=bind.inverse_transform_location(p);return [v.x*100,v.y*100,v.z*100]
 hp=[position(v) for v in hp];hslots=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in host.materials]
 factory={i for i,s in enumerate(hslots) if 'FactoryRearGrip' in s['name'] or 'Grip_Default' in s['name'] or s['name']=='M_M16_PistolGrip'}
 if not factory:raise RuntimeError('No factory section '+key)
 # Capture receiver neighbourhood and factory grip, excluding the authored arms.
 selected=[]
 for tid,tri in enumerate(ht):
  name=hslots[hm[tid]]['name'].lower();points=[hp[i] for i in [tri.x,tri.y,tri.z]]
  if any(w in name for w in ['skin','manny','sleeve','glove','barepalm','barearm']):continue
  nearby=all(max(p[a] for p in points)>lo[a]-[4,7,2][a] and min(p[a] for p in points)<hi[a]+[4,7,8][a] for a in range(3))
  if hm[tid] in factory or nearby:selected.append(tid)
 used=sorted({i for tid in selected for i in [ht[tid].x,ht[tid].y,ht[tid].z]});lookup={v:i for i,v in enumerate(used)}
 pos=array.array('f',(x for i in used for x in hp[i]));tri=array.array('i',(lookup[i] for tid in selected for i in [ht[tid].x,ht[tid].y,ht[tid].z]));mat=array.array('i',(hm[tid] for tid in selected));ns=array.array('f')
 for tid in selected:
  vectors=[v for v in Q.get_triangle_normals(hdm,tid) if isinstance(v,u.Vector)]
  for n in vectors:
   if key not in ['HK416','Super90']:n=bind.inverse_transform_direction(n)
   ns.extend([n.x,n.y,n.z])
 info={'path':hosts[key],'sha256':sha(hosts[key]),'vertices':len(used),'triangles':len(selected),'slots':hslots,'factory_slots':sorted(factory),'frame':frame,'root_translation':[bind.translation.x,bind.translation.y,bind.translation.z],'root_scale':[bind.scale3d.x,bind.scale3d.y,bind.scale3d.z]}
 with (I/(key+'_host.bin')).open('wb') as f:
  f.write((json.dumps(info)+'\n').encode());pos.tofile(f);tri.tofile(f);mat.tofile(f);ns.tofile(f)
 R['hosts'][key]=info;(O/'capture.json').write_text(json.dumps(R,indent=2));print('JUNCTION_CAPTURED',key,len(selected),sorted(factory),flush=True)
R['complete']=True;(O/'capture.json').write_text(json.dumps(R,indent=2));print('JUNCTION_CAPTURE_COMPLETE',flush=True)
