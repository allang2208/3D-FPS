"""Read the installed M870 hold frame, buttpad and tactical sockets; no saves."""
import hashlib,json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def xyz(v):return [v.x,v.y,v.z]
def tr(t):return xyz(t.translation)+[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]+xyz(t.scale3d)
mesh=u.load_asset('/Game/Weapons/M870/Tactical20261015/SK_M870_V7')
mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh)
root=mod.get_bone_transform('WPN_root',True)
front=mod.get_bone_transform('WPN_FrontSight',True).translation
rear=mod.get_bone_transform('WPN_RearSight',True).translation
forward=(front-rear).normal();up=(u.Vector(0,0,1)-forward*forward.z).normal();side=up.cross(forward).normal()
root_up=root.rotation.rotate_vector(u.Vector(0,0,1))
old_axis=(front-rear)-root_up*(front-rear).dot(root_up)
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read the installed stock surface')
_,vectors,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
points=u.GeometryScript_List.convert_vector_list_to_array(vectors)
_,indices,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
triangles=u.GeometryScript_List.convert_triangle_list_to_array(indices)
slots=[str(m.material_slot_name) for m in mesh.materials]
keep={i for i,n in enumerate(slots) if not any(s in n.lower() for s in ('skin','glove','sleeve','manny','hands'))}
ids=set()
for i,t in enumerate(triangles):
    if u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] in keep:ids.update((t.x,t.y,t.z))
coords=[(points[i].dot(forward),points[i].dot(side),points[i].dot(up)) for i in ids]
back=min(p[0] for p in coords);pad=[p for p in coords if p[0]<back+4.]
stock=forward*back+side*((min(p[1] for p in pad)+max(p[1] for p in pad))*.5)+up*((min(p[2] for p in pad)+max(p[2] for p in pad))*.5)
report=dict(mesh=mesh.get_path_name(),root_reference=tr(root),front=xyz(front),rear=xyz(rear),
    barrel_axis_component=xyz(forward),barrel_up_component=xyz(up),barrel_up_root=xyz(u.Quat(-root.rotation.x,-root.rotation.y,-root.rotation.z,root.rotation.w).rotate_vector(up)),
    old_projected_axis_component=xyz(old_axis),stock_root=xyz(root.inverse_transform_location(stock)),stock_component=xyz(stock),
    source_slots=[slots[i] for i in sorted(keep)],tactical={},poses={})
for variant in ('laser','flashlight','blessed_laser'):
    asset=u.load_asset('/Game/Weapons/M870/TacticalFit20261017/SM_'+variant)
    sockets={}
    for name in ('Emitter','AimGuide'):
        socket=asset.find_socket(name)
        if socket:sockets[name]=dict(location=xyz(socket.relative_location),rotation=str(socket.relative_rotation))
    report['tactical'][variant]=dict(asset=asset.get_path_name(),sockets=sockets)
names=list(mod.get_all_bone_names())
for role,times in (('idle',[0.]),('fire',[0.,.16,.35,.4,.62,.9])):
    clip=u.load_asset('/Game/Weapons/M870/Tactical20261015/Animations/A_M870_'+role)
    report['poses'][role]=dict(asset=clip.get_path_name(),times=times,local_frames=[
        [tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,min(seconds,clip.get_play_length()),False,mesh)] for seconds in times])
report['bone_names']=[str(n) for n in names]
report['bone_parents']=[str(mod.get_parent_name(n)) for n in names]
report['mesh_sha256']=hashlib.sha256((ROOT/'Content/Weapons/M870/Tactical20261015/SK_M870_V7.uasset').read_bytes()).hexdigest()
(OUT/'geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M870_WORLD_HOLD_GEOMETRY_READ stock_root='+str(report['stock_root'])+' up_root='+str(report['barrel_up_root']),flush=True)
