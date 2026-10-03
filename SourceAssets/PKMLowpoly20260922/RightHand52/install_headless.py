"""Save PKM-local hand binding and empty reload fingers; retain all other tracks."""
from pathlib import Path
import unreal as u,json,hashlib,shutil,itertools
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/PKMLowpoly20260922/RightHand52');ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/ModularOutfit20260925';E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def disk(path):return ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def backup(file):
 dest=P/'Before'/file.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(file,dest)
def save(asset):
 asset.modify()
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Save failed '+asset.get_path_name())
dirty={x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};meshes=json.loads((P/'mesh_inputs.json').read_text());clips=[json.loads((P/'Authored'/f'{f}.json').read_text()) for f in ['base','vertical','canted','prism','angled']]
for d in meshes+clips:
 path=d['asset']
 if sha(disk(path))!=d.get('sha256',d.get('source_sha256')):raise RuntimeError('Concurrent edit '+path)
 if path.split('.')[0] in dirty:raise RuntimeError('Unsaved target '+path)
families=['BarePalmV7','BarePalmV7','HuntFieldGlovesV1','FittedFieldGlovesV1','FittedSleevesV1']
for family in ['BarePalmV7','HuntFieldGlovesV1','FittedFieldGlovesV1','FittedSleevesV1']:
 if sha(OUT/family/'Authored/PKM.json')!=sha(P/'Inputs'/f'{family}_source.json'):raise RuntimeError('Source changed '+family)
receipt=dict(meshes=[],animations=[],complete=False,runtime_tested=False)
def record():(P/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
for entry,family in zip(meshes,families):
 path=entry['asset'];asset=u.load_asset(path);source=json.loads((P/'Inputs'/f'{family}_source.json').read_text());target=json.loads((P/'Authored'/f'{family}.json').read_text());lookup={}
 for i,point in enumerate(source['positions']):lookup.setdefault(tuple(round(v*1000) for v in point),[]).append(i)
 dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read failed '+path)
 _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones};indices={n:i for i,n in names.items()};_,vs,_=Q.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(vs);_,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts);ids=sorted({v for t in ts for v in (t.x,t.y,t.z)});touched=0
 for vi in ids:
  _,ws,valid=B.get_vertex_bone_weights(dm,vi);old={names[w.bone_index]:w.weight for w in ws if w.weight>0}
  if sum(w for n,w in old.items() if n.endswith('_r'))<.99:continue
  point=[vs[vi].x,vs[vi].y,vs[vi].z];key=tuple(round(v*1000) for v in point);candidates=lookup.get(key,[])
  if not candidates:
   for off in itertools.product([-1,0,1],repeat=3):candidates+=lookup.get(tuple(key[j]+off[j] for j in range(3)),[])
  if not candidates:raise RuntimeError('Source vertex missing '+path+' '+str(vi))
  best=min(candidates,key=lambda j:sum((point[k]-source['positions'][j][k])**2 for k in range(3))*1e5+sum(abs(old.get(n,0)-source['weights'][j].get(n,0)) for n in set(old)|set(source['weights'][j])))
  if sum((point[k]-source['positions'][best][k])**2 for k in range(3))>4e-6:raise RuntimeError('Source geometry changed '+path)
  new=target['weights'][best]
  if sum(abs(new.get(n,0)-source['weights'][best].get(n,0)) for n in set(new)|set(source['weights'][best]))<1e-8:continue
  B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=indices[n],weight=w) for n,w in new.items()]);touched+=1
 backup(disk(path));slots=list(asset.materials);lods=S.get_lod_count(asset);opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[v.material_interface for v in slots],new_material_slot_names=[v.material_slot_name for v in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write failed '+path)
 for lod in range(lods):
  settings=S.get_lod_build_settings(asset,lod);settings.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,lod,settings)
 if lods>1 and not S.regenerate_lod(asset,lods,True,False):raise RuntimeError('LOD rebuild failed '+path)
 E.set_metadata_tag(asset,'PKMRightHandRevision','RightHand52');save(asset);receipt['meshes'].append(dict(asset=path,vertices_reweighted=touched,lods=lods,saved=True));record();print('PKM52_MESH_SAVED',path,touched,flush=True)
for d in clips:
 asset=u.load_asset(d['asset']);backup(disk(d['asset']));ctrl=asset.get_editor_property('controller')
 if ctrl is None:ctrl=u.AnimDataController();ctrl.set_model(asset.get_editor_property('data_model_interface'))
 ctrl.open_bracket('PKM right hand native hinge and pull-push finger pressure',False)
 try:
  for n,keys in d['tracks'].items():
   if not ctrl.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],[u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):raise RuntimeError('Track write failed '+n)
 finally:ctrl.close_bracket(False)
 E.set_metadata_tag(asset,'PKMRightHandRevision','RightHand52');save(asset);receipt['animations'].append(dict(asset=d['asset'],saved=True,tracks=list(d['tracks'])));record();print('PKM52_ANIMATION_SAVED',d['asset'],flush=True)
for family in ['BarePalmV7','HuntFieldGlovesV1','FittedFieldGlovesV1','FittedSleevesV1']:
 source=OUT/family/'Authored/PKM.json';backup(source);source.write_bytes((P/'Authored'/f'{family}.json').read_bytes())
 for relative in ['Saved/PKM.json','NativeDefaults/PKM.json']:
  file=OUT/family/relative
  if file.exists():
   backup(file);d=json.loads(file.read_text());d['authored_sha256']=sha(source);d['right_hand_revision']='RightHand52';d['runtime_tested']=False
   if family!='BarePalmV7':d['bare_authored_sha256']=sha(OUT/'BarePalmV7/Authored/PKM.json')
   file.write_text(json.dumps(d,indent=2))
receipt['complete']=True;record();print('PKM52_COMPLETE')

