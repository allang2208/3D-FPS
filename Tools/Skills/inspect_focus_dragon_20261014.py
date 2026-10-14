"""Read only: current focus book state and loaded Dragon Breath range inputs."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/FocusDragon20261014')
OUT.mkdir(parents=True, exist_ok=True)

def prop(obj, name):
    try:
        value = obj.get_editor_property(name)
        return value.get_path_name() if isinstance(value, u.Object) else str(value)
    except Exception as exc:
        return 'unavailable: ' + str(exc)[:160]

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result = {'game_world': world.get_path_name() if world else None, 'pawns': []}
if world:
    for pawn in u.GameplayStatics.get_all_actors_of_class(world, u.Pawn):
        if not pawn.is_player_controlled():
            continue
        row = {'pawn': pawn.get_path_name(), 'components': []}
        for comp in pawn.get_components_by_class(u.ActorComponent):
            if 'Spellbook' not in comp.get_name() and 'Dragon' not in comp.get_name():
                continue
            item = {'name': comp.get_name(), 'class': comp.get_class().get_name()}
            if isinstance(comp, u.SkeletalMeshComponent):
                item['properties'] = {key: prop(comp, key) for key in ['skeletal_mesh_asset', 'animation_mode', 'animation_data', 'leader_pose_component', 'pause_anims', 'no_skeleton_update', 'force_refpose', 'enable_animation', 'visible', 'visibility_based_anim_tick_option']}
                inst = comp.get_anim_instance()
                item['anim_instance'] = inst.get_class().get_name() if inst else None
                item['position'] = comp.get_position()
                item['bones'] = {str(comp.get_bone_name(i)): str(comp.get_socket_transform(comp.get_bone_name(i), u.RelativeTransformSpace.RTS_COMPONENT)) for i in range(min(8, comp.get_num_bones()))}
            row['components'].append(item)
        result['pawns'].append(row)
base = '/Game/Weapons/SpellbookEvildeer20261009/PagesV1'
result['clips'] = []
for name in ['A_Spellbook_16Pages_Open', 'A_Spellbook_16Pages_Flip']:
    clip = u.load_asset(base + '/Animations/' + name)
    row = {'name': name, 'loaded': bool(clip), 'properties': {key: prop(clip, key) for key in ['skeleton', 'sequence_length', 'additive_anim_type', 'enable_root_motion']} if clip else {}, 'samples': []}
    if clip:
        for eval_type in [u.AnimDataEvalType.RAW, u.AnimDataEvalType.COMPRESSED]:
            options = u.AnimPoseEvaluationOptions()
            options.set_editor_property('evaluation_type', eval_type)
            for time in [0., min(1.95, clip.get_play_length()), clip.get_play_length()]:
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
                names = list(u.AnimPoseExtensions.get_bone_names(pose))
                row['samples'].append({'mode': str(eval_type), 'time': time, 'bones': {str(n): str(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names[:6]}})
    result['clips'].append(row)
(OUT / 'focus-runtime-before.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
