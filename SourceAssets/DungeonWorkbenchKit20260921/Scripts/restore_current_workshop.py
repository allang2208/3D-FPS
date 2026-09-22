"""Full dungeon rebuild only: restore final surrounding props, then the workbench assembly."""
from pathlib import Path
import json,runpy,unreal as u
ROOT=Path(__file__).resolve().parents[1];DATA=json.loads((ROOT/'Config/surroundings.json').read_text())
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve dirty maps before full workshop restoration')
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':raise RuntimeError('Full dungeon rebuild must have loaded the dungeon map')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
for r in DATA['actors']:
    a=actors.get(r['label'])
    if r.get('hidden') or not r.get('visible',True):
        if a:
            a.modify();a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True);a.set_actor_enable_collision(False)
            c=a.get_component_by_class(u.LightComponent) or a.get_component_by_class(u.StaticMeshComponent)
            if c:c.modify();c.set_visibility(False)
        continue
    if not a:
        cls=u.load_class(None,r['class_path']);a=AA.spawn_actor_from_class(cls,u.Vector());a.set_actor_label(r['label'])
    a.modify();a.set_actor_location_and_rotation(u.Vector(*r['location']),u.Rotator(roll=r['rotation'][0],pitch=r['rotation'][1],yaw=r['rotation'][2]),False,True);a.set_actor_scale3d(u.Vector(*r['scale']))
    a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    if r.get('mesh'):
        c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_static_mesh(u.load_asset(r['mesh']));c.set_editor_property('override_materials',[u.load_asset(p) if p else None for p in r['materials']]);c.set_visibility(True);c.set_collision_profile_name(r['collision']);c.set_editor_property('cast_shadow',r['cast_shadow'])
    if r.get('light'):
        c=a.get_component_by_class(u.LightComponent);c.modify();c.set_visibility(True)
        for name,value in r['light'].items():
            if name=='intensity_units':value=getattr(u.LightUnits,value.split('.')[-1])
            if name=='light_color':value=u.Color(*value)
            c.set_editor_property(name,value)
for label in DATA['retired_lights']:
    a=actors.get(label)
    if a:
        a.modify();a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True);c=a.get_component_by_class(u.LightComponent)
        if c:c.modify();c.set_visibility(False);c.set_intensity(0)
if not ED.save_current_level():raise RuntimeError('Final surrounding workshop save failed')
runpy.run_path(str(ROOT/'Scripts/import_and_install.py'),run_name='__main__',init_globals={'WORKBENCH_FULL_REBUILD':True})
