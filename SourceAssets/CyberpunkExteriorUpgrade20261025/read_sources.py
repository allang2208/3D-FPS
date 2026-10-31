"""Read imported authoring assemblies and the formal exterior's attachment inputs."""
from pathlib import Path
import unreal as u,json,gc
R=Path(__file__).resolve().parent;PROJECT=R.parents[1]
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
report=dict(assemblies={},meshes={},materials={},map={})

def tr(t):
    return dict(p=list(t.translation.to_tuple()),q=list(t.rotation.to_tuple()),s=list(t.scale3d.to_tuple()))

def material(m):
    if not m:return None
    path=m.get_path_name()
    if path in report['materials']:return path
    row=dict(type=m.get_class().get_name())
    if isinstance(m,u.MaterialInstanceConstant):
        row['parent']=m.get_editor_property('parent').get_path_name()
        row['scalars']={str(k):L.get_material_instance_scalar_parameter_value(m,k) for k in L.get_scalar_parameter_names(m)}
        row['vectors']={str(k):list(L.get_material_instance_vector_parameter_value(m,k).to_tuple()) for k in L.get_vector_parameter_names(m)}
        row['textures']={str(k):(L.get_material_instance_texture_parameter_value(m,k).get_path_name() if L.get_material_instance_texture_parameter_value(m,k) else None) for k in L.get_texture_parameter_names(m)}
    report['materials'][path]=row
    return path

def mesh(m):
    path=m.get_path_name()
    if path not in report['meshes']:
        b=m.get_bounding_box()
        report['meshes'][path]=dict(min=list(b.min.to_tuple()),max=list(b.max.to_tuple()),slots=[str(s.material_slot_name) for s in m.static_materials],materials=[material(s.material_interface) for s in m.static_materials],nanite=m.get_editor_property('nanite_settings').enabled)
    return path

def components(actor):
    rows=[]
    for c in actor.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        instances=[tr(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())] if isinstance(c,u.InstancedStaticMeshComponent) else [tr(c.get_world_transform())]
        row=dict(component=c.get_name(),mesh=mesh(c.static_mesh),materials=[material(m) for m in c.get_materials()],instances=instances)
        try:row['custom_primitive_data']=list(c.get_editor_property('custom_primitive_data').get_editor_property('data'))
        except Exception:pass
        for key in ('num_custom_data_floats','per_instance_sm_custom_data'):
            try:row[key]=list(c.get_editor_property(key)) if key=='per_instance_sm_custom_data' else c.get_editor_property(key)
            except Exception:pass
        rows.append(row)
    return rows

# Only an unsaved authoring world is used to resolve packed Blueprint components.
# No sample or test map is created in Content.
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
folder=PROJECT/'Content/CitySampleBuildings/Building/Library/Kit_Ref_Bldg/LevelInstance'
paths=[p for p in sorted(folder.glob('BPP_*.uasset')) if 'Level01' not in p.stem]
for p in paths:
    asset='/Game/'+p.relative_to(PROJECT/'Content').with_suffix('').as_posix()
    cls=E.load_blueprint_class(asset)
    if not cls:raise RuntimeError('Missing reference building '+asset)
    actor=aa.spawn_actor_from_class(cls,u.Vector())
    report['assemblies'][p.stem]=dict(asset=asset,components=components(actor))
    aa.destroy_actor(actor)
    (R/'sources.json').write_text(json.dumps(report),encoding='utf8')
    print('EXTERIOR_SOURCE_ASSEMBLY',p.stem,len(report['assemblies'][p.stem]['components']),flush=True)

for name in ('SM_Slums_Vent_02c','SM_Slums_Vent_02d','SM_Slums_Pipe_05a','SM_Slums_Wires_02a','SM_Slums_Pipe_03a'):
    p='/Game/SoulCity/Environment/Meshes/Building_Slum/'+name
    m=u.load_asset(p)
    if m:mesh(m)
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=a.get_actor_label()
    if not (label.startswith(('BAY_','AP7_BayLandmark_','AP8_','AP9_','AP15_','AP16_','AP18_','AP19_')) or label=='AP7_Atmosphere'):continue
    report['map'][label]=dict(transform=tr(a.get_actor_transform()),components=components(a))
report['stage']='authoring_sources_read'
(R/'sources.json').write_text(json.dumps(report),encoding='utf8')
print('EXTERIOR_SOURCES_READY',len(report['assemblies']),len(report['meshes']),len(report['materials']))
