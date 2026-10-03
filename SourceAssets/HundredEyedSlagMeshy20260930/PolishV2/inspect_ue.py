import unreal as u
import json
from pathlib import Path
OUT = Path(__file__).resolve().parent
BASE = '/Game/Monsters/HundredEyedSlag/V1'
mesh = u.load_asset(BASE + '/SK_HundredEyedSlag_V1')
material = u.load_asset(BASE + '/Materials/M_HundredEyedSlag_Skin')
report = {'mesh': mesh.get_path_name(), 'materials': [], 'material': {}, 'actors': [], 'animations': {}}
for slot in mesh.get_editor_property('materials'):
    report['materials'].append({'name': str(slot.material_slot_name),
        'material': slot.material_interface.get_path_name() if slot.material_interface else None})
for prop in ('used_with_skeletal_mesh', 'shading_model', 'blend_mode', 'material_domain'):
    report['material'][prop] = str(material.get_editor_property(prop))
for prop in (u.MaterialProperty.MP_FRONT_MATERIAL, u.MaterialProperty.MP_BASE_COLOR,
             u.MaterialProperty.MP_NORMAL):
    node = u.MaterialEditingLibrary.get_material_property_input_node(material, prop)
    report['material'][str(prop)] = node.get_class().get_name() if node else None
report['material']['textures'] = [x.get_path_name() for x in u.MaterialEditingLibrary.get_used_textures(material)]
for role in ('Idle', 'Run', 'Move', 'Death'):
    clip = u.load_asset(BASE + '/Animations/A_HundredEyedSlag_' + role)
    model = clip.get_editor_property('data_model_interface')
    opts = u.AnimPoseEvaluationOptions()
    opts.evaluation_type = u.AnimDataEvalType.SOURCE
    opts.optional_skeletal_mesh = mesh
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, 0., opts)
    names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
    report['animations'][role] = {'seconds': clip.get_play_length(), 'keys': model.get_number_of_keys(),
        'bones': names, 'root': str(u.AnimPoseExtensions.get_ref_bone_pose(pose, 'root', u.AnimPoseSpaces.WORLD))}
physics = mesh.get_editor_property('physics_asset')
report['physics'] = {'asset': physics.get_path_name()}
try:
    bodies = list(physics.get_editor_property('skeletal_body_setups'))
    report['physics']['bodies'] = [{'bone': str(x.get_editor_property('bone_name')),
        'geometry': str(x.get_editor_property('agg_geom'))} for x in bodies]
except Exception as exc: report['physics']['python_detail'] = str(exc)
actor_class = u.load_class(None, '/Script/FPSGAME.HundredEyedSlagMonster')
defaults = u.get_default_object(actor_class)
report['defaults'] = {'chase_speed': defaults.get_editor_property('chase_speed'),
    'mesh_materials': [m.get_path_name() if m else None for m in defaults.mesh.get_materials()]}
worlds = [u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()]
try:
    game_world = u.EditorLevelLibrary.get_game_world()
    if game_world: worlds.append(game_world)
except Exception: pass
for world in worlds:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, actor_class):
        comp = actor.mesh
        report['actors'].append({'name': actor.get_name(), 'world': world.get_name(),
            'state': str(actor.get_editor_property('state')),
            'mesh': str(comp.get_skeletal_mesh_asset()),
            'materials': [m.get_path_name() if m else None for m in comp.get_materials()],
            'overrides': [str(m) for m in comp.get_editor_property('override_materials')],
            'anim_instance': str(comp.get_anim_instance()),
            'speed': actor.get_velocity().length()})
(OUT / 'before_ue.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('SLAG_DIAG ' + json.dumps(report, ensure_ascii=False))
