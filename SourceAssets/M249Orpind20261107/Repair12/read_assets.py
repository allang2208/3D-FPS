"""Read live material bindings and the installed optic interfaces for production."""
from pathlib import Path
import json,hashlib,unreal as u
r=Path(__file__).resolve().parent;E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
out={'meshes':{},'materials':{},'optics':{},'hashes':{}}
def path(a):return a.get_path_name() if a else None
def material(a):
    if not a or path(a) in out['materials']:return
    row={'base':path(a.get_base_material()),'blend':str(a.get_base_material().blend_mode)}
    if isinstance(a,u.MaterialInstanceConstant):
        row['parent']=path(a.parent)
        row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(a,n) for n in L.get_scalar_parameter_names(a)}
        row['vectors']={str(n):list(L.get_material_instance_vector_parameter_value(a,n).to_tuple()) for n in L.get_vector_parameter_names(a)}
        row['textures']={str(n):path(L.get_material_instance_texture_parameter_value(a,n)) for n in L.get_texture_parameter_names(a)}
    out['materials'][path(a)]=row
def mesh(p):
    a=u.load_asset(p)
    if not isinstance(a,(u.SkeletalMesh,u.StaticMesh)):return
    slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
    out['meshes'][p]=[{'slot':str(s.material_slot_name),'material':path(s.material_interface)} for s in slots]
    for s in slots:material(s.material_interface)
    file=Path(u.Paths.project_content_dir())/(p.removeprefix('/Game/').split('.')[0]+'.uasset')
    out['hashes'][p]=hashlib.sha256(file.read_bytes()).hexdigest()
    return a
for p in ['/Game/Weapons/M249/SK_M249_V7']+list(E.list_assets('/Game/Weapons/M249/Assembly',True,False))+list(E.list_assets('/Game/Weapons/M249/Bipod',True,False)):mesh(p.split('.')[0])
for key in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic','kv_scope_4x','thermal_scope','lpvo_ring','thermal_selector'):
    p='/Game/Weapons/M24/CommonOptics20261028/Meshes/SM_M24_'+key;a=mesh(p)
    if not a:raise RuntimeError('Missing installed optic '+p)
    sockets={}
    for name in ('SightRear','SightFront','SightUp','AimCenter','ZoomRing','ZoomPivot'):
        s=a.find_socket(name)
        if s:sockets[name]={'location':list(s.relative_location.to_tuple()),'rotation':list(s.relative_rotation.to_tuple())}
    out['optics'][key]={'source':p,'sockets':sockets}
sk=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(sk,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native M249 frame unavailable')
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
def transform(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
out['frames']={str(b.name):transform(b.world_transform) for b in bones if str(b.name) in ('WPN_root','PKM_Cover','WPN_RearSight','WPN_FrontSight')}
master=u.load_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface')
out['shared_master_customs']=[str(n.get_editor_property('description')) for n in L.get_material_expressions(master) if isinstance(n,u.MaterialExpressionCustom)]
(r/'current_assets.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M249_PRODUCTION_INPUTS_READ',len(out['meshes']),len(out['materials']),flush=True)
