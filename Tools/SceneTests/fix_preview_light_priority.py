"""Fix only the known key/fill priority tie in the M4 validation map."""
import json
from pathlib import Path
import unreal

path = '/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation'
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert level.load_level(path)
lights = {a.get_name(): a.light_component for a in actors.get_all_level_actors() if isinstance(a, unreal.DirectionalLight)}
assert set(lights) == {'DirectionalLight_0', 'DirectionalLight_1'}, list(lights)
assert lights['DirectionalLight_0'].get_editor_property('intensity') == 4.0
assert lights['DirectionalLight_1'].get_editor_property('intensity') == 2.0
before = {name: light.get_editor_property('forward_shading_priority') for name, light in lights.items()}
lights['DirectionalLight_0'].set_editor_property('forward_shading_priority', 1)
lights['DirectionalLight_1'].set_editor_property('forward_shading_priority', 0)
lights['DirectionalLight_1'].set_editor_property('atmosphere_sun_light', False)
assert level.save_current_level()
assert level.load_level(path)
after = {a.get_name(): a.light_component.get_editor_property('forward_shading_priority') for a in actors.get_all_level_actors() if isinstance(a, unreal.DirectionalLight)}
assert after == {'DirectionalLight_0': 1, 'DirectionalLight_1': 0}, after
fill = next(a for a in actors.get_all_level_actors() if a.get_name() == 'DirectionalLight_1')
assert not fill.light_component.get_editor_property('atmosphere_sun_light')
(Path(unreal.Paths.project_saved_dir()) / 'LightingAudit' / 'preview-fix.json').write_text(json.dumps(dict(before=before, after=after), indent=2))
unreal.log('PREVIEW_LIGHT_PRIORITY_FIX_PASS')
