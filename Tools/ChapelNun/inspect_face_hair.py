import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/FaceHairFixR1')
L=u.MaterialEditingLibrary
d={}
for name in ['SK_Nun_Head','SK_Nun_CollarCross']:
 a=u.load_asset('/Game/Characters/ChapelNun20261115/Meshes/'+name)
 d[name]={'materials':[{'slot':str(m.material_slot_name),'material':m.material_interface.get_path_name() if m.material_interface else None} for m in a.materials], 'skeleton':a.skeleton.get_path_name()}
 for k in ['imported_bounds','positive_bounds_extension','negative_bounds_extension','post_process_anim_blueprint','min_lod','disable_morph_target','lod_settings','lod_info','lods']:
  try:d[name][k]=str(a.get_editor_property(k))
  except:pass
 # Capture actual authored head sections and bone binding, without changing assets.
 if name=='SK_Nun_Head':
  Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;LL=u.GeometryScript_List
  dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
  _,ps,_=Q.get_all_vertex_positions(dm,False);_,ts,_=Q.get_all_triangle_indices(dm,False);_,bs=B.get_all_bones_info(dm)
  ps=LL.convert_vector_list_to_array(ps);ts=LL.convert_triangle_list_to_array(ts)
  counts={}
  for i in range(len(ts)):
   mid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0];counts[mid]=counts.get(mid,0)+1
  d[name]['geometry']={'vertices':len(ps),'triangles':len(ts),'material_triangles':counts,'bounds_min':[min(getattr(v,c) for v in ps) for c in 'xyz'],'bounds_max':[max(getattr(v,c) for v in ps) for c in 'xyz'],'bones':len(bs)}
  d[name]['sample_weights']={}
  for i in range(0,len(ps),max(1,len(ps)//8)):
   _,ww,_=B.get_vertex_bone_weights(dm,i);d[name]['sample_weights'][i]=[(str(bs[w.bone_index].name),w.weight) for w in ww]
for name in ['M_NunSkin','MI_Nun_Hair']:
 a=u.load_asset('/Game/Characters/ChapelNun20261115/Materials/'+name);entry={'class':a.get_class().get_name()}
 for k in ['blend_mode','shading_model','two_sided','use_material_attributes','opacity_mask_clip_value','parent','scalar_parameter_values','vector_parameter_values','texture_parameter_values']:
  try:
   v=a.get_editor_property(k);entry[k]=[x.export_text() for x in v] if isinstance(v,u.Array) else str(v)
  except:pass
 if name=='MI_Nun_Hair':
  entry['scalars']={str(p):L.get_material_instance_scalar_parameter_value(a,p) for p in L.get_scalar_parameter_names(a)}
  entry['vectors']={str(p):str(L.get_material_instance_vector_parameter_value(a,p)) for p in L.get_vector_parameter_names(a)}
  entry['textures']={str(p):str(L.get_material_instance_texture_parameter_value(a,p)) for p in L.get_texture_parameter_names(a)}
 d[name]=entry
(R/'asset_before.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print('NUN_FACE_HAIR_INSPECTED',flush=True)
