"""Read the existing PIE pose and equipment identities; do not drive gameplay."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordGripPair20261010')
out.mkdir(parents=True, exist_ok=True)
worlds = u.EditorLevelLibrary.get_pie_worlds(True)
report = {'pie_active': bool(worlds), 'bodies': []}
def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z, t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]
for world in worlds[:1]:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        component = actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not component:
            continue
        body = component.get_body_mesh()
        if not body:
            continue
        anim = body.get_anim_instance()
        state = component.get_body_state()
        row = {'actor': actor.get_name(), 'body': body.skeletal_mesh_asset.get_path_name(),
               'state': {key: str(state.get_editor_property(key)) for key in
                   ('family', 'weapon', 'action', 'action_variant', 'action_progress', 'action_weight')},
               'grip_roll': anim.get_curve_value('SwordGripRoll'), 'bones': {}, 'meshes': []}
        for i in range(body.get_num_bones()):
            name = body.get_bone_name(i)
            row['bones'][str(name)] = pack(body.get_socket_transform(name, u.RelativeTransformSpace.RTS_WORLD))
        config = json.loads(Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
        row['configured_clips'] = {k: v for k, v in config['clips'].items()
                        if k in ('Melee.FullBody.Overhead', 'Melee.FullBody.DashOverhead')}
        for mesh in actor.get_components_by_class(u.SkeletalMeshComponent):
            if not mesh.skeletal_mesh_asset:
                continue
            item = {'name': mesh.get_name(), 'asset': mesh.skeletal_mesh_asset.get_path_name(),
                    'visible': mesh.is_visible(), 'hidden': mesh.get_editor_property('hidden_in_game'),
                    'component': pack(mesh.get_world_transform()), 'bones': {}}
            for name in ('hand_r', 'hand_l', 'WPN_root'):
                if mesh.get_bone_index(name) >= 0:
                    item['bones'][name] = pack(mesh.get_socket_transform(name, u.RelativeTransformSpace.RTS_WORLD))
            row['meshes'].append(item)
        report['bodies'].append(row)
(out / 'live-pair.json').write_text(json.dumps(report, indent=2))
print('SWORD_PAIR_LIVE ' + json.dumps({**report, 'bodies': [{k: v for k, v in row.items() if k != 'bones'} for row in report['bodies']]}))
