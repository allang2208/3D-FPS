"""Add navigation to the DayNight development area without starting gameplay."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
MAP = '/Game/GameMaps/DayNight_Lighting'
map_file = ROOT / 'Content/GameMaps/DayNight_Lighting.umap'
output = ROOT / 'Saved/FatZombieNavigation'
output.mkdir(parents=True, exist_ok=True)
before_hash = hashlib.sha256(map_file.read_bytes()).hexdigest()
backup = output / ('before_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
backup.mkdir()
shutil.copy2(map_file, backup / map_file.name)

level = u.get_editor_subsystem(u.LevelEditorSubsystem)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
# Run through the current editor's Python console to retain its loaded map
# and allow UE's asset-loading/nav-build ticks to finish before this script.
if not world or world.get_path_name() != MAP + '.DayNight_Lighting':
    raise RuntimeError('Open DayNight_Lighting in the editor before running this script')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop gameplay before editing navigation')
actors = u.get_editor_subsystem(u.EditorActorSubsystem)

# The 5 km weather floor is a backdrop. Cover the player start, traversal
# props and surrounding 200 x 200 m development area with real brush bounds.
center = u.Vector(1000, 1000, 300)
extent = u.Vector(10000, 10000, 600)
if not u.MonsterAIController.build_navigation_bounds(world, center, extent):
    raise RuntimeError('Navigation bounds/build failed')

navmeshes = [a for a in actors.get_all_level_actors() if isinstance(a, u.RecastNavMesh)]
report = {
    'map': MAP,
    'backup': str(backup / map_file.name),
    'before_sha256': before_hash,
    'bounds_center_cm': [center.x, center.y, center.z],
    'bounds_extent_cm': [extent.x, extent.y, extent.z],
    'navigation': [],
}
for nav in navmeshes:
    report['navigation'].append({
        'name': nav.get_actor_label(),
        'radius_cm': nav.get_editor_property('agent_radius'),
        'height_cm': nav.get_editor_property('agent_height'),
    })

if hashlib.sha256(map_file.read_bytes()).hexdigest() != before_hash:
    raise RuntimeError('Map changed on disk during navigation build; leaving newer disk copy intact')
if not level.save_current_level():
    raise RuntimeError('Cannot save the repaired map')
report['after_sha256'] = hashlib.sha256(map_file.read_bytes()).hexdigest()

# Re-query only the failed source/target from the user's existing gameplay log.
# FatZombie is radius 44 / height 172; its suitable configured navmesh is
# HandBrain (62 / 204), not the smaller Nurse (34 / 184).
fat_nav = next((nav for nav in navmeshes
                if nav.get_editor_property('agent_radius') == 62
                and nav.get_editor_property('agent_height') == 204), None)
report['reported_path'] = {'navigation': fat_nav.get_actor_label() if fat_nav else None}
if fat_nav:
    path = u.NavigationSystemV1.find_path_to_location_synchronously(
        world, u.Vector(1629.017, 2017.575, 88.150),
        u.Vector(1292.926, 1647.383, 98.150), fat_nav)
    report['reported_path'].update({
        'valid': path.is_valid() if path else False,
        'partial': path.is_partial() if path else None,
        'length_cm': path.get_path_length() if path else 0,
        'points': [[p.x, p.y, p.z] for p in path.path_points] if path else [],
    })
(output / 'repair.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('FAT_NAV_REPAIR ' + json.dumps(report))
