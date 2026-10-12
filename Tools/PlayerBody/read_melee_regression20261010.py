"""Read the reported melee assets and existing session; never start or stop play."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME')
out = root / 'SourceAssets/ThirdPersonMeleeRegression20261010'
out.mkdir(parents=True, exist_ok=True)
config = json.loads((root / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
keys = ['Uppercut', 'Overhead', 'DashOverhead', 'Whirlwind.Start', 'Whirlwind.Loop', 'Whirlwind.End']
report = {'body_mesh': config['body_mesh'], 'clips': {}, 'existing_bodies': []}
for key in keys:
    path = config['clips']['Melee.FullBody.' + key]
    clip = u.load_asset(path)
    if not clip:
        raise RuntimeError('Missing configured melee asset: ' + path)
    times, values = u.AnimationLibrary.get_float_keys(clip, 'SwordGripRoll')
    report['clips'][key] = dict(asset=path, skeleton=clip.get_editor_property('skeleton').get_path_name(),
        duration=clip.get_play_length(), markers=[str(m.marker_name) for m in u.AnimationLibrary.get_animation_sync_markers(clip)],
        source_hash=u.EditorAssetLibrary.get_metadata_tag(clip, 'GripSourceHash'),
        curve_keys=len(values), curve_range=[min(values), max(values)] if values else [])
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['pie_active'] = bool(world)
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        body = actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not body:
            continue
        mesh = body.get_body_mesh()
        if not mesh:
            continue
        state = body.get_body_state()
        anim = mesh.get_anim_instance()
        row = dict(actor=actor.get_name(), mesh=mesh.skeletal_mesh_asset.get_path_name(),
            family=str(state.family), action=str(state.action), variant=str(state.action_variant), progress=state.action_progress)
        if anim:
            clips = anim.get_editor_property('clips')
            row['loaded_clips'] = {str(k): v.get_path_name() for k, v in clips.items() if str(k).startswith('Melee.FullBody.') and v}
        report['existing_bodies'].append(row)
(out / 'asset-and-session-before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, separators=(',', ':')))
