import unreal as u,json
from pathlib import Path
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/woodworking_v4_import_20261008')
assert Path(u.Paths.project_dir()).resolve()==(W/'ImportHost').resolve()
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
r=json.loads((W/'ue_import_receipt.json').read_text())
for record in r['meshes']:
    mesh=u.load_asset(record['mesh']);assert mesh
    assert [mesh.get_num_triangles(i) for i in range(3)]==record['triangles']
    record['screen_sizes_before_reload']=list(sub.get_lod_screen_sizes(mesh))
    mesh.modify();assert sub.set_lod_screen_sizes(mesh,[1,.45,.18]);assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
    record['lod_screen_sizes']=list(sub.get_lod_screen_sizes(mesh))
    assert all(abs(a-b)<1e-5 for a,b in zip(record['lod_screen_sizes'],[1,.45,.18]))
    if 'Blade' not in mesh.get_name():
        socket=mesh.find_socket('WoodworkingSawPivot');assert socket
        record['socket_cm']=str(socket.get_editor_property('relative_location'))
    assert all(s.material_interface for s in mesh.static_materials)
r['lod_screen_sizes_set_after_final_mesh_build']=True
(W/'ue_import_receipt.json').write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
print('V4_LOD_FINAL',[(m['mesh'],m['lod_screen_sizes']) for m in r['meshes']])
