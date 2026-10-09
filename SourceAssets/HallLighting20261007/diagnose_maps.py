"""Inspect saved hall bindings without saving or starting PIE; restore the active map."""
import json, runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE_ACTIVE: keep the current world')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('DIRTY_MAP: preserve current work')
previous=editor.get_editor_world()
previous=previous.get_path_name().split('.')[0] if previous else None
reports=[]
try:
    for name in ('L_ReceptionHall_Subject','L_FacilityTransit_Subject','L_FacilityTransit_Alternate_Subject'):
        path='/Game/GameMaps/Design/'+name
        world=u.EditorLoadingAndSavingUtils.load_map(path)
        if not world:raise RuntimeError('Cannot inspect '+path)
        entry=dict(map=path,lights=[],diffusers=[])
        for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
            label=a.get_actor_label()
            if not label.startswith(('Reception_','FacilityTransit_')):continue
            c=a.get_component_by_class(u.PointLightComponent)
            if c:
                f=c.light_function_material
                entry['lights'].append(dict(label=label,intensity=c.intensity,
                    function=f.get_path_name() if f else None,visible=c.is_visible(),
                    shadows=c.cast_shadows,fade=c.light_function_fade_distance,
                    disabled=c.disabled_brightness))
            for c in a.get_components_by_class(u.StaticMeshComponent):
                if c.static_mesh and 'Diffuser' in c.static_mesh.get_name():
                    entry['diffusers'].append(dict(label=label,mesh=c.static_mesh.get_path_name(),
                        materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
        reports.append(entry)
finally:
    if not commandlet and previous:u.EditorLoadingAndSavingUtils.load_map(previous)
(ROOT/'Receipts/map-diagnosis.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
print('MAP_BINDINGS',[(r['map'],len(r['lights']),sum(bool(p['function']) for p in r['lights']),r['diffusers']) for r in reports])
