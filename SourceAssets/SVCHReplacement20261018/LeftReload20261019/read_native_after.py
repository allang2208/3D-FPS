"""Read current assets for native-V9 magazine contact authoring; never save assets."""
import json,gzip,hashlib
from pathlib import Path
import unreal as u

O=Path(__file__).parent;I=O/'InputsAfter';I.mkdir(exist_ok=True);P=Path(u.Paths.project_dir()).resolve()
ASSETS={'arms':'/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7'}
manifest={}
def xf(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def digest(path):
 return hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def pick(result,cls):return next(v for v in result if isinstance(v,cls))
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
for key,path in ASSETS.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);names=list(mod.get_all_bone_names())
 data={'path':path,'sha256':digest(path),'names':[str(n) for n in names],
       'parents':[str(mod.get_parent_name(n)) for n in names],
       'reference':[xf(mod.get_bone_transform(n,True)) for n in names],
       'materials':[str(s.material_slot_name) for s in mesh.get_editor_property('materials')], 'morph_names':[m.get_name() for m in mesh.get_editor_property('morph_targets')]}
 del mod
 dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
 result=G.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
 if u.GeometryScriptOutcomePins.SUCCESS not in result:raise RuntimeError('Cannot read '+path)
 positions=L.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,False),u.GeometryScriptVectorList))
 triangles=L.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,False),u.GeometryScriptTriangleList))
 slots=L.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
 data.update(positions=[[v.x,v.y,v.z] for v in positions],triangles=[[t.x,t.y,t.z] for t in triangles],material_ids=list(slots))
 _,bones=B.get_all_bones_info(dm);data['weight_bones']=[str(b.name) for b in sorted(bones,key=lambda b:b.index)]
 data['weights']=[]
 for v in range(len(positions)):
  _,ws,valid=B.get_vertex_bone_weights(dm,v)
  data['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
 with gzip.open(I/(key+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))
 manifest[key]={'path':path,'sha256':data['sha256'],'vertices':len(positions),'triangles':len(triangles),'materials':data['materials']}
 print('SVCH_RELOAD_INPUT',key,len(positions),len(triangles),data['materials'],flush=True)


(I/'manifest.json').write_text(json.dumps(manifest,indent=2))
