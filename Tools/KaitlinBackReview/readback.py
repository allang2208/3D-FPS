"""Read the saved LODs, material routes and upper-back surface without gameplay."""
import json,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/KaitlinBackReview20261117'
saved=json.loads((R/'saved.json').read_text());mesh=u.load_asset(saved['asset'])
ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
G,Q,L,M=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_Materials
slots=[str(m.material_slot_name) for m in mesh.materials]
report=dict(asset=mesh.get_path_name(),lods=[],cloth_assets=[c.get_path_name() for c in mesh.mesh_clothing_assets],
            player_materials_preserved=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name()) for m in mesh.materials]==saved['materials'])
expected=[169132,81046,32202]
for lod in range(ss.get_lod_count(mesh)):
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=lod))
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved LOD')
 _,points,_=Q.get_all_vertex_positions(dm,False);points=[[v.x,v.y,v.z] for v in L.convert_vector_list_to_array(points)]
 _,triangles,_=Q.get_all_triangle_indices(dm,False);triangles=[[v.x,v.y,v.z] for v in L.convert_triangle_list_to_array(triangles)]
 _,ids,_=M.get_all_triangle_material_i_ds(dm);ids=list(L.convert_index_list_to_array(ids))
 section_map=[ss.get_lod_material_slot(mesh,lod,i) for i in range(ss.get_num_sections(mesh,lod))]
 ids=[section_map[i] for i in ids]
 counts={name:ids.count(i) for i,name in enumerate(slots)}
 if counts['RobeHood'] or len(triangles)!=expected[lod]:raise RuntimeError('Hood remains or LOD differs')
 report['lods'].append(dict(lod=lod,triangles=len(triangles),section_material_map=section_map,material_triangles=counts))
 if lod==0:
  selected={i for i,(x,y,z) in enumerate(points) if -29<x<29 and y<1 and 112<z<150}
  faces=[i for i,t in enumerate(triangles) if all(v in selected for v in t) and slots[ids[i]]!='RobeSimulationProxy']
  used=sorted({v for i in faces for v in triangles[i]});remap={v:i for i,v in enumerate(used)}
  view=dict(path=mesh.get_path_name(),positions=[points[v] for v in used],triangles=[[remap[v] for v in triangles[i]] for i in faces],triangle_materials=[ids[i] for i in faces],materials=slots)
  (R/'BackViews/ue_blue_mage_robe_repaired.json').write_text(json.dumps(view,separators=(',',':')))
 del dm,points,triangles;gc.collect()
(R/'readback.json').write_text(json.dumps(report,indent=2))
print('KAITLIN_BACK_READBACK',[(r['lod'],r['triangles'],r['material_triangles']['RobeHood']) for r in report['lods']],flush=True)
