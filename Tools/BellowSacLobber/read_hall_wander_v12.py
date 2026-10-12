"""Read the requested idle/wander bindings and authored hall floor inputs; no simulation."""
import json
import unreal as u

cls = u.load_class(None, '/Game/Monsters/BellowSacLobber/BP_BellowSacLobber.BP_BellowSacLobber_C')
cdo = u.get_default_object(cls)
movement = cdo.get_editor_property('character_movement')
anim = cdo.get_editor_property('animation_set')
ai = cdo.get_editor_property('ai_controller_class')
report = {
    'class': cls.get_path_name(),
    'ai': ai.get_path_name(),
    'auto_possess_ai': str(cdo.get_editor_property('auto_possess_ai')),
    'movement_class': movement.get_class().get_path_name(),
    'walk_speed': cdo.get_editor_property('walk_speed'),
    'chase_speed': cdo.get_editor_property('chase_speed'),
    'wander_radius': u.get_default_object(ai).get_editor_property('wander_radius'),
    'animation_set': anim.get_path_name(),
    'animation_walk_speed': anim.get_editor_property('walk_speed'),
    'animation_run_speed': anim.get_editor_property('run_speed'),
    'pie_active': bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),
    'dirty_content': [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    'dirty_maps': [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
report['hall_floors'] = []
for generator in u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator):
    catalog = json.loads(generator.get_editor_property('module_catalog_json'))
    for module in catalog['modules']:
        if module['id'] not in ('FacilityReceptionHall', 'FacilityTransit'):
            continue
        report['hall_floors'].append({
            'module': module['id'],
            'parts': [p for p in module['parts'] if any(s in p['mesh'] for s in ('MezzanineStructure', 'GallerySlab'))],
        })
print('BELLOW_HALL_WANDER_INPUTS ' + json.dumps(report, ensure_ascii=False))
