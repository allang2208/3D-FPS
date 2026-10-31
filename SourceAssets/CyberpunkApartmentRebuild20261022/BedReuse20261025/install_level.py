"""Reuse the approved bed and throw on the other existing apartment bed."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import unreal as u

R = Path(__file__).resolve().parent
PROJECT = R.parents[2]
MAP = '/Game/GameMaps/L_CyberpunkApartment'
TAG = 'Apartment.BedReuse20261025'
TARGETS = (('AP_Bed3_Bed', 'AP_Bed3_FootThrow', 'Bed3'),)


def pose(actor):
    rotation = actor.get_actor_rotation()
    return dict(position=list(actor.get_actor_location().to_tuple()),
                rotation=dict(pitch=rotation.pitch, yaw=rotation.yaw, roll=rotation.roll),
                scale=list(actor.get_actor_scale3d().to_tuple()))


def apply_upgrade(world):
    if not world or world.get_path_name().split('.')[0] != MAP:
        raise RuntimeError('Only the formal apartment can receive this bed upgrade')
    actors = {a.get_actor_label(): a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)}
    source = actors['AP_Bed2_Bed'].static_mesh_component
    source_throw = actors['BP_FootThrow'].static_mesh_component
    mesh = source.static_mesh
    throw_mesh = source_throw.static_mesh
    # Reuse the live approved surface instances, including their calibrated UV scale.
    if not mesh or 'SM_BP_BedRefined' not in mesh.get_name() or not throw_mesh:
        raise RuntimeError('The formal Bed2 upgrade must be installed first')
    profiles = json.loads((PROJECT/'Content/ColdSteelData/apartment_furniture_rest.json').read_text('utf-8-sig'))
    profile = next((r for r in profiles['furniture'] if r['mesh'] == mesh.get_path_name()), None)
    if profile is None:
        raise RuntimeError('Approved bed rest profile is missing')
    # Resolve the exact owned actors before any map mutation; never create a missing bed.
    for label, throw_label, room in TARGETS:
        bed = actors[label]
        if not isinstance(bed, u.StaticMeshActor):
            raise RuntimeError('Unexpected bed actor type: '+label)
        if any(abs(a-b) > .02 for a, b in zip(bed.get_actor_scale3d().to_tuple(), profile['scale'])):
            raise RuntimeError('Bed requires a separate size/contact adaptation: '+label)
        existing_throw = actors.get(throw_label)
        if existing_throw and not existing_throw.actor_has_tag(TAG):
            raise RuntimeError('Preserve an unrelated actor named '+throw_label)
    subsystem = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    rows = []
    for label, throw_label, room in TARGETS:
        bed = actors[label]
        comp = bed.static_mesh_component
        old_mesh = comp.static_mesh.get_path_name() if comp.static_mesh else None
        original_pose = pose(bed)
        bed.modify()
        comp.modify()
        mobility = comp.get_editor_property('mobility')
        comp.set_mobility(u.ComponentMobility.MOVABLE)
        comp.set_static_mesh(mesh)
        comp.set_editor_property('override_materials', list(source.get_materials()))
        comp.set_mobility(mobility)
        tags = list(bed.tags)
        if u.Name(TAG) not in tags:
            bed.set_editor_property('tags', tags+[u.Name(TAG)])
        # Keep the original actor identity, pose, collision profile and room links.
        throw = actors.get(throw_label)
        created = throw is None
        if created:
            throw = subsystem.spawn_actor_from_class(u.StaticMeshActor, bed.get_actor_location())
            throw.set_actor_label(throw_label)
            throw.set_editor_property('tags', [u.Name(TAG)])
        throw.modify()
        throw.set_folder_path('Apartment20261022/'+room+'/Bedding')
        tc = throw.static_mesh_component
        tc.set_mobility(u.ComponentMobility.MOVABLE)
        tc.set_static_mesh(throw_mesh)
        tc.set_editor_property('override_materials', list(source_throw.get_materials()))
        tc.set_collision_profile_name('NoCollision')
        tc.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        throw.set_actor_enable_collision(False)
        tc.set_editor_property('cast_shadow', source_throw.get_editor_property('cast_shadow'))
        tc.set_editor_property('visible_in_ray_tracing', source_throw.get_editor_property('visible_in_ray_tracing'))
        # Both approved meshes share the same bed-local origin. Attach once so
        # future placement changes carry the bedspread along with the mattress.
        throw.attach_to_actor(bed, u.Name('None'), u.AttachmentRule.KEEP_WORLD,
                              u.AttachmentRule.KEEP_WORLD, u.AttachmentRule.KEEP_WORLD, False)
        tc.set_relative_transform(u.Transform(), False, False)
        tc.set_mobility(mobility)
        rows.append(dict(actor=label, previous_mesh=old_mesh, mesh=mesh.get_path_name(),
                         transform=original_pose, materials=[m.get_path_name() if m else None for m in comp.get_materials()],
                         foot_throw=throw_label, foot_throw_created=created,
                         foot_throw_mesh=throw_mesh.get_path_name(),
                         collision_profile=str(comp.get_collision_profile_name()),
                         rest_profile=mesh.get_path_name()))
    return dict(map=MAP, beds=rows, reused_mesh_assets=2, created_mesh_assets=0,
                created_maps=0, game_tested=False)


def main():
    subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if subsystem and subsystem.get_game_world():
        raise RuntimeError('Current PIE must end before saving the apartment')
    dirty = u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty:
        raise RuntimeError('Preserve unsaved maps: '+str([p.get_path_name() for p in dirty]))
    path = PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap'
    backup = R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/path.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    world = subsystem.get_editor_world() if subsystem else None
    if not world or world.get_path_name().split('.')[0] != MAP:
        world = u.EditorLoadingAndSavingUtils.load_map(MAP)
    report = apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError('Formal apartment save failed')
    report.update(stage='formal_apartment_beds_saved', saved_at=datetime.now().astimezone().isoformat(),
                  backup=str(backup), map_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  new_editor_started=False)
    (R/'installed.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print('APARTMENT_BEDS_REUSED_AND_SAVED', len(report['beds']), report['saved_at'])


if __name__ == '__main__':
    main()
