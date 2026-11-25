"""Place the residents in their own stalls, in streamed village-local centimetres."""
import math
import unreal as ue
from stable_actors import ASSEMBLY, ROOT, label_stable

TAG='VillageStable.Horses'
FOLDER=ROOT+'/Horses'


def load(path):
    asset=ue.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing horse asset '+path)
    return asset


def install_horses(actors, upgrade_placed=False):
    mesh=load(FOLDER+'/SK_StableWarhorse')
    ref=mesh.skeleton.get_reference_pose()
    get=ue.AnimPoseExtensions.get_bone_pose
    def pos(pose,name):
        return get(pose,name,ue.AnimPoseSpaces.WORLD).translation
    forward=pos(ref,'mouth_socket')-pos(ref,'pelvis')
    heading=math.degrees(math.atan2(forward.y,forward.x))
    bounds=mesh.get_imported_bounds()
    floor_z=.8-(bounds.origin.z-bounds.box_extent.z)
    if not 150<2*bounds.box_extent.z<285:
        raise RuntimeError('Expected a full-size warhorse in centimetres: '+str(bounds.box_extent))
    opts=ue.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh=mesh
    horses=[]
    existing={actor.get_actor_label():actor for actor in actors.get_all_level_actors()
              if TAG in map(str,actor.tags) and ASSEMBLY in map(str,actor.tags)}
    for stall,clip_name,facing in [(2,'Q_Feed',180.),(4,'Idle',153.)]:
        clip=load(FOLDER+'/Animations/A_Warhorse_'+clip_name)
        direction=ue.Rotator(yaw=facing-heading)
        if stall==2:
            # Set the muzzle inside the hay crib using the actual sequence in UE centimetres.
            mouths=[pos(ue.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/12,opts),
                        'mouth_socket') for i in range(12)]
            mouth=tuple(sum(getattr(pt,key) for pt in mouths)/len(mouths) for key in ('x','y','z'))
            bite=ue.MathLibrary.transform_location(ue.Transform(rotation=direction),ue.Vector(*mouth))
            if not 75 < floor_z+bite.z < 105:
                raise RuntimeError('Horse mouth does not reach the hay at its authored height: '+str(bite))
            at=ue.Vector(3779-bite.x,3819-bite.y,floor_z)
        else:
            at=ue.Vector(4840,3820,floor_z)
        label='Village_Stable_Horse_Stall%02d'%stall
        previous=existing.get(label)
        if upgrade_placed and previous is None:
            raise RuntimeError('Missing placed resident '+label)
        if upgrade_placed and previous:
            skin=previous.mesh if isinstance(previous,ue.StableRidingHorse) else previous.skeletal_mesh_component
            at=skin.get_world_location()
            facing=skin.get_world_rotation().yaw+heading
        actor=previous if isinstance(previous,ue.StableRidingHorse) else None
        if actor is None:
            if previous is not None and not isinstance(previous,ue.SkeletalMeshActor):
                raise RuntimeError('Unexpected resident class for '+label)
            actor=actors.spawn_actor_from_class(ue.StableRidingHorse,at,ue.Rotator(yaw=facing))
            if not actor:
                raise RuntimeError('Could not create rideable resident '+label)
            if previous is not None and not actors.destroy_actor(previous):
                raise RuntimeError('Could not replace old resident '+label)
            label_stable(actor,label,[ASSEMBLY,TAG])
        actor.modify()
        half=actor.capsule_component.get_scaled_capsule_half_height()
        actor.set_actor_location_and_rotation(at+ue.Vector(0,0,half),ue.Rotator(yaw=facing),False,True)
        comp=actor.mesh
        comp.modify()
        comp.set_mobility(ue.ComponentMobility.MOVABLE)
        comp.set_skeletal_mesh_asset(mesh)
        comp.set_relative_location_and_rotation(ue.Vector(0,0,-half),ue.Rotator(yaw=-heading),False,True)
        comp.set_simulate_physics(False)
        actor.set_editor_property('registered_stall',stall)
        actor.set_editor_property('stall_animation',clip)
        for field,sequence in [('idle_animation','Idle'),('walk_animation','Walk'),('canter_animation','Canter')]:
            actor.set_editor_property(field,load(FOLDER+'/Animations/A_Warhorse_'+sequence))
        comp.set_animation_mode(ue.AnimationMode.ANIMATION_SINGLE_NODE)
        data=comp.get_editor_property('animation_data')
        data.anim_to_play=clip
        data.saved_looping=True
        data.saved_playing=True
        data.saved_play_rate=1.
        data.saved_position=0. if stall==2 else clip.get_play_length()*.34
        comp.set_editor_property('animation_data',data)
        row=dict(stall=stall,actor=label,actor_class=actor.get_class().get_path_name(),
                 loop=clip.get_path_name(),location_cm=list(at.to_tuple()),yaw_deg=facing)
        if stall==2:
            row['mean_muzzle_cm']=[at.x+bite.x,at.y+bite.y,at.z+bite.z]
        horses.append(row)
    return dict(scope='riding' if upgrade_placed else 'horses',horses=horses)
