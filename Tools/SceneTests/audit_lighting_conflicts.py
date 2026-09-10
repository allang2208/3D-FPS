"""Read actual loaded light components in all three gameplay maps; never saves assets."""
import json
from pathlib import Path
import unreal

out = Path(unreal.Paths.project_saved_dir()) / 'LightingAudit'
out.mkdir(exist_ok=True)
editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {}
for name in ['DayNight_Lighting', 'L_Normandy_FPS_Test', 'L_MilitaryTrench_FPS_Test']:
    assert editor.load_level('/Game/GameMaps/' + name)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rows = []
    for actor in actors_api.get_all_level_actors():
        components = actor.get_components_by_class(unreal.LightComponentBase)
        relevant = any(s in actor.get_class().get_name().lower() for s in ['daynight', 'lighting_manager', 'sequence', 'skyatmosphere'])
        if not components and not relevant:
            continue
        row = dict(label=actor.get_actor_label(), cls=actor.get_class().get_name(), path=actor.get_path_name(), lights=[])
        for light in components:
            item = dict(name=light.get_name(), cls=light.get_class().get_name())
            for prop in ['intensity', 'visible', 'affects_world', 'mobility', 'forward_shading_priority', 'atmosphere_sun_light', 'atmosphere_sun_light_index', 'real_time_capture']:
                try:
                    value = light.get_editor_property(prop)
                    item[prop] = value if isinstance(value, (bool, int, float, str)) else str(value)
                except Exception:
                    pass
            row['lights'].append(item)
        if isinstance(actor, unreal.LevelSequenceActor):
            row['auto_play'] = actor.get_editor_property('playback_settings').get_editor_property('auto_play')
        rows.append(row)
    report[name] = rows
    (out / 'editor-before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('LIGHTING_AUDIT_MAP ' + name + ' ' + json.dumps(rows))
unreal.log('LIGHTING_EDITOR_AUDIT_COMPLETE')
