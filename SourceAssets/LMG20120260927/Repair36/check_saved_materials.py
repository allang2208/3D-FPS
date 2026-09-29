import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;a=u.load_asset('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10');G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;M=u.GeometryScript_Materials;L=u.GeometryScript_List;ME=u.MaterialEditingLibrary
dm,out=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,tl,_=Q.get_all_triangle_indices(dm,False);tris=L.convert_triangle_list_to_array(tl);counts={}
for i in range(len(tris)):
 mid,valid=M.get_triangle_material_id(dm,i)
 if valid:counts[mid]=counts.get(mid,0)+1
rows=[];bad=[]
for i,count in sorted(counts.items()):
 s=a.materials[i];m=s.material_interface;base=m.get_base_material() if m else None;ok=bool(base and base.get_editor_property('used_with_skeletal_mesh'))
 row={'slot':str(s.material_slot_name),'material':m.get_path_name() if m else None,'triangles':count,'skeletal_usage':ok};rows.append(row)
 if not ok or not m or 'WorldGrid' in m.get_path_name() or 'DefaultMaterial' in m.get_path_name():bad.append(row)
cloth=[r for r in rows if r['slot'].endswith('Box_Cloth')]
normal=u.load_asset('/Game/Weapons/LMG201/Repair36/Textures/T_LMG201_R36_Receiver_Normal');coat=u.load_asset('/Game/Weapons/LMG201/Repair36/Materials/MI_LMG201_R36_Coat');c=ME.get_material_instance_vector_parameter_value(coat,'FinishColor');actual={'color_linear':[c.r,c.g,c.b],'roughness':ME.get_material_instance_scalar_parameter_value(coat,'DryRoughness'),'metallic':ME.get_material_instance_scalar_parameter_value(coat,'Metallic')}
report={'active_slots':rows,'invalid_skeletal_materials':bad,'cloth_slots':cloth,'receiver_normal_green_flip':bool(normal.get_editor_property('flip_green_channel')),'coating':actual,'pie_running':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'game_tested':False}
(O/'saved_material_check.json').write_text(json.dumps(report,indent=2));print('R36_SAVED_MATERIALS',json.dumps({'active_slots':len(rows),'invalid_skeletal_materials':bad,'cloth_slots':cloth,'coating':actual,'receiver_normal_green_flip':report['receiver_normal_green_flip']}),flush=True)
if bad or len(cloth)!=2:raise RuntimeError('An active section still lacks a correct skeletal material')
