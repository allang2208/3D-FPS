"""Apply the approved R14 bone motion and its four hoof contacts to the existing Canter package."""
import gzip
import json
from pathlib import Path
import sys

import unreal as ue

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_hoofsteps import AUDIO, GAITS, HORSES, LIB, bind_contacts, save


def install(data_path):
    with gzip.open(data_path, 'rt', encoding='utf-8') as stream:
        motion = json.load(stream)
    package = HORSES + '/Animations/A_Warhorse_Canter'
    clip = ue.load_asset(package)
    mesh = ue.load_asset(HORSES + '/SK_StableWarhorse')
    if not isinstance(clip, ue.AnimSequence) or clip.get_editor_property('skeleton') != mesh.skeleton:
        raise RuntimeError('Missing original Warhorse canter or skeleton')
    if any(p.get_name() == package for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('The canter package has unsaved changes')
    waves = [ue.load_asset(AUDIO + f'/SW_Hoof_Canter_{i:02}') for i in range(1, 5)]
    if not all(waves):
        raise RuntimeError('Missing original canter hoof sounds')
    pose = mesh.skeleton.get_reference_pose()
    api = ue.AnimPoseExtensions
    model = clip.get_editor_property('data_model_interface')
    data = motion['bones']
    skeleton_bones = {str(name) for name in api.get_bone_names(pose)}
    if not data.keys() <= skeleton_bones:
        raise RuntimeError('Gallop source and resident horse bones differ')
    world = {b: api.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD) for b in data}
    keys = {}
    for name, values in data.items():
        rest = api.get_bone_pose(pose, name, ue.AnimPoseSpaces.LOCAL)
        parent = world.get(values['parent'])
        basis = parent.rotation if parent is not None else ue.Quat(0, 0, 0, 1)
        undo = basis.inversed()
        right = basis * rest.rotation
        turns = [undo * ue.Quat(*q) * right for q in values['rotation']]
        positions = [rest.translation] * len(turns)
        if 'translation_cm' in values:
            positions = [rest.translation + basis.unrotate_vector(ue.Vector(*p)) / parent.scale3d
                         for p in values['translation_cm']]
        keys[name] = (positions, turns, [rest.scale3d] * len(turns))
    controller = clip.get_editor_property('controller')
    controller.open_bracket('Install approved Warhorse coastal gallop', False)
    try:
        controller.set_frame_rate(ue.FrameRate(numerator=motion['rate'], denominator=1), False)
        controller.set_number_of_frames(ue.FrameNumber(value=motion['frames']), False)
        for name, (positions, rotations, scales) in keys.items():
            if not model.is_valid_bone_track_name(name) and not controller.add_bone_curve(name, False):
                raise RuntimeError('Failed to create track ' + name)
            if not controller.set_bone_track_keys(name, positions, rotations, scales, False):
                raise RuntimeError('Failed to write track ' + name)
    finally:
        controller.close_bracket(False)
    expected = motion['frames'] / motion['rate']
    if abs(clip.get_play_length() - expected) > .0001:
        raise RuntimeError('The animation controller did not apply the requested duration')
    clip.set_editor_property('rate_scale', motion['rate_scale'])
    period, _, contacts = GAITS['Canter']
    bind_contacts(clip, waves, period, contacts, motion['contacts'])
    LIB.set_metadata_tag(clip, 'StableHoofPhases', json.dumps(motion['contacts']))
    LIB.set_metadata_tag(clip, 'StableCanterFit', motion['source'])
    LIB.set_metadata_tag(clip, 'StableHorseMotion', motion['source'])
    save(clip)
    return dict(package=package, motion=motion['source'], period_s=expected, rate_scale=motion['rate_scale'],
                game_period_at_full_speed_s=expected*660/1160/motion['rate_scale'], contact_phases=motion['contacts'])
