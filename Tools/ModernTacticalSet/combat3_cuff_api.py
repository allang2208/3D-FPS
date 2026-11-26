import unreal as u
print('CUFF_MATERIAL_API',[(name,getattr(u.GeometryScript_Materials,name).__doc__) for name in dir(u.GeometryScript_Materials) if 'all_triangle_material' in name],flush=True)
print('CUFF_INDEX_API',[(name,getattr(u.GeometryScript_List,name).__doc__) for name in dir(u.GeometryScript_List) if 'index_list_to_array' in name],flush=True)
