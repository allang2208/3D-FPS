import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KSurface20261018');m=u.load_asset('/Game/Weapons/Saiga12K/SurfaceRebuild20261018/SK_Saiga12K_Manny');G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;LS=u.GeometryScript_List
d,_=G.copy_mesh_from_skeletal_mesh(m,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,bs=B.get_all_bones_info(d);names={b.index:str(b.name) for b in bs};_,ts,_=Q.get_all_triangle_indices(d,False);ts=list(LS.convert_triangle_list_to_array(ts));r={'bones':names,'weights':{},'bounds':{}}
for i,t in enumerate(ts):
 mi,ok=u.GeometryScript_Materials.get_triangle_material_id(d,i);name=str(m.materials[mi].material_slot_name)
 if not name.startswith('Saiga12K_') or name in r['weights']:continue
 _,ws,valid=B.get_vertex_bone_weights(d,t.x);r['weights'][name]=[{'index':w.bone_index,'name':names.get(w.bone_index),'weight':w.weight} for w in ws]
for k in ('Refined20261017','SurfaceRebuild20261018'):
 a=u.load_asset('/Game/Weapons/Saiga12K/'+k+'/Attachments/SM_Saiga12K_vertical');b=a.get_bounds();r['bounds'][k]={'origin':[b.origin.x,b.origin.y,b.origin.z],'extent':[b.box_extent.x,b.box_extent.y,b.box_extent.z],'radius':b.sphere_radius}
(O/'Reports/saved-diagnostic.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
