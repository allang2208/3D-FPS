"""Extract the current factory magazine and its real native bone frame."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KMagazine20261017')
PATH='/Game/Weapons/Saiga12K/Refined20261017/SK_Saiga12K_Manny'
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;ML=u.MathLibrary;L=u.MaterialEditingLibrary
mesh=u.load_asset(PATH)
dm,st=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);byname={str(b.name):b for b in bones};names=[str(b.name) for b in bones]
local=u.AnimationLibrary.get_bone_poses_for_frame(u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle'),names,0,False,mesh);pose={}
for b,t in zip(bones,local):pose[str(b.name)]=t if b.parent_index<0 else t.multiply(pose[names[b.parent_index]])
ref=byname['WPN_SOCKET_Magazine'].world_transform;mag=pose['WPN_SOCKET_Magazine'];root=pose['WPN_root']
def xyz(p):return [p.x,p.y,p.z]
def cm(p):return [p.x*100,p.y*100,p.z*100]
def to_root(p):return ML.inverse_transform_location(root,ML.transform_location(mag,ML.inverse_transform_location(ref,p)))
def to_socket(p):return ML.inverse_transform_location(mag,ML.transform_location(root,p))
index=next(i for i,s in enumerate(mesh.materials) if str(s.material_slot_name)=='Saiga12K_Magazine')
material=mesh.materials[index].material_interface
_,vp,_=Q.get_all_vertex_positions(dm,False);vp=list(LS.convert_vector_list_to_array(vp));_,tp,_=Q.get_all_triangle_indices(dm,False);tp=list(LS.convert_triangle_list_to_array(tp))
selected=[i for i in range(len(tp)) if u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]==index]
ids=sorted({v for i in selected for v in (tp[i].x,tp[i].y,tp[i].z)});lookup={v:i for i,v in enumerate(ids)}
R={'source':PATH,'slot':'Saiga12K_Magazine','material':material.get_path_name(),'bone':'WPN_SOCKET_Magazine','positions':[cm(to_root(vp[i])) for i in ids],'triangles':[],'normals':[],'uv0':[],'uv1':[],
 'socket_frame_cm':{'origin':cm(to_socket(u.Vector())), 'axes':[cm(to_socket(u.Vector(*v))) for v in ((.01,0,0),(0,.01,0),(0,0,.01))]},
 'material_scalars':{str(n):L.get_material_instance_scalar_parameter_value(material,n) for n in L.get_scalar_parameter_names(material)},
 'material_vectors':{str(n):[getattr(L.get_material_instance_vector_parameter_value(material,n),c) for c in 'rgba'] for n in L.get_vector_parameter_names(material)}}
for i in selected:
 t=tp[i];R['triangles'].append([lookup[v] for v in (t.x,t.y,t.z)])
 ns=[n for n in Q.get_triangle_normals(dm,i) if isinstance(n,u.Vector)][:3]
 R['normals'].append([xyz(ML.inverse_transform_direction(root,ML.transform_direction(mag,ML.inverse_transform_direction(ref,n)))) for n in ns])
 for k in (0,1):R['uv'+str(k)].append([[v.x,v.y] for v in Q.get_triangle_u_vs(dm,k,i)[:3]])
(O/'Input/factory.json').write_text(json.dumps(R,separators=(',',':')),encoding='utf-8')
print('SAIGA_FACTORY_MAGAZINE_EXTRACTED',len(ids),len(selected))
