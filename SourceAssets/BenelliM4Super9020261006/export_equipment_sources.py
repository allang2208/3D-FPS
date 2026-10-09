import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];X=O/'EquipmentSources';X.mkdir(exist_ok=True)
C=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries

def xyz(v):return [v.x,v.y,v.z]
def read(path,key,geometry=False):
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing binding '+path)
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
 _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
 data={'source':path,'skeleton':mesh.skeleton.get_path_name(),'bones':{str(b.name):{'index':b.index,'parent':b.parent_index,'position':xyz(b.world_transform.translation),'axes':[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]} for b in bones}}
 if geometry:
  _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps)
  _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
  data.update(positions=[xyz(v) for v in ps],triangles=[],uv=[],normals=[],triangle_materials=[],weights=[],materials=[v.material_interface.get_path_name() for v in mesh.materials],material_slots=[str(v.material_slot_name) for v in mesh.materials])
  for i,t in enumerate(ts):
   a,b,c,ok=Q.get_triangle_u_vs(dm,0,i);_,n0,n1,n2,ok=Q.get_triangle_normals(dm,i)
   data['triangles'].append(xyz(t));data['uv'].append([[v.x,v.y] for v in (a,b,c)]);data['normals'].append([xyz(v) for v in (n0,n1,n2)])
   material,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i);data['triangle_materials'].append(material)
  for i in range(len(ps)):
   _,ws,ok=B.get_vertex_bone_weights(dm,i);data['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
 (X/(key+'.json')).write_text(json.dumps(data,separators=(',',':')))
 print('EXPORTED_EQUIPMENT_SOURCE',key,flush=True)
 return data
seen=set()
for path,profile in C['profiles'].items():
 key=profile['rig_profile']
 if key in seen:continue
 seen.add(key)
 if not (X/('rig_'+key+'.json')).exists():read(path,'rig_'+key)
for item,entry in C['items'].items():
 if entry.get('slot') in (3,7) and entry.get('rig_meshes',{}).get('M4') and not (X/(item+'.json')).exists():read(entry['rig_meshes']['M4'],item,True)
receipt=json.loads((O/'import_receipt.json').read_text())
for kind,path in receipt['outfit'].items():
 if not (X/('source_'+kind+'.json')).exists():read(path,'source_'+kind,True)
