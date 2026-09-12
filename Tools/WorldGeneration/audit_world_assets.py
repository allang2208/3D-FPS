"""Read-only UE asset audit. Never imports, edits, saves or loads a level.

Run with UnrealEditor-Cmd <project> -run=pythonscript -script=<this file>
-unattended -NullRHI. The only output is under FPSGAME/Saved/WorldGenerationAudit.
"""
import collections
import json
from pathlib import Path
import unreal

OUT = Path('D:/FPS3D/FPSGAME/Saved/WorldGenerationAudit')
OUT.mkdir(parents=True, exist_ok=True)
project = Path(unreal.Paths.project_dir()).resolve().name
roots = (['/Game/UnrealNormandy', '/Game/MilitaryTrench', '/Game/SD_Art',
          '/Game/PWL_Light_Manager', '/Game/RPGEnvironmentVFX', '/Game/AnimalVarietyPack']
         if project == 'FPSGAME' else
         ['/Game/GrassLandscape', '/Game/Megaplant_Library',
          '/Game/MWLandscapeAutoMaterial', '/Game/PN_FoliageCollection'])
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(roots, force_rescan=False)
report = dict(project=project, project_dir=unreal.Paths.project_dir(),
              scope='Local on-disk registry and read-only metadata; no runtime/visual acceptance',
              packages={}, meshes=[], graphs=[], foliage=[], errors=[])

def attempt(row, key, fn):
    try:
        row[key] = fn()
    except Exception as exc:
        row.setdefault('unavailable', {})[key] = str(exc)[:220]

for root in roots:
    assets = registry.get_assets_by_path(root, recursive=True, include_only_on_disk_assets=True)
    assets = sorted(assets, key=lambda a: str(a.package_name))
    classes = collections.Counter(str(a.asset_class_path.asset_name) for a in assets)
    report['packages'][root] = dict(count=len(assets), classes=dict(classes), assets=[
        dict(path=str(a.package_name), cls=str(a.asset_class_path.asset_name)) for a in assets])
    for data in assets:
        cls = str(data.asset_class_path.asset_name)
        if cls not in ('StaticMesh', 'PCGGraph', 'FoliageType_InstancedStaticMesh'):
            continue
        path = str(data.package_name)
        row = dict(path=path)
        # Avoid loading multi-million-triangle nature meshes: registry tags first;
        # inspect live mesh properties for FPSGAME meshes and compact nature meshes.
        for tag in ('Triangles', 'Vertices', 'LODCount', 'NaniteEnabled', 'Materials'):
            value = data.get_tag_value(tag)
            if value:
                row['registry_' + tag] = value
        if cls == 'StaticMesh' and project != 'FPSGAME' and '/Megaplant_Library/' in path:
            row['loaded'] = False
            report['meshes'].append(row)
            continue
        try:
            obj = data.get_asset()
            if obj is None:
                raise RuntimeError('get_asset returned None')
            if cls == 'StaticMesh':
                row['loaded'] = True
                attempt(row, 'lod_count', lambda: obj.get_num_lods())
                attempt(row, 'nanite', lambda: bool(obj.get_editor_property('nanite_settings').get_editor_property('enabled')))
                attempt(row, 'simple_collision_count', lambda: sum(len(obj.get_editor_property('body_setup')
                    .get_editor_property('agg_geom').get_editor_property(p)) for p in
                    ('box_elems', 'sphere_elems', 'sphyl_elems', 'convex_elems', 'tapered_capsule_elems')))
                attempt(row, 'collision_complexity', lambda: str(obj.get_editor_property('body_setup').get_editor_property('collision_trace_flag')))
                attempt(row, 'size_m', lambda: [round(v * 0.02, 3) for v in (
                    obj.get_bounds().box_extent.x, obj.get_bounds().box_extent.y, obj.get_bounds().box_extent.z)])
                attempt(row, 'materials', lambda: [str(s.get_editor_property('material_interface').get_path_name())
                    if s.get_editor_property('material_interface') else None for s in obj.get_editor_property('static_materials')])
                report['meshes'].append(row)
            elif cls == 'PCGGraph':
                attempt(row, 'hierarchical', lambda: bool(obj.get_editor_property('use_hierarchical_generation')))
                attempt(row, 'nodes', lambda: [n.get_settings().get_class().get_name() for n in obj.get_editor_property('nodes') if n])
                report['graphs'].append(row)
            else:
                for prop in ('mesh', 'cull_distance', 'align_to_normal', 'ground_slope_angle', 'affect_distance_field_lighting'):
                    attempt(row, prop, lambda p=prop: str(obj.get_editor_property(p)))
                report['foliage'].append(row)
        except Exception as exc:
            report['errors'].append(dict(path=path, error=str(exc)[:300]))
    (OUT / (project + '-assets.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('WORLD_ASSET_AUDIT_PACKAGE ' + root + ' ' + str(dict(classes)))
unreal.log('WORLD_ASSET_AUDIT_COMPLETE ' + project + ' meshes=' + str(len(report['meshes'])) + ' errors=' + str(len(report['errors'])))
