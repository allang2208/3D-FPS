"""Read-only diagnosis of the user's F6 infected-dog spawn issue."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/Saved/InfectedDogMeshy/F6Diagnosis.json')
out.parent.mkdir(parents=True, exist_ok=True)
data = {}

def read(dst, key, call):
    try:
        v = call()
        dst[key] = v if isinstance(v, (bool, int, float, str, list, dict, type(None))) else str(v)
        return v
    except Exception as e:
        dst[key] = {'error': str(e)}

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_game_world() if editor else None
data['world'] = str(world)
if world:
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    data['player'] = {'object': str(pawn)}
    if pawn:
        read(data['player'], 'location', pawn.get_actor_location)
        read(data['player'], 'rotation', pawn.get_actor_rotation)
    data['dogs'] = []
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.InfectedDogMonster):
        item = {'actor': actor.get_path_name()}
        data['dogs'].append(item)
        for key, call in [('location', actor.get_actor_location), ('rotation', actor.get_actor_rotation),
                          ('scale', actor.get_actor_scale3d), ('hidden', actor.is_hidden),
                          ('actor_bounds', lambda: actor.get_actor_bounds(False))]:
            read(item, key, call)
        for key in ['animation_set', 'health', 'max_health']:
            read(item, key, lambda key=key: actor.get_editor_property(key))
        mesh = actor.get_editor_property('mesh')
        md = {}; item['mesh'] = md
        for key in ['skeletal_mesh', 'relative_location', 'relative_rotation', 'relative_scale3d',
                    'visible', 'hidden_in_game', 'bounds_scale', 'animation_mode', 'anim_class']:
            read(md, key, lambda key=key: mesh.get_editor_property(key))
        read(md, 'world_transform', mesh.get_world_transform)
        read(md, 'component_bounds', lambda: u.SystemLibrary.get_component_bounds(mesh))
        read(md, 'anim_instance', mesh.get_anim_instance)
        read(md, 'bone_count', mesh.get_num_bones)
        md['bones'] = {}
        for i in range(mesh.get_num_bones()):
            name = str(mesh.get_bone_name(i))
            if i < 6 or any(part in name.lower() for part in ['head', 'paw', 'foot', 'root', 'pelvis']):
                read(md['bones'], name, lambda name=name: mesh.get_socket_transform(name, u.RelativeTransformSpace.RTS_COMPONENT))

asset = u.load_asset('/Game/Monsters/InfectedDog/MeshyV2/SK_InfectedDog_MeshyV2')
data['asset'] = {'name': str(asset)}
ad = data['asset']
read(ad, 'bounds', asset.get_bounds)
read(ad, 'skeleton', lambda: asset.get_editor_property('skeleton'))
imp = read(ad, 'import_data', lambda: asset.get_editor_property('asset_import_data'))
if imp:
    ad['import_options'] = {}
    for key in ['import_uniform_scale', 'convert_scene', 'convert_scene_unit', 'force_front_x_axis', 'import_translation', 'import_rotation']:
        read(ad['import_options'], key, lambda key=key: imp.get_editor_property(key))
bp = u.load_asset('/Game/Monsters/InfectedDog/BP_InfectedDog')
cdo = u.get_default_object(bp.generated_class())
data['cdo'] = {}
read(data['cdo'], 'animation_set', lambda: cdo.get_editor_property('animation_set'))
read(data['cdo'], 'mesh', lambda: cdo.get_editor_property('mesh').get_editor_property('skeletal_mesh'))
comp = u.SkeletalMeshComponent()
comp.set_skeletal_mesh_asset(asset)
names = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
data['animation_poses'] = {}
opts = u.AnimPoseEvaluationOptions()
opts.set_editor_property('evaluation_type', u.AnimDataEvalType.SOURCE)
opts.set_editor_property('optional_skeletal_mesh', asset)
for role in ['Idle', 'Walk', 'Run', 'AttackBite']:
    clip = u.load_asset('/Game/Monsters/InfectedDog/MeshyV2/Animations/A_InfectedDogMeshy_' + role)
    if not clip: continue
    cd = {'duration': clip.get_play_length()}
    data['animation_poses'][role] = cd
    for time in [0., clip.get_play_length() * .5]:
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, opts)
        pd = {}; cd[str(time)] = pd
        for name in names:
            pd[name] = {}
            for label, fn in [('ref', u.AnimPoseExtensions.get_ref_bone_pose), ('animated', u.AnimPoseExtensions.get_bone_pose)]:
                t = fn(pose, name, u.AnimPoseSpaces.WORLD)
                pd[name][label] = {'p': [t.translation.x,t.translation.y,t.translation.z],
                                   'q': [t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
                                   's': [t.scale3d.x,t.scale3d.y,t.scale3d.z]}
if world:
    data['ui'] = []
    for panel in u.WidgetBlueprintLibrary.get_all_widgets_of_class(world, u.DevelopmentPanelWidget, False):
        pd = {}; data['ui'].append(pd)
        for key in ['spawn_status', 'spawn_count']:
            read(pd, key, lambda key=key: str(panel.get_editor_property(key).get_text()))
        read(pd, 'selected', lambda: panel.get_editor_property('monster_choice').get_selected_option())
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('F6_DIAGNOSIS_SAVED ' + str(out))
