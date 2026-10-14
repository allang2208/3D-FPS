"""Two local equipment moves found by the transit source-geometry review."""
SUBJECTS=('/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject')
REVISION='transit_equipment_clearance_20261013'
PPE_POSITION=[190.,-1748.,0.]
MOP_POSITION=[-1985.,-907.,0.]

def apply_module(module):
    changes=[]
    for actor in module['runtime_actors']:
        if actor.get('container_id')=='FacilityTransit.PPE5':
            before=actor['position'];actor['position']=list(PPE_POSITION)
            changes.append(dict(id=actor['container_id'],before=before,after=actor['position']))
    for part in module['parts']:
        if part.get('id')=='Incident_CleaningMop':
            before=part['position'];part['position']=list(MOP_POSITION)
            changes.append(dict(id=part['id'],before=before,after=part['position']))
    if len(changes)!=2:raise RuntimeError('Expected the sixth PPE locker and the cleaning mop')
    return changes

def apply_subject(world):
    import unreal as u
    if world.get_path_name().split('.')[0] not in SUBJECTS:return []
    changes=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        position=None
        if isinstance(actor,u.ColdSteelSceneContainer) and str(actor.get_editor_property('container_id'))=='FacilityTransit20261007.PPE5':
            position=PPE_POSITION
        elif actor.get_actor_label()=='FacilityTransit_Incident_CleaningMop':position=MOP_POSITION
        if position is None:continue
        actor.modify();sc=actor.get_editor_property('root_component');sc.modify();mobility=sc.mobility;sc.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_location(u.Vector(position[0]+5900,position[1],position[2]),False,True)
        sc.set_mobility(mobility)
        changes.append(dict(actor=actor.get_actor_label(),room_position=position))
    if len(changes)!=2:raise RuntimeError('Expected two matching subject actors')
    return changes
