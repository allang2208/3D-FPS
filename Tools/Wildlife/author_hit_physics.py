"""Give each ambient character its own copy of the model's bone collision."""
import unreal as u

library = u.EditorAssetLibrary
for species, pack in [('DeerDoe', 'DeerStagAndDoe'), ('DeerStag', 'DeerStagAndDoe'),
                      ('Pig', 'Pig'), ('Fox', 'Fox'), ('Crow', 'Crow')]:
    folder = '/Game/Monsters/Wildlife/' + species
    character = library.load_asset(f'{folder}/BP_WL_{species}')
    component = u.get_default_object(character.generated_class()).get_editor_property('mesh')
    original = f'/Game/AnimalVarietyPack/{pack}/Meshes/SK_{species}_PhysicsAsset'
    path = f'{folder}/PA_WL_{species}'
    physics = library.load_asset(path) if library.does_asset_exist(path) else library.duplicate_asset(original, path)
    if not physics:
        raise RuntimeError(f'Could not create {path}')
    bodies = [body for body in u.ObjectIterator(u.BodySetup) if body.get_outer() == physics]
    if not bodies:
        raise RuntimeError(f'Missing skeletal bodies on {path}')
    for body in bodies:
        body.modify()
        body.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
    if not library.save_loaded_asset(physics, False):
        raise RuntimeError(f'Could not save {path}')
    character.modify()
    component.modify()
    component.set_physics_asset(physics, True)
    if not library.save_loaded_asset(character, False):
        raise RuntimeError(f'Could not save {character.get_path_name()}')
    u.log(f'WILDLIFE_HIT_PHYSICS {species} bodies={len(bodies)} asset={path}')
