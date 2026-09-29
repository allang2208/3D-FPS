import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LMG201Wrist20260929';c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
paths={'shirt':c['items']['ue_chainmail_shirt']['rig_meshes']['LMG201'],'native':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10.SK_LMG201_Cover10','skin':c['items']['ue_field_gloves']['skin_meshes']['LMG201']}
(R/'before.json').write_text(json.dumps(paths));Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
for name,path in paths.items():
 a=u.load_asset(path);dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
 _,bones=B.get_all_bones_info(dm);bn={b.index:str(b.name) for b in bones}
 _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps);_,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
 d=dict(source=path,positions=[[p.x,p.y,p.z] for p in ps],triangles=[],triangle_materials=[],weights=[],normals=[],uv=[],bones={str(b.name):dict(position=[b.world_transform.translation.x,b.world_transform.translation.y,b.world_transform.translation.z]) for b in bones})
 for i,t in enumerate(ts):
  slot,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
  if name=='native' and slot not in [0,1,2]:continue
  d['triangles'].append([t.x,t.y,t.z]);d['triangle_materials'].append(slot)
 for i in range(len(ps)):
  _,ws,valid=B.get_vertex_bone_weights(dm,i);d['weights'].append({bn[w.bone_index]:w.weight for w in ws if w.weight>0})
 (R/(name+'.json')).write_text(json.dumps(d,separators=(',',':')));print('WRIST_SOURCE_SAVED',name,len(ps),flush=True)
