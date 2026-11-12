"""Save our first translated mount after the protected Sockets read failed."""
from pathlib import Path
import unreal as u,json,hashlib
r=Path(__file__).resolve().parent;project=r.parents[2]
path='/Game/Weapons/M249/CommonParts20261108/Meshes/SM_M249_vertical'
extra=json.loads((r/'extra_inputs.json').read_text());disk=project/'Content'/(path.removeprefix('/Game/')+'.uasset')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE retained')
a=u.load_asset(path);dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read pending mount')
_,positions,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
points=[v.to_tuple() for v in u.GeometryScript_List.convert_vector_list_to_array(positions)]
bounds=[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
expected=json.loads((r.parent/'Repair13/parts_recipe.json').read_text())['parts']['vertical']['bounds_root_cm']
for row in expected:row[1]+=3.
if max(abs(bounds[j][i]-expected[j][i]) for j in range(2) for i in range(3))>.001:raise RuntimeError('Pending mount differs from our exact translation; preserve')
if path in dirty and not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Pending mount save failed')
receipt=dict(saved={path:hashlib.sha256(disk.read_bytes()).hexdigest()},mounts={path:dict(shift_root_cm=[0,3,0],vertices=len(points),recovered_own_pending_translation=True)},unchanged_base_animations=True,complete=False)
(r/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('WRIST33_OWN_PENDING_MOUNT_SAVED',flush=True)
