"""Read current M16 optic and handle geometry for authoring; no world changes."""
import unreal as u,json,array,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];I=O/'Input';I.mkdir(exist_ok=True)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;M=u.GeometryScript_Materials
R={'assets':{},'complete':False};paths={k:'/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_'+k for k in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring')}
paths['eoth_holographic']='/Game/Weapons/CommonHK41620260930/Meshes/SM_M16_eoth_holographic'
paths['thermal_scope']='/Game/Weapons/ThermalScope20261006/Runtime/SM_Thermal_M16'
paths['thermal_selector']='/Game/Weapons/ThermalScope20261006/Runtime/SM_ThermalSelector_M16'
def sha(path):return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 sockets={str(s.socket_name):{'location':[s.relative_location.x,s.relative_location.y,s.relative_location.z],'rotation':[s.relative_rotation.pitch,s.relative_rotation.yaw,s.relative_rotation.roll],'scale':[s.relative_scale.x,s.relative_scale.y,s.relative_scale.z]} for s in u.ObjectIterator(u.StaticMeshSocket) if s.get_outer()==mesh and mesh.find_socket(s.socket_name)==s}
 b=sms.get_lod_build_settings(mesh,0)
 row={'path':path,'sha256':sha(path),'sockets':sockets,'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials], 'build_settings':{k:b.get_editor_property(k) for k in ('recompute_normals','recompute_tangents','use_full_precision_u_vs','use_high_precision_tangent_basis')}}
 task=u.AssetExportTask();task.object=mesh;task.filename=str(I/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
 row['fbx']=task.filename;R['assets'][key]=row
path='/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny';host=u.load_asset(path)
dm,status=G.copy_mesh_from_skeletal_mesh(host,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Host extraction')
_,p,_=Q.get_all_vertex_positions(dm,False);p=L.convert_vector_list_to_array(p);_,t,_=Q.get_all_triangle_indices(dm,False);t=L.convert_triangle_list_to_array(t)
mid=next(v for v in M.get_all_triangle_material_i_ds(dm) if isinstance(v,u.GeometryScriptIndexList));mid=L.convert_index_list_to_array(mid)
sm=u.SkeletonModifier();sm.set_skeletal_mesh(host);bind=sm.get_bone_transform('WPN_root',True)
hp=[bind.inverse_transform_location(v)*100 for v in p]
slots=[str(s.material_slot_name) for s in host.materials]
ids=[i for i,tri in enumerate(t) if not any(w in slots[mid[i]].lower() for w in ('skin','manny','sleeve','glove','barepalm','barearm'))]
used=sorted({v for i in ids for v in [t[i].x,t[i].y,t[i].z]});lookup={v:i for i,v in enumerate(used)}
info={'path':path,'sha256':sha(path),'vertices':len(used),'triangles':len(ids),'slots':slots,'frame':'WPN_root cm with .01 attachment compensation'}
with (I/'host.bin').open('wb') as f:
 f.write((json.dumps(info)+'\n').encode());array.array('f',(v for i in used for v in [hp[i].x,hp[i].y,hp[i].z])).tofile(f);array.array('i',(lookup[v] for i in ids for v in [t[i].x,t[i].y,t[i].z])).tofile(f);array.array('i',(mid[i] for i in ids)).tofile(f)
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
R['host']=info;R['pie']=False if headless else u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor();R['dirty']=[] if headless else [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
R['complete']=True;(O/'capture.json').write_text(json.dumps(R,indent=2));print('M16_OPTIC_INPUTS',len(paths),info['triangles'],R['pie'],flush=True)
