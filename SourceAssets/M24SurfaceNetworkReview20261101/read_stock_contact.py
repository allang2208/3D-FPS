"""Read the installed factory buttpad and native sight frame; no asset writes."""
import unreal as u, json, hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
path='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9'
a=u.load_asset(path)
component=u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(a)
mod=u.SkeletonModifier();mod.set_skeletal_mesh(a)
root=mod.get_bone_transform('WPN_root',True)
front=mod.get_bone_transform('WPN_FrontSight',True).translation
rear=mod.get_bone_transform('WPN_RearSight',True).translation
up=root.rotation.rotate_vector(u.Vector(0,-1,0))
axis=front-rear;axis=(axis-up*axis.dot(up)).normal();side=up.cross(axis).normal()
G,Q,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
assert status==u.GeometryScriptOutcomePins.SUCCESS
_,vs,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(vs)
_,ts,_=Q.get_all_triangle_indices(dm,False);tris=L.convert_triangle_list_to_array(ts)
_,ms,_=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm);materials=L.convert_index_list_to_array(ms)
slots=[str(m.material_slot_name) for m in a.materials]
stock=slots.index('M24_FactoryStock');ids=set()
for ti,t in enumerate(tris):
    if materials[ti]==stock:ids.update([t.x,t.y,t.z])
coords=[(points[i].dot(axis),points[i].dot(side),points[i].dot(up)) for i in ids]
back=min(v[0] for v in coords);pad=[v for v in coords if v[0]<back+4.0]
lateral=(min(v[1] for v in pad)+max(v[1] for v in pad))*.5
vertical=(min(v[2] for v in pad)+max(v[2] for v in pad))*.5
contact=axis*back+side*lateral+up*vertical
xyz=lambda v:[v.x,v.y,v.z]
disk=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
row={'mesh':a.get_path_name(),'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),
     'has_stock_contact_socket':component.does_socket_exist('WPN_StockContact'),
     'has_eject_bone':component.does_socket_exist('WPN_Eject'),
     'has_generic_eject_socket':component.does_socket_exist('WPN_SOCKET_Eject'),
     'stock_root':xyz(root.inverse_transform_location(contact)),'stock_cs':xyz(contact),
     'forward_cs':xyz(axis),'up_cs':xyz(up),'source_slots':['M24_FactoryStock'],
     'contact_width_cm':max(v[1] for v in pad)-min(v[1] for v in pad),
     'contact_height_cm':max(v[2] for v in pad)-min(v[2] for v in pad)}
(O/'stock_contact.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
print('M24_WORLD_STOCK_CONTACT',json.dumps(row),flush=True)
