"""Scoped light replacement in an explicitly supplied saved world."""
import unreal as u
from pathlib import Path
import copy,json,runpy,math

ROOT=Path(__file__).resolve().parent

COMMON=('intensity_units','intensity','attenuation_radius','light_color','use_temperature','temperature',
    'cast_shadows','cast_static_shadows','cast_dynamic_shadows','indirect_lighting_intensity',
    'volumetric_scattering_intensity','max_draw_distance','max_distance_fade_range',
    'light_function_material','light_function_scale','light_function_fade_distance','disabled_brightness',
    'lighting_channels','affect_translucent_lighting','affect_reflection','affect_global_illumination')

def apply(world,actor,binding):
    old=actor.get_component_by_class(u.LocalLightComponent)
    if not old:raise RuntimeError('Missing local light: '+actor.get_actor_label())
    f=binding['fields'];kind=f['type'];replacement=actor
    rot=u.Rotator(pitch=f.get('pitch',-90),yaw=f.get('yaw',0),roll=f.get('roll',0))
    location=u.Vector(*f['position'])
    needs_rect=kind=='rect' and not isinstance(old,u.RectLightComponent)
    if needs_rect:
        aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor.get_editor_world()!=world:raise RuntimeError('Scoped scene save requires the target editor world')
        replacement=aa.spawn_actor_from_class(u.RectLight,location,rot)
        if not replacement:raise RuntimeError('Could not create bound rect light')
        if replacement.get_world()!=world:raise RuntimeError('Wrong target world')
        replacement.set_actor_label(actor.get_actor_label()+'_FixtureBound')
        replacement.set_folder_path(actor.get_folder_path())
        replacement.set_editor_property('tags',list(actor.tags))
        replacement.set_owner(actor.get_owner())
        light=replacement.get_component_by_class(u.RectLightComponent)
        for key in COMMON:light.set_editor_property(key,old.get_editor_property(key))
        light.set_intensity(old.intensity*.25)
    else:light=old
    replacement.modify();light.modify();light.set_mobility(u.ComponentMobility.MOVABLE)
    if not binding.get('preserve_transform'):
        replacement.set_actor_location_and_rotation(location,rot,False,True)
    if kind=='rect':
        light.set_editor_property('source_width',f['source_width_cm']);light.set_editor_property('source_height',f['source_height_cm'])
    elif isinstance(light,u.PointLightComponent):
        light.set_editor_property('source_radius',f.get('source_radius',1.));light.set_editor_property('source_length',f.get('source_length',0.))
    if replacement!=actor:
        label=actor.get_actor_label()
        aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        if not aa.destroy_actor(actor):raise RuntimeError('Could not remove superseded light: '+label)
        replacement.set_actor_label(label)
    return replacement

def snapshot(actor):
    c=actor.get_component_by_class(u.LocalLightComponent)
    return dict(label=actor.get_actor_label(),type=c.get_class().get_name(),position=[c.get_world_location().x,c.get_world_location().y,c.get_world_location().z],
        forward=[c.get_forward_vector().x,c.get_forward_vector().y,c.get_forward_vector().z],intensity=c.intensity,
        function=c.light_function_material.get_path_name() if c.light_function_material else None)

def apply_subject(world=None):
    world=world or u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0] not in ('/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject'):return []
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    data=json.loads((ROOT/'Config/bindings.json').read_text('utf8'))
    rows=data['modules']['FacilityTransit'];out=[];offset=[5900,0,0]
    def shifted(b):
        b=copy.deepcopy(b)
        for key in ('position',):b['fields'][key]=[a+d for a,d in zip(b['fields'][key],offset)]
        return b
    for i,b in enumerate(rows):
        if i<19:label='FacilityTransit_Hall_'+b['original_id']
        elif i<21:label='FacilityTransit_'+b['original_id']
        else:
            route=(i-21)//2+1;lamp=(i-21)%2
            candidates=[name for name in actors if name.startswith('FacilityTransit_') and name.endswith('_Route'+str(route)+'_'+str(lamp))]
            if len(candidates)!=1:raise RuntimeError('Cannot identify subject portal light')
            label=candidates[0]
        a=actors[label];before=a.get_component_by_class(u.LocalLightComponent)
        already_rect=isinstance(before,u.RectLightComponent)
        a=apply(world,a,shifted(b))
        if b.get('intensity_scale') and not already_rect:a.get_component_by_class(u.LocalLightComponent).set_intensity(a.get_component_by_class(u.LocalLightComponent).intensity*b['intensity_scale'])
        out.append(snapshot(a));actors[label]=a
    for b in data['splits']['FacilityTransit']:
        i=b['source_index'];route=(i-21)//2+1
        original=next(a for name,a in actors.items() if name.startswith('FacilityTransit_') and name.endswith('_Route'+str(route)+'_1'))
        label='FacilityTransit_FixtureTunnelB_Route'+str(route)
        if label not in actors:
            aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
            b2=shifted(b);f=b2['fields']
            a=aa.spawn_actor_from_class(u.RectLight,u.Vector(*f['position']),u.Rotator(pitch=f['pitch'],yaw=f['yaw'],roll=f['roll']))
            a.set_actor_label(label);a.set_folder_path(original.get_folder_path());a.set_editor_property('tags',list(original.tags))
            src=original.get_component_by_class(u.LocalLightComponent);dst=a.get_component_by_class(u.LocalLightComponent)
            for key in COMMON:dst.set_editor_property(key,src.get_editor_property(key))
            actors[label]=a
        a=apply(world,actors[label],shifted(b));out.append(snapshot(a))
    # These two maintained walkthrough maps also contain the original reception.
    reception=runpy.run_path(str(ROOT.parent/'ReceptionLighting20261009/recipe.py'))
    for p in reception['layout']()['lights']:
        label='Reception_'+p['id'];a=actors.get(label)
        if not a:raise RuntimeError('Reception copy is missing a lamp')
        pos=reception['anchor'](p);pos[2]+=reception['EMITTER_OFFSET_CM'];local=p['role']!='main'
        f=dict(type='rect' if local else 'spot',position=pos,pitch=-90,yaw=0,roll=90 if local else 0,
            source_width_cm=123.,source_height_cm=32.,source_radius=1.,source_length=0.)
        a=apply(world,a,dict(fields=f))
        if not local:reception['apply_subject_coverage'](a.get_component_by_class(u.LocalLightComponent))
        out.append(snapshot(a))
    coverage=ROOT.parent/'DungeonLightCoverage20261009/recipe.py'
    if coverage.exists():
        reach=runpy.run_path(str(coverage))
        if reach['installed']():reach['apply_subject'](world)
    ground=ROOT.parent/'ReceptionGroundLighting20261009/recipe.py'
    if ground.exists():
        fill=runpy.run_path(str(ground))
        if fill['installed']():out.extend(fill['apply_subject'](world))
    finish=ROOT.parent/'ReceptionFinish20261010/recipe.py'
    if finish.exists():
        detail=runpy.run_path(str(finish))
        if detail['installed']():detail['apply_subject'](world)
    transit_finish=ROOT.parent/'TransitFinish20261010/recipe.py'
    if transit_finish.exists():
        detail=runpy.run_path(str(transit_finish))
        if detail['installed']():detail['apply_subject'](world)
    incident=ROOT.parent/'TransitIncidentDressing20261010/recipe.py'
    if incident.exists():
        detail=runpy.run_path(str(incident))
        if detail['installed']():detail['apply_subject'](world)
    incident_detail=ROOT.parent/'TransitIncidentDetail20261010/recipe.py'
    if incident_detail.exists():
        detail=runpy.run_path(str(incident_detail))
        if detail['installed']():detail['apply_subject'](world)
    stair_corner=ROOT.parent/'HallStairCorner20261010/recipe.py'
    if stair_corner.exists():
        detail=runpy.run_path(str(stair_corner))
        if detail['installed']():detail['apply_subject'](world)
    facility_detail=ROOT.parent/'FacilityDetailRepair20261010/recipe.py'
    if facility_detail.exists():
        detail=runpy.run_path(str(facility_detail))
        if detail['installed']():detail['apply_subject'](world)
    return out
