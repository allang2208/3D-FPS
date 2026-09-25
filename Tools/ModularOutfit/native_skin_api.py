"""Read the installed geometry authoring API used by native-bound bare hands."""
from pathlib import Path
import unreal as u
names={
 'GeometryScript_AssetUtils':['copy_mesh_from_skeletal_mesh','copy_mesh_to_skeletal_mesh'],
 'GeometryScript_BoneWeights':['get_all_bones_info','get_vertex_bone_weights','copy_bones_from_mesh','set_vertex_bone_weights','mesh_create_bone_weights'],
 'GeometryScript_MeshQueries':['get_all_vertex_positions','get_all_triangle_indices','get_triangle_u_vs'],
 'GeometryScript_ListUtilityFunctions':['convert_vector_list_to_array','convert_triangle_list_to_array','convert_array_to_index_list'],
 'GeometryScript_MeshEdits':['append_buffers_to_mesh'],
 'GeometryScript_Materials':['get_triangle_material_id','set_triangle_material_id'],
}
lines=[]
for cls,methods in names.items():
    c=getattr(u,cls,None)
    for name in methods:
        f=getattr(c,name,None)
        lines.append(cls+'.'+name+'\n'+str(getattr(f,'__doc__','MISSING')))
        if not f and c:lines.append(str([n for n in dir(c) if any(s in n for s in ('triangle','vector','array','uv'))]))
Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/native-skin-api.txt').write_text('\n'.join(lines))
print('Native skin authoring API written')
