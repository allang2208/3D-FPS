"""Read saved waist geometry only; never convert a live Leader Pose component."""
import gc,hashlib,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from pants_compatibility_paths import *
inventory=read(R/'inventory.json');editor=u.get_editor_subsystem(u.LevelEditorSubsystem) if '-run=' not in u.SystemLibrary.get_command_line().lower() else None
write(R/'editor_state.json',dict(pie=bool(editor and editor.is_in_play_in_editor())))
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
for row in inventory['meshes']:
    if row.get('reuse_pair') or row.get('capture'):continue
    path=row['asset'];mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing trousers '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved trousers '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);_,bs=B.get_all_bones_info(dm)
    positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)];triangles=[xyz(t) for t in L.convert_triangle_list_to_array(fs)];names={b.index:str(b.name) for b in bs}
    slots=[str(s.material_slot_name) for s in mesh.materials];materials=[s.material_interface.get_path_name() for s in mesh.materials]
    selected=[];ids=set()
    for ti,tri in enumerate(triangles):
        if max(positions[v][2] for v in tri)<84 or min(positions[v][2] for v in tri)>112:continue
        slot=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0]
        if 'skin' in slots[slot].lower() or '/asianmale_jason/' in materials[slot].lower():continue
        selected.append(tri);ids.update(tri)
    ids=sorted(ids);remap={v:i for i,v in enumerate(ids)};weights=[]
    for vi in ids:
        _,ws,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('No waist binding '+path)
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    data=dict(source=path,positions=[positions[i] for i in ids],triangles=[[remap[i] for i in t] for t in selected],outer_shell_triangles=len(selected),weights=weights,bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bs},asset_sha256=hashlib.sha256(disk(path).read_bytes()).hexdigest())
    file=R/'Read'/(hashlib.sha256(path.encode()).hexdigest()[:12]+'.json');write(file,data);row.update(capture=str(file),asset_sha256=data['asset_sha256']);write(R/'inventory.json',inventory)
    print('PANTS_WAIST_CAPTURED',row['item'],path,flush=True);del mesh,dm,data,positions,triangles,weights;gc.collect();u.SystemLibrary.collect_garbage()
print('PANTS_WAIST_CAPTURE_COMPLETE',flush=True)
