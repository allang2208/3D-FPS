"""Read installed parts, native fitting surfaces and motion inputs for authoring."""
import unreal as u,json,pickle,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent; (r/'Input').mkdir(exist_ok=True)
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;out={'parts':{},'materials':{},'hashes':{}}
keys=['skeleton','core_stock','qr_performance','tactical_telescopic','phantom_reargrip','stable_antislip_reargrip','balanced_reargrip','vertical','tactical_vertical','canted','prism','angled','suppressor','tactical_suppressor','brake','titanium_brake']
paths={k:'/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_'+k for k in keys}
paths['legendary_adjustable_tactical_stock']='/Game/Weapons/LegendaryStock20261006/Fitted/SM_TacticalStock_PKM'
paths['multi_caliber_suppressor']='/Game/Weapons/CommonHK41620260930/Meshes/SM_Common_multi_caliber_suppressor'
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def path(a):return a.get_path_name() if a else None
def record(a):
    p=path(a);f=Path(u.Paths.project_content_dir())/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
    out['hashes'][p]=hashlib.sha256(f.read_bytes()).hexdigest()
def material(a):
    if not a or path(a) in out['materials']:return
    base=a.get_base_material();row={'base':path(base),'blend':str(base.blend_mode)}
    if isinstance(a,u.MaterialInstanceConstant):
        row['parent']=path(a.parent)
        row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(a,n) for n in L.get_scalar_parameter_names(a)}
        row['vectors']={str(n):list(L.get_material_instance_vector_parameter_value(a,n).to_tuple()) for n in L.get_vector_parameter_names(a)}
        row['textures']={str(n):path(L.get_material_instance_texture_parameter_value(a,n)) for n in L.get_texture_parameter_names(a)}
    row['customs']=[dict(description=str(n.get_editor_property('description')),code=n.get_editor_property('code')) for n in L.get_material_expressions(base) if isinstance(n,u.MaterialExpressionCustom)]
    out['materials'][path(a)]=row
for key,p in paths.items():
    a=u.load_asset(p)
    if not isinstance(a,u.StaticMesh):raise RuntimeError('Missing source '+p)
    f=r/'Input'/('SM_'+key+'.fbx')
    t=u.AssetExportTask();t.object=a;t.filename=str(f);t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.StaticMeshExporterFBX();t.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Export '+p)
    slots=[dict(slot=str(s.material_slot_name),material=path(s.material_interface)) for s in a.static_materials]
    for s in a.static_materials:material(s.material_interface)
    sockets={}
    for name in ('Muzzle','AimGuide','Mount','MountCenter'):
        s=a.find_socket(name)
        if s:sockets[name]=list(s.relative_location.to_tuple())
    out['parts'][key]=dict(source=p,fbx=str(f),slots=slots,sockets=sockets);record(a)
    print('M249_PART_SOURCE',key,flush=True)
def rig(p):
    mesh=u.load_asset(p);dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native geometry '+p)
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);bones=sorted(bones,key=lambda b:b.index)
    d=dict(names=[str(b.name) for b in bones],parents=[b.parent_index for b in bones],bind=[tr(b.world_transform) for b in bones]);record(mesh)
    return mesh,dm,d
mesh,dm,d=rig('/Game/Weapons/M249/SK_M249_V7')
_,v,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False);_,f,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
d['vertices']=[v.to_tuple() for v in u.GeometryScript_List.convert_vector_list_to_array(v)]
d['faces']=[(v.x,v.y,v.z) for v in u.GeometryScript_List.convert_triangle_list_to_array(f)]
d['sections']=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(d['faces']))]
d['slots']=[str(s.material_slot_name) for s in mesh.materials];d['clips']={}
for p in ['/Game/Weapons/M249/Animations/A_M249_'+k for k in ('idle','fire','equip','inspect','quick_melee','reload','reload_empty','sprint_enter','sprint_loop','sprint_exit')]+['/Game/Weapons/M249/Bipod/A_M249_Bipod']:
    clip=u.load_asset(p)
    if not isinstance(clip,u.AnimSequence):continue
    fps=120;duration=clip.get_play_length();count=round(duration*fps)+1
    d['clips'][path(clip)]=dict(fps=fps,duration=duration,frames=[[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,d['names'],min(i/fps,duration),False,mesh)] for i in range(count)])
    record(clip);print('M249_MOTION_SOURCE',clip.get_name(),count,flush=True)
def profile(p):
    a=u.load_asset(p)
    if not a:return []
    record(a)
    return [dict(base=path(c.get_editor_property('base')),retained=path(c.get_editor_property('retained')),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]) for c in a.get_editor_property('clips')]
d['support']=profile('/Game/Weapons/M249/Bipod/DA_M249_SupportGrip')
d['bipod']=profile('/Game/Weapons/M249/Bipod/DA_M249_Bipod')
with (r/'native.pkl').open('wb') as f:pickle.dump(d,f)
donor,dm,pd=rig('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular');pd['holds']={}
for family in ('base','vertical','canted','prism','angled'):
    pp=profile('/Game/Weapons/AnimationProfiles20261001/ue_pkm_lowpoly/DA_'+family)
    layer=next((c for c in pp if c['base'].split('.')[0].endswith('_idle')),None)
    cp=layer['retained'] or layer['base'] if layer else '/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_idle'
    clip=u.load_asset(cp)
    if not clip:raise RuntimeError('Donor idle '+cp)
    pd['holds'][family]=dict(local=[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,pd['names'],0.,False,donor)],tracks=layer['tracks'] if layer else [],clip=cp)
with (r/'donor.pkl').open('wb') as f:pickle.dump(pd,f)
(r/'inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M249_COMMON_PART_INPUTS_SAVED',len(out['parts']),flush=True)
