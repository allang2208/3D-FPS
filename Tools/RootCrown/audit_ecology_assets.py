"""Read-only Root Crown asset/area audit requested by the user. No play or saves."""
import json
from pathlib import Path
import unreal as u

report = {'asset_checks': {}, 'missing': [], 'gameplay_tested': False, 'multiplayer_tested': False}
bp = u.load_asset('/Game/Monsters/RootCrown/BP_RootCrownRigPreview')
if not bp or not bp.generated_class():
    raise RuntimeError('Root Crown blueprint/class missing')
cdo = u.get_default_object(bp.generated_class())
for key in ('visual_mesh', 'hit_surface_physics', 'idle_clip', 'move_clip', 'turn_left_clip',
            'turn_right_clip', 'slash_clip', 'needle_clip', 'root_clip', 'stun_clip', 'air_clip',
            'land_clip', 'get_up_clip', 'death_clip', 'slash_material', 'slash_arc_material',
            'needle_mesh', 'needle_material', 'root_knot_mesh', 'root_flesh_material',
            'root_warning_material', 'mine_signal_material', 'slash_gesture_sound',
            'slash_contact_sound', 'needle_gesture_sound', 'needle_impact_sound',
            'root_gesture_sound', 'root_break_sound', 'hit_sound', 'land_sound', 'death_sound',
            'ai_controller_class'):
    value = cdo.get_editor_property(key)
    report['asset_checks'][key] = value.get_path_name() if value else None
    if not value:
        report['missing'].append(key)
hits = cdo.get_editor_property('hit_clips')
report['hit_clips'] = [x.get_path_name() if x else None for x in hits]
if len(hits) != 4 or any(x is None for x in hits):
    report['missing'].append('four_directional_hit_clips')
report['numbers'] = {key: cdo.get_editor_property(key) for key in
    ('max_health', 'level', 'walk_speed', 'turn_speed', 'slash_damage', 'needle_damage',
     'root_damage', 'mine_trigger_radius', 'mine_blast_radius', 'mine_fuse_seconds', 'mine_lifetime')}
report['rank'] = str(cdo.get_editor_property('rank'))
report['mesh_materials'] = [x.material_interface.get_path_name() if x.material_interface else None
                          for x in cdo.get_editor_property('visual_mesh').get_editor_property('materials')]
report['catalogs'] = []
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if not isinstance(actor, u.AuthoredDungeonGenerator):
        continue
    catalog = json.loads(actor.get_editor_property('module_catalog_json') or '{}')
    report['catalogs'].append({'actor': actor.get_path_name(),
        'ecology_modules': [m for m in catalog.get('modules', []) if m.get('id') in
                            ('EcoNursery', 'EcoHydroponics', 'EcoBiosphere')]})
out = Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014/Reports/ecology_asset_audit.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print('ROOT_CROWN_ASSET_AUDIT ' + json.dumps({'missing': report['missing'],
    'asset_count': len(report['asset_checks']), 'catalog_count': len(report['catalogs'])}))
