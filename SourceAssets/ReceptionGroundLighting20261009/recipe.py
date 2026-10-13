"""Six fixture-bound gallery downlights. All established reception lamps stay intact."""
from pathlib import Path
import copy,json

ROOT=Path(__file__).resolve().parent
REVISION='reception_ground_continuity_20261010'
MODULE='FacilityReceptionHall'
MESH='/Game/Dungeons/IndustrialV1/Meshes/SM_CeilingLamp_Cool'
MATERIALS=['/Game/Dungeons/IndustrialV1/Materials/M_DarkSteel',
           '/Game/Dungeons/HallLighting20261007/Materials/M_SteadyDiffuser']
SUBJECTS=('/Game/GameMaps/Design/L_ReceptionHall_Subject',
          '/Game/GameMaps/Design/L_FacilityTransit_Subject',
          '/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject')

def fixtures():
    # Authored gallery underside: 412 cm. Existing fitting hanger top: +21 cm.
    # Glass: -8..-4 cm; protective ribs end at -10.5 cm. Emitter clears ribs by 1 cm.
    rows=[]
    for side in (-1,1):
        for x,role,lm,radius in ((-1400,'arrival',350.,800.),(-280,'stair_approach',300.,750.),(1200,'east_gallery',350.,800.)):
            key='GroundContinuity_'+('South' if side<0 else 'North')+'_'+role
            anchor=[x,side*1225.,391.]
            rows.append(dict(id=key,anchor=anchor,light=dict(id=key,type='rect',
                position=[anchor[0],anchor[1],anchor[2]-11.5],pitch=-90.,yaw=0.,roll=90.,
                intensity=lm,radius=radius,optimized_radius_cm=radius,role='local',
                color=[.86,.86,.78],cast_shadows=True,source_width_cm=106.,source_height_cm=20.,
                indirect_lighting_intensity=.4,volumetric_scattering_intensity=0.,
                max_draw_distance_cm=3200.,fade_range_cm=650.,
                fixture_anchor_cm=anchor,fixture_mesh=MESH,ground_continuity_revision=REVISION)))
    return rows

def is_added(row):return row.get('ground_continuity_revision')==REVISION

def apply_module(module):
    if module['id']!=MODULE:return []
    # Replace only this overlay's rows; never re-normalize old lamp intensities.
    module['lights']=[p for p in module['lights'] if not is_added(p)]
    module['parts']=[p for p in module['parts'] if not is_added(p)]
    rows=fixtures()
    for row in rows:
        module['lights'].append(copy.deepcopy(row['light']))
        module['parts'].append(dict(id=row['id']+'_Fixture',mesh=MESH,position=row['anchor'],
            scale=[1.,1.,1.],yaw=0.,collision=False,cast_shadow=True,fluid=False,
            materials=MATERIALS,ground_continuity_revision=REVISION))
    module['runtime_assets']=sorted(set(module.get('runtime_assets',[]))|{MESH,*MATERIALS})
    module['ground_continuity_revision']=REVISION
    return rows

def installed():
    receipt=ROOT/'Receipts/install.json'
    return receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='maps_saved'

def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    result=copy.deepcopy(catalog)
    apply_module(next(m for m in result['modules'] if m['id']==MODULE))
    result['facility_flow']['layout_bank']['contract_sha1']=contract_hash(result)
    return result

def apply_subject(world):
    import unreal as u
    if world.get_path_name().split('.')[0] not in SUBJECTS:return []
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_editor_world()!=world:raise RuntimeError('New gallery fixtures require the target editor world')
    aa=u.get_editor_subsystem(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    mesh=u.load_asset(MESH);materials=[u.load_asset(p) for p in MATERIALS]
    if not mesh or not all(materials):raise RuntimeError('Missing existing gallery lamp assets')
    changed=[]
    for row in fixtures():
        fixture_label='Reception_'+row['id']+'_Fixture'
        light_label='Reception_'+row['id']
        for label in (fixture_label,light_label):
            if label in actors and REVISION not in [str(t) for t in actors[label].tags]:
                raise RuntimeError('Preserve unowned actor: '+label)
        fixture=actors.get(fixture_label)
        if not fixture:
            fixture=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*row['anchor']),u.Rotator())
            fixture.set_actor_label(fixture_label)
        fixture.modify();sc=fixture.static_mesh_component;sc.modify()
        sc.set_mobility(u.ComponentMobility.MOVABLE)
        fixture.set_actor_location_and_rotation(u.Vector(*row['anchor']),u.Rotator(),False,True)
        sc.set_static_mesh(mesh)
        for i,mat in enumerate(materials):sc.set_material(i,mat)
        sc.set_cast_shadow(True);sc.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        sc.set_editor_property('generate_overlap_events',False)
        sc.set_mobility(u.ComponentMobility.STATIC)
        f=row['light'];rotation=u.Rotator(pitch=-90.,yaw=0.,roll=90.)
        actor=actors.get(light_label)
        if not actor:
            actor=aa.spawn_actor_from_class(u.RectLight,u.Vector(*f['position']),rotation)
            actor.set_actor_label(light_label)
        actor.modify();light=actor.get_component_by_class(u.RectLightComponent);light.modify()
        light.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_location_and_rotation(u.Vector(*f['position']),rotation,False,True)
        light.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        light.set_intensity(f['intensity']);light.set_attenuation_radius(f['radius'])
        light.set_light_color(u.LinearColor(*f['color'],1.));light.set_cast_shadows(True)
        for key,value in dict(source_width=106.,source_height=20.,indirect_lighting_intensity=.4,
            volumetric_scattering_intensity=0.,max_draw_distance=3200.,max_distance_fade_range=650.).items():
            light.set_editor_property(key,value)
        for a in (fixture,actor):
            a.set_folder_path('Reception/GroundContinuity')
            a.set_editor_property('tags',list(set([str(t) for t in a.tags]+['Reception.Subject',REVISION])))
        changed.append(dict(id=row['id'],intensity=light.intensity,radius=light.attenuation_radius,
            position=[light.get_world_location().x,light.get_world_location().y,light.get_world_location().z],
            forward=[light.get_forward_vector().x,light.get_forward_vector().y,light.get_forward_vector().z]))
    return changed
