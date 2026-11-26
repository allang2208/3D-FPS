"""Read the original Normandy assemblies without saving the source maps."""
import json
from pathlib import Path
import unreal as u

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
folder = root / 'SourceAssets/TemperateHillsVillage'
folder.mkdir(exist_ok=True, parents=True)
assemblies = sorted((root / 'Content/UnrealNormandy/Assembly').glob('SL_Packed*.umap'))
result = {}
def xyz(v):
    return [round(n, 4) for n in (v.x, v.y, v.z)]

for source in assemblies:
    world = u.EditorLoadingAndSavingUtils.load_map('/Game/UnrealNormandy/Assembly/' + source.stem)
    if not world:
        raise RuntimeError(source.stem)
    actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
    if not any(a.get_components_by_class(u.StaticMeshComponent) for a in actors):
        desc = u.WorldPartitionBlueprintLibrary.get_actor_descs()
        if desc:
            u.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in desc])
            actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
    pieces = []
    for actor in actors:
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            mesh = c.static_mesh
            if not mesh or not mesh.get_path_name().startswith('/Game/UnrealNormandy/StaticMeshes/'):
                continue
            if not c.is_visible() or c.get_editor_property('hidden_in_game'):
                continue
            center, extent, _ = u.SystemLibrary.get_component_bounds(c)
            materials = [m.get_path_name() if m else None for m in c.get_editor_property('override_materials')]
            transforms = ([c.get_instance_transform(i, True) for i in range(c.get_instance_count())]
                          if isinstance(c, u.InstancedStaticMeshComponent) else [c.get_world_transform()])
            for t in transforms:
                r = t.rotation.rotator()
                pieces.append(dict(mesh=mesh.get_path_name(), pos=xyz(t.translation), rot=[r.pitch,r.yaw,r.roll],
                                   scale=xyz(t.scale3d), center=xyz(center), extent=xyz(extent), materials=materials,
                                   collision=str(c.get_collision_enabled()).split(':')[0].rsplit('.',1)[-1], profile=str(c.get_collision_profile_name())))
    if not pieces:
        raise RuntimeError('No authored geometry in ' + source.stem)
    result[source.stem] = pieces
    u.log('VILLAGE_READ %s %d' % (source.stem, len(pieces)))
(folder / 'house-pieces.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
