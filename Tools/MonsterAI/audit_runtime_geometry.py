"""Read active creature CDOs and mesh statistics without spawning or saving assets."""
from datetime import datetime
from pathlib import Path
import json
import re
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT / 'Saved/MonsterGeometryAudit20261006'
OUT.mkdir(parents=True, exist_ok=True)
CORE = {'BlindSupplicantM07', 'MantisM27', 'LurkerM08', 'FleshHand', 'FleshHandMinion',
        'HandBrain', 'PoisonMaggot', 'HangingBellM09', 'VortexCofferM25', 'M10Mawcrawler',
        'SpiralPillarM14', 'HundredEyedSlag'}
report = dict(started=datetime.now().isoformat(), complete=False, actors=[], meshes={},
              errors=[], assets_saved=False, gameplay_run=False, performance_measured=False)
subsystem = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)

def record():
    (OUT / 'runtime.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default

def path(obj):
    return obj.get_path_name() if obj else None

def scalar(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return prop(value, 'default', str(value))

def mesh_info(mesh):
    key = mesh.get_path_name()
    if key in report['meshes']:
        return key
    # FAssetData(UObject*) obtains current object/render statistics; it does
    # not substitute old documentation counts or nominal reduction ratios.
    data = u.AssetRegistryHelpers.create_asset_data(mesh)
    result = dict(path=key, kind=mesh.get_class().get_name(), tags={}, lods=[])
    for name in ('Triangles', 'Vertices', 'LODs', 'Bones', 'MorphTargets', 'MaxBoneInfluences',
                 'NaniteEnabled', 'NaniteTriangles', 'NaniteVertices'):
        result['tags'][name] = u.AssetRegistryHelpers.get_tag_value(data, name)
    if isinstance(mesh, u.SkeletalMesh):
        count = subsystem.get_lod_count(mesh)
        result['lod_count'] = count
        models = list(prop(mesh, 'source_models', []))
        for index in range(count):
            lod = dict(index=index, vertices=subsystem.get_num_verts(mesh, index),
                       sections=subsystem.get_num_sections(mesh, index))
            if index == 0 and result['tags'].get('Triangles'):
                lod['triangles'] = int(result['tags']['Triangles'])
            else:
                # Read actual lower-LOD render geometry, not target fractions.
                dynamic = u.DynamicMesh()
                requested = u.GeometryScriptMeshReadLOD()
                requested.set_editor_property('lod_type', u.GeometryScriptLODType.RENDER_DATA)
                requested.set_editor_property('lod_index', index)
                _, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
                    mesh, dynamic, u.GeometryScriptCopyMeshFromAssetOptions(), requested)
                if outcome != u.GeometryScriptOutcomePins.SUCCESS:
                    raise RuntimeError('Could not read render LOD ' + str(index) + ' of ' + key)
                lod['triangles'] = dynamic.get_triangle_count()
                dynamic.reset()
            if index < len(models):
                model = models[index]
                lod['screen_size'] = scalar(prop(model, 'screen_size'))
                settings = prop(model, 'reduction_settings')
                lod['target_triangle_fraction'] = scalar(prop(settings, 'num_of_triangles_percentage')) if settings else None
            result['lods'].append(lod)
        result['materials'] = [path(prop(slot, 'material_interface')) for slot in prop(mesh, 'materials', [])]
        result['skeleton'] = path(prop(mesh, 'skeleton'))
        result['min_lod'] = scalar(prop(mesh, 'min_lod'))
        result['ray_tracing_min_lod'] = scalar(prop(mesh, 'ray_tracing_min_lod'))
        result['lod_settings'] = path(prop(mesh, 'lod_settings'))
        imported = prop(mesh, 'asset_import_data')
        result['import_sources'] = list(imported.extract_filenames()) if imported else []
        result['corpse_bindings'] = []
        result['user_data_classes'] = [x.get_class().get_name() for x in mesh.get_editor_property('asset_user_data') if x]
        binding_class = u.load_class(None, '/Script/FPSGAME.MonsterSoftCorpseBinding')
        binding = mesh.get_asset_user_data_of_class(binding_class)
        if binding:
            # Data is a protected native UPROPERTY. Preserve that limitation and
            # trace the package's unique hard M14SoftBodyData dependency instead.
            options = u.AssetRegistryDependencyOptions()
            options.set_editor_property('include_hard_package_references', True)
            options.set_editor_property('include_soft_package_references', False)
            dependencies = u.AssetRegistryHelpers.get_asset_registry().get_dependencies(key.split('.')[0], options)
            result['soft_corpse_dependency_paths'] = [str(x) for x in dependencies if '/SoftCorpseV1/' in str(x) and '/DA_' in str(x)]
            if len(result['soft_corpse_dependency_paths']) != 1:
                raise RuntimeError('Corpse binding dependency is not unique: ' + key)
            corpse_data = u.load_asset(result['soft_corpse_dependency_paths'][0])
            corpse_mesh = corpse_data.get_editor_property('corpse_mesh')
            result['corpse_bindings'].append(dict(binding=path(binding), data=path(corpse_data), mesh=path(corpse_mesh),
                method='binding exists + unique hard package dependency + data asset CorpseMesh; protected Binding.Data not directly read'))
    report['meshes'][key] = result
    return key

source = (PROJECT / 'Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp').read_text(encoding='utf8')
entries = re.findall(r'Add\(TEXT\("([^"]+)"\),\s*TEXT\("([^"]+)"\),\s*TEXT\("([^"]+)"\)', source)
report['registry_source'] = 'Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp'
report['registry_entries'] = len(entries)
report['dirty_before'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
record()
for ident, label, class_path in entries:
    if ident not in CORE:
        continue
    item = dict(id=ident, label=label, class_path=class_path)
    report['actors'].append(item)
    try:
        cls = u.load_class(None, class_path)
        if not cls:
            raise RuntimeError('Class could not load: ' + class_path)
        cdo = u.get_default_object(cls)
        component = prop(cdo, 'mesh')
        visual = prop(cdo, 'visual_mesh')
        component_mesh = component.get_skeletal_mesh_asset() if component else None
        mesh = visual or component_mesh
        if not mesh:
            raise RuntimeError('No active visual mesh on ' + class_path)
        item['visual_property'] = path(visual)
        item['component_mesh'] = path(component_mesh)
        item['active_mesh'] = mesh_info(mesh)
        item['component_forced_lod'] = scalar(prop(component, 'forced_lod_model'))
        item['component_min_lod'] = scalar(prop(component, 'min_lod_model'))
        item['component_scale'] = str(prop(component, 'relative_scale3d'))
        item['lod_behavior_properties'] = {name: scalar(prop(cdo, name)) for name in
            ('bMinion', 'bUseCoherentGillMotion', 'ClothResumeDistance', 'ClothSuspendDistance')}
        item['skeletal_components'] = []
        for extra in cdo.get_components_by_class(u.SkeletalMeshComponent):
            extra_mesh = extra.get_skeletal_mesh_asset()
            if extra_mesh:
                item['skeletal_components'].append(dict(component=extra.get_name(), mesh=mesh_info(extra_mesh),
                                                        visible=scalar(prop(extra, 'visible'))))
        corpse_data = prop(cdo, 'soft_body_death_data')
        item['corpse_meshes'] = []
        if corpse_data and prop(corpse_data, 'corpse_mesh'):
            item['corpse_meshes'].append(mesh_info(prop(corpse_data, 'corpse_mesh')))
        for binding in report['meshes'][item['active_mesh']].get('corpse_bindings', []):
            if binding['mesh']:
                item['corpse_meshes'].append(mesh_info(u.load_asset(binding['mesh'])))
        item['corpse_meshes'] = sorted(set(item['corpse_meshes']))
        print('GEOMETRY_AUDIT ' + ident + ' ' + str(report['meshes'][item['active_mesh']]['tags']), flush=True)
    except Exception as error:
        item['error'] = str(error)
        report['errors'].append(dict(id=ident, error=str(error)))
    record()
report['authored_corpse_manifest'] = []
for authored in json.loads((PROJECT / 'SourceAssets/MonsterSoftCorpse20261005/sources.json').read_text(encoding='utf8')):
    if not any(character in CORE for character in authored['characters']):
        continue
    entry = dict(key=authored['key'], source=authored['source'], manifest_mesh=authored['corpse'])
    try:
        data_path = '/Game/Monsters/SoftCorpseV1/' + authored['key'] + '/DA_' + authored['key'] + '_SoftCorpse'
        data = u.load_asset(data_path)
        corpse_mesh = data.get_editor_property('corpse_mesh') if data else None
        entry.update(data=path(data), actual_data_mesh=mesh_info(corpse_mesh) if corpse_mesh else None)
    except Exception as error:
        entry['error'] = str(error)
        report['errors'].append(dict(id=authored['key'] + ' authored corpse', error=str(error)))
    report['authored_corpse_manifest'].append(entry)
    record()
report['dirty_after'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
report.update(complete=True, finished=datetime.now().isoformat())
record()
print('MONSTER_GEOMETRY_AUDIT_SAVED ' + str(OUT / 'runtime.json') + ' errors=' + str(len(report['errors'])), flush=True)
