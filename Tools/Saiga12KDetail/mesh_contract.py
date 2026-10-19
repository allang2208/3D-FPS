import unreal as u,json,hashlib
def arm_contract(mesh):
 G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;BW=u.GeometryScript_BoneWeights
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+mesh.get_path_name())
 _,p,_=Q.get_all_vertex_positions(dm,False);p=list(LS.convert_vector_list_to_array(p));_,t,_=Q.get_all_triangle_indices(dm,False);t=list(LS.convert_triangle_list_to_array(t));_,bones=BW.get_all_bones_info(dm)
 nc=Q.get_num_uv_sets(dm);slots=list(mesh.materials);rows=[];weights={}
 def vec(v):return [round(float(getattr(v,c)),6) for c in 'xyz']
 for ti,tr in enumerate(t):
  mid,ok=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
  if not ok or str(slots[mid].material_slot_name).startswith('Saiga12K_'):continue
  vids=[tr.x,tr.y,tr.z];ns=[v for v in Q.get_triangle_normals(dm,ti) if isinstance(v,u.Vector)][:3];uvs=[Q.get_triangle_u_vs(dm,ch,ti)[:3] for ch in range(nc)]
  corners=[]
  for k,vi in enumerate(vids):
   if vi not in weights:
    _,ws,valid=BW.get_vertex_bone_weights(dm,vi);weights[vi]=sorted([[w.bone_index,round(w.weight,6)] for w in ws if w.weight>0])
   corners.append([vec(p[vi]),vec(ns[k]),[[round(v[k].x,6),round(v[k].y,6)] for v in uvs],weights[vi]])
  rows.append(json.dumps([str(slots[mid].material_slot_name),corners],separators=(',',':')))
 digest=hashlib.sha256('\n'.join(sorted(rows)).encode()).hexdigest()
 return {'triangle_count':len(rows),'uv_channels':nc,'positions_normals_all_uv_weights_sha256':digest,'skeleton':mesh.skeleton.get_path_name(),'morphs':sorted([m.get_name() for m in mesh.get_editor_property('morph_targets')]),'bones':[{'name':str(b.name),'parent':b.parent_index,'position':vec(b.world_transform.translation),'rotation':[round(getattr(b.world_transform.rotation,c),6) for c in 'xyzw'],'scale':vec(b.world_transform.scale3d)} for b in bones]}
