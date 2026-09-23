import unreal as u
for cls,methods in [('GeometryScript_AssetUtils',['copy_mesh_from_static_mesh_v2']),('GeometryScript_MeshQueries',['get_all_vertex_positions','get_all_triangle_indices']),('GeometryScript_List',['convert_vector_list_to_array','convert_triangle_list_to_array'])]:
 c=getattr(u,cls,None)
 print(cls,c)
 if c:
  for m in methods:print(m,getattr(c,m).__doc__)
