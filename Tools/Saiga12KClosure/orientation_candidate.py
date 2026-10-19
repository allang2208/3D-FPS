import unreal as u,json,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018';D='/Game/Weapons/Saiga12K/Closure20261018';E=u.EditorAssetLibrary
sys.path.insert(0,str(P/'Tools/Saiga12KDetail'));from mesh_contract import arm_contract
old=u.load_asset('/Game/Weapons/Saiga12K/Detail20261018/SK_Saiga12K_Manny');before=arm_contract(old)
target=E.duplicate_asset(old.get_path_name(),D+'/SK_Saiga12K_OrientationCandidate')
if not target:raise RuntimeError('Candidate already exists or duplicate failed')
dm,st=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(target,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,ts,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False);ts=list(u.GeometryScript_List.convert_triangle_list_to_array(ts));slots=target.materials
ids=[i for i in range(len(ts)) if str(slots[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]].material_slot_name).startswith('Saiga12K_')]
_,selection=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,ids,u.GeometryScriptMeshSelectionType.TRIANGLES)
u.GeometryScript_Normals.flip_triangle_selection_normals(dm,selection,True,False)
sk=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=sk.get_lod_build_settings(target,0)
settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;settings.remove_degenerates=False;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
sk.set_lod_build_settings(target,0,settings)
_,st=u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dm,target,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
if st!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save winding candidate')
after=arm_contract(target)
if before!=after:raise RuntimeError('Arm contract changed')
E.save_loaded_asset(target,False)
(O/'Receipts/orientation-candidate.json').write_text(json.dumps({'asset':target.get_path_name(),'triangles_flipped':len(ids),'normals_flipped':False,'arm_contract_unchanged':True,'before':before,'build_settings':str(sk.get_lod_build_settings(target,0))},indent=2))
print('ORIENTATION_CANDIDATE_SAVED',target.get_path_name(),len(ids))
