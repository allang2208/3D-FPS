"""Read the affected body asset and any existing player pose; never start PIE."""
import sys
from pathlib import Path
import unreal as u
P = Path('D:/FPS3D/FPSGAME'); R = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'Tools/ModularOutfit'))
import garment_ue as g
config = g.read(P / 'Content/ColdSteelData/modular_outfits.json')
item = config['items']['ue_field_sweater']
g.write(R / 'before.json', dict(recipe=item))
native, profile = next((k, v) for k, v in config['profiles'].items() if v['rig_profile'] == 'Body')
folder = R / 'Before/Body'; paths = dict(shirt=item['rig_meshes']['Body'], skin=profile['native_bare_skin'], native=native)
for key in ('shirt', 'skin'):
    asset = u.load_asset(paths[key]); _, data = g.source_snapshot(asset)
    data['slots'] = [dict(slot=str(m.material_slot_name), material=m.material_interface.get_path_name() if m.material_interface else '') for m in asset.get_editor_property('materials')]
    g.write(folder / (key + '.json'), data)
    paths[key + '_sha256'] = g.digest(g.asset_file(paths[key]))
g.write(folder / 'paths.json', paths)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
live = dict(playing=bool(world), components=[])
if world:
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    if pawn:
        for component in pawn.get_components_by_class(u.SkeletalMeshComponent):
            asset = component.get_skinned_asset()
            if not asset or not component.is_visible():
                continue
            leader = component.get_editor_property('leader_pose_component')
            row = dict(name=component.get_name(), asset=asset.get_path_name(),
                leader=leader.get_name() if leader else None,
                transform=g.transform(component.get_world_transform()),
                only_owner_see=component.get_editor_property('only_owner_see'),
                owner_no_see=component.get_editor_property('owner_no_see'),
                materials=[component.get_material(i).get_path_name() if component.get_material(i) else '' for i in range(component.get_num_materials())],
                lod=component.get_predicted_lod_level(),
                bones={str(component.get_bone_name(i)): g.transform(component.get_socket_transform(component.get_bone_name(i), u.RelativeTransformSpace.RTS_COMPONENT)) for i in range(component.get_num_bones())})
            live['components'].append(row)
            print('FIELD_SURFACE_LIVE', row['name'], row['asset'], 'LOD', row['lod'], 'leader', row['leader'], flush=True)
g.write(R / 'live.json', live)
traversal = item['rig_meshes']['Traversal']
native, row = next((k, v) for k, v in config['profiles'].items() if v['rig_profile'] == 'Traversal')
folder = R / 'Before/Traversal'
for key, path in [('shirt', traversal), ('skin', row['native_bare_skin'])]:
    asset = u.load_asset(path); _, data = g.source_snapshot(asset)
    g.write(folder / (key + '.json'), data)
g.write(folder / 'paths.json', dict(shirt=traversal, native=native, skin=row['native_bare_skin'],
    shirt_sha256=g.digest(g.asset_file(traversal)), skin_sha256=g.digest(g.asset_file(row['native_bare_skin']))))
poses = {}
options = u.AnimPoseEvaluationOptions(optional_skeletal_mesh=u.load_asset(native), evaluation_type=u.AnimDataEvalType.COMPRESSED)
for action in ('Vault', 'Mantle', 'Climb'):
    path = '/Game/Movement/Traversal/Native/A_Traversal_' + action
    clip = u.load_asset(path)
    for i in range(11):
        time = clip.get_play_length() * i / 10
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
        poses[action + '_' + str(i)] = dict(clip=path, time=time, bones={n: g.transform(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in data['rest']})
g.write(folder / 'poses.json', poses)
print('FIELD_SURFACE_CAPTURED', 'playing', live['playing'], 'components', len(live['components']), flush=True)
