"""Bake native PCG output into static, spatially grouped game assets."""
from pathlib import Path
from datetime import datetime
import json,math,collections,runpy,unreal as u
R=Path(__file__).resolve().parent;BASE='/Game/NativeNearBank20261028'
M=json.loads((R/'publish_manifest.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
S=u.get_engine_subsystem(u.SubobjectDataSubsystem);F=u.SubobjectDataBlueprintFunctionLibrary
OWNER='CyberpunkApartment.NearBankNativePCG20261028'
policy=runpy.run_path(str(R/'Performance/component_policy.py'))['apply'] if M.get('performance_policy') else None
groups=collections.defaultdict(lambda:collections.defaultdict(list))
for row in M['rows']:
    if row.get('spline'):raise RuntimeError('Spline deformation requires a separate authored component')
    key=(row['mesh'],tuple(row['materials']),row.get('custom_stride',0))
    for tr in row['transforms']:
        p=tr['p'];cell=(math.floor(p[0]/20000),math.floor(p[1]/20000))
        groups[cell][key].append(tr)
saved=[];total=0
for (cx,cy),batch in sorted(groups.items()):
    name=f'BP_NativeBlock_{cx+20:02d}_{cy+20:02d}';asset=BASE+'/Blocks/'+name
    bp=u.load_asset(asset)
    if not bp:
        factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Actor)
        bp=A.create_asset(name,BASE+'/Blocks',u.Blueprint,factory)
    handles=S.k2_gather_subobject_data_for_blueprint(bp)
    names={str(F.get_variable_name(F.get_data(h))):h for h in handles}
    def component(n,cls,parent):
        h=names.get(n)
        if not h:
            h,error=S.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cls,blueprint_context=bp))
            if not F.is_handle_valid(h):raise RuntimeError(str(error))
            S.rename_subobject(h,u.Text(n));names[n]=h
        return h,F.get_object(F.get_data(h))
    had_authored_root='NativeDistrictRoot' in names
    root,rc=component('NativeDistrictRoot',u.SceneComponent,handles[0]);rc.set_mobility(u.ComponentMobility.STATIC)
    if not had_authored_root:
        if not S.make_new_scene_root(handles[0],root,bp):raise RuntimeError('Cannot establish static root')
    # Reset owned components before rebuilding a cell.
    for h in names.values():
        c=F.get_object(F.get_data(h))
        if isinstance(c,u.InstancedStaticMeshComponent):c.clear_instances()
    origin=[cx*20000,cy*20000,-10857];cell_count=0
    for index,((mesh_path,materials,stride),transforms) in enumerate(sorted(batch.items())):
        mesh=u.load_asset(mesh_path)
        if not mesh:raise RuntimeError('Unresolved selected asset '+mesh_path)
        h,c=component(f'NativeMesh_{index:03d}',u.HierarchicalInstancedStaticMeshComponent,root)
        c.set_mobility(u.ComponentMobility.STATIC);S.attach_subobject(root,h);c.set_static_mesh(mesh)
        c.set_num_custom_data_floats(stride)
        c.set_editor_property('override_materials',[])
        for i,p in enumerate(materials):
            if p:
                mat=u.load_asset(p)
                if not mat:raise RuntimeError('Unresolved selected material '+p)
                c.set_material(i,mat)
        hidden='/Repair/Collision/' in mesh_path
        solid=hidden or any(t in mesh_path for t in ['/Building/','/Road/','/Roads/','/Meshes/BuildingPads','/Meshes/JunctionAsphalt','/Meshes/ParkGround','/Repair/Meshes/','BlackAlder','StreetLamp','Parking_Meter','Road_Sign','Hydrant','Mailbox'])
        c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        c.set_visibility(not hidden);c.set_hidden_in_game(hidden)
        c.set_editor_property('cast_shadow',not hidden);c.set_editor_property('affect_distance_field_lighting',False)
        c.set_cull_distances(0,70000 if any(t in mesh_path for t in ['BlackAlder','/Vehicle/','Parking_Meter','Mail','Hydrant']) else 0)
        if policy:policy(c,mesh_path,mesh,transforms)
        inst=[]
        for t in transforms:
            tr=u.Transform();tr.translation=u.Vector(*[t['p'][i]-origin[i] for i in range(3)]);tr.rotation=u.Quat(*t['q']);tr.scale3d=u.Vector(*t['s']);inst.append(tr)
        c.add_instances(inst,False,False,False)
        if stride:c.set_editor_property('per_instance_sm_custom_data',[v for t in transforms for v in t['custom']])
        cell_count+=len(inst)
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Cannot compile '+name)
    cdo=u.get_default_object(bp.generated_class());tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick)
    E.set_metadata_tag(bp,'NativeDistrict.Owner',OWNER)
    if not E.save_loaded_asset(bp,False):raise RuntimeError('Cannot save '+name)
    saved.append(dict(path=bp.get_path_name(),origin=origin,label='NBPCG_'+name.removeprefix('BP_'),instances=cell_count));total+=cell_count
    print('NATIVE_BLOCK_SAVED',name,cell_count,flush=True)
(R/'publish_assets.json').write_text(json.dumps(dict(stage='blocks_saved',blocks=saved,instances=total,native_pcg_graph_executed=True,saved_at=datetime.now().astimezone().isoformat()),indent=2),encoding='utf8')
print('NATIVE_BLOCKS_SAVED',len(saved),total,flush=True)
