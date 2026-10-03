"""Read existing M07 actors and bindings; never start or change PIE/assets."""
import json
import math
from datetime import datetime
from pathlib import Path
import unreal as u

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != Path('D:/FPS3D/FPSGAME/FPSGAME.uproject'):
    raise RuntimeError('Read-only M07 diagnosis belongs to the FPSGAME editor.')

def prop(obj, name):
    try:
        value = obj.get_editor_property(name)
        if isinstance(value, u.Object):
            return value.get_path_name()
        return str(value)
    except Exception as exc:
        return 'unavailable: ' + str(exc)


def component(mesh):
    anim = mesh.get_anim_instance()
    return {
        'mesh': prop(mesh, 'skeletal_mesh_asset'),
        'animation_mode': prop(mesh, 'animation_mode'),
        'anim_class': prop(mesh, 'anim_class'),
        'anim_instance': anim.get_class().get_path_name() if anim else None,
        'active_clip': prop(anim, 'active_clip') if anim else None,
        'outgoing_loop': prop(anim, 'outgoing_loop') if anim else None,
        'pause_anims': prop(mesh, 'pause_anims'),
        'force_ref_pose': prop(mesh, 'force_ref_pose'),
        'leader_pose': prop(mesh, 'leader_pose_component'),
    }


bp_class = u.load_class(None, '/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.BP_BlindSupplicantM07_C')
defaults = u.get_default_object(bp_class)
report = {'defaults': component(defaults.get_editor_property('mesh'))}
report['defaults']['clips'] = {name: prop(defaults, name) for name in (
    'idle_clip', 'walk_clip', 'slow_walk_clip', 'chase_clip', 'melee_left_clip', 'melee_right_clip')}
report['saved_clip_data'] = {}
mesh_asset = defaults.get_editor_property('visual_mesh')
for name in ('idle_clip', 'slow_walk_clip', 'chase_clip'):
    clip = defaults.get_editor_property(name)
    entry = {'skeleton': prop(clip, 'skeleton'), 'length': clip.get_play_length(), 'bone_data': {}}
    for eval_type in (u.AnimDataEvalType.RAW, u.AnimDataEvalType.COMPRESSED):
        options = u.AnimPoseEvaluationOptions()
        options.set_editor_property('evaluation_type', eval_type)
        options.set_editor_property('optional_skeletal_mesh', mesh_asset)
        poses = [u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
                 for time in (0., clip.get_play_length() * .3)]
        for bone in ('upperarm_l', 'thigh_l', 'calf_l'):
            a, b = [u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.LOCAL)
                    for pose in poses]
            qa, qb = a.rotation, b.rotation
            dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
            entry['bone_data'][str(eval_type) + ':' + bone] = {
                'rotation_change_deg': math.degrees(2. * math.acos(min(1., dot)))}
    report['saved_clip_data'][name] = entry
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['game_world'] = world.get_path_name() if world else None
report['actors'] = []
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.BlindSupplicantMonster):
        record = component(actor.get_editor_property('mesh'))
        record.update(actor=actor.get_path_name(), state=prop(actor, 'state'), velocity=str(actor.get_velocity()),
                      movement_mode=prop(actor.get_character_movement(), 'movement_mode'),
                      controller=actor.get_controller().get_class().get_path_name() if actor.get_controller() else None)
        report['actors'].append(record)
    player = u.GameplayStatics.get_player_character(world, 0)
    report['player'] = {'location': str(player.get_actor_location()), 'velocity': str(player.get_velocity())} if player else None
report['editor_navigation'] = []
editor_world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
for actor in u.GameplayStatics.get_all_actors_of_class(editor_world, u.RecastNavMesh):
    report['editor_navigation'].append({'name': actor.get_name(), 'radius': prop(actor, 'agent_radius'),
                                         'height': prop(actor, 'agent_height'),
                                         'query_extent': prop(actor, 'default_query_extent'),
                                         'runtime_generation': prop(actor, 'runtime_generation')})
output = Path('D:/FPS3D/FPSGAME/Saved/Logs') / ('M07MovementCause-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_MOVEMENT_CAUSE_DATA ' + str(output), flush=True)
print('M07_EXISTING_ANIMATION_STATE ' + json.dumps(report, ensure_ascii=False), flush=True)
