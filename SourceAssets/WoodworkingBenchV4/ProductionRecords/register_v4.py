from pathlib import Path
import importlib.util,unreal as u,json,math
P=Path('D:/FPS3D/FPSGAME');W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/woodworking_v4_import_20261008')
spec=importlib.util.spec_from_file_location('woodworking_v4_registration',str(P/'Tools/Building/register_woodworking_bench.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
bridge='-run=pythonscript' not in u.SystemLibrary.get_command_line().casefold()
module.main(bridge=bridge)
palette=u.load_asset(module.PALETTE);matches=[e for e in palette.components if str(e.id)=='woodworking_bench'];assert len(matches)==1
e=matches[0];assert str(e.material)=='None';mesh=u.load_asset('/Game/Building/WoodworkingBenchV4/SM_WoodworkingBench');assert e.mesh==mesh
b=mesh.get_bounds();cell=[e.footprint.x,e.footprint.y,e.footprint.z];offset=e.pivot_offset_cm
# Static placement contract: every quarter-turn keeps the same bottom Z at a zero-height anchor.
ground_z=cell[2]*10-b.origin.z+offset.z+(b.origin.z-b.box_extent.z);assert abs(ground_z)<.001
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
readback=[]
for name in ['SM_WoodworkingBench','SM_WoodworkingBenchBody','SM_WoodworkingSawBlade']:
    m=u.load_asset('/Game/Building/WoodworkingBenchV4/'+name);assert m
    lods=list(sub.get_lod_screen_sizes(m));assert all(abs(a-b)<1e-5 for a,b in zip(lods,[1,.45,.18])),(name,lods)
    socket=m.find_socket('WoodworkingSawPivot')
    if name!='SM_WoodworkingSawBlade':assert socket and abs(socket.get_editor_property('relative_location').x-86.5)<.01
    readback.append({'mesh':m.get_path_name(),'triangles':[m.get_num_triangles(i) for i in range(3)],'lod_screen_sizes':lods,'convex_collision_count':sub.get_convex_collision_count(m),'socket_cm':str(socket.get_editor_property('relative_location')) if socket else None})
r={'mesh':mesh.get_path_name(),'unique_woodworking_id':True,'category':'other','footprint_cells':cell,'ground_error_cm':ground_z,'meshes':readback,'maps_saved':False,'gameplay_tested':False}
(W/'palette_readback.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print('V4_REGISTERED_READBACK',json.dumps(r))
