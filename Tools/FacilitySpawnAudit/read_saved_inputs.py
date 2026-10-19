"""Read saved spawn inputs without starting gameplay or modifying packages."""
import hashlib
import json
import re
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/FacilitySpawnAudit20261017'

def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None

def value(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return v.get_path_name() if isinstance(v, u.Object) else str(v)

def agent_rows(obj):
    return [{k: value(prop(a, k)) for k in ['name', 'agent_radius', 'agent_height', 'nav_data_class']}
            for a in prop(obj, 'supported_agents')]

paths = set()
for source in (ROOT / 'Source/FPSGAME/Dungeons').glob('Facility*Encounter.cpp'):
    paths.update(re.findall(r'TEXT\("((?:/Game/Monsters/[^"\n]+_C)|(?:/Script/FPSGAME\.[^"\n]+))"\)', source.read_text(encoding='utf-8-sig')))
# Transit objective candidates come from the development catalog.
paths.add('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14.BP_SpiralPillarM14_C')
report = {'read_only': True, 'gameplay_started': False, 'classes': []}
for path in sorted(paths):
    cls = u.load_class(None, path)
    row = {'path': path, 'loaded': cls is not None}
    if cls:
        cdo = u.get_default_object(cls)
        cap = prop(cdo, 'capsule_component')
        move = prop(cdo, 'character_movement')
        nav = prop(move, 'nav_agent_props')
        row.update({'capsule_radius': cap.get_scaled_capsule_radius(),
                    'capsule_half_height': cap.get_scaled_capsule_half_height(),
                    'agent': {k: value(prop(nav, k)) for k in ['agent_radius', 'agent_height', 'preferred_nav_data']},
                    'update_nav_from_collision': value(prop(prop(move, 'nav_movement_properties'), 'update_nav_agent_with_owners_collision')),
                    'defaults': {k: value(prop(cdo, k)) for k in ['rank', 'visual_mesh', 'max_health', 'level', 'attack_damage']}})
        if path.startswith('/Game/'):
            package = ROOT / 'Content' / (path.split('.')[0][6:] + '.uasset')
            row['disk'] = {'exists': package.is_file(), 'path': str(package)}
            if package.is_file():
                row['disk'].update({'sha256': hashlib.sha256(package.read_bytes()).hexdigest(), 'mtime': package.stat().st_mtime})
    report['classes'].append(row)
world = u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
nav = u.NavigationSystemV1.get_navigation_system(world)
report['navigation'] = agent_rows(nav)
report['bounds'] = [{'label': a.get_actor_label(), 'mask': [bool(prop(prop(a, 'supported_agents'), 'supports_agent'+str(i))) for i in range(7)]}
                    for a in u.GameplayStatics.get_all_actors_of_class(world, u.NavMeshBoundsVolume)]
report['generators'] = []
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator):
    catalog = prop(actor, 'module_catalog_json')
    manifest = prop(actor, 'layout_manifest_json')
    entry = {'path': actor.get_path_name(), 'catalog_bytes': len(catalog or ''), 'manifest_bytes': len(manifest or ''),
             'seed': value(prop(actor, 'generated_seed'))}
    if catalog:
        (OUT / 'saved_catalog.json').write_text(catalog, encoding='utf-8')
    if manifest:
        (OUT / 'saved_manifest.json').write_text(manifest, encoding='utf-8')
    report['generators'].append(entry)
(OUT / 'saved_inputs.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('FACILITY_SPAWN_AUDIT_SAVED classes=%d missing=%d generators=%d' %
      (len(report['classes']), sum(not r['loaded'] for r in report['classes']), len(report['generators'])), flush=True)
