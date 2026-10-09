"""Future authorized UE 5.8.3 commandlet: import only this package's new assets.

No editor launch, map construction, PIE, render, tests, route activation or
external-asset modifications. Existing mismatched assets are never overwritten.
"""
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_common as c
import container_bridge as containers


def main():
    import unreal as u
    c.execution_guard(u)
    scene, manifest, roles = c.load_inputs()
    revision = scene['revision']
    E = u.EditorAssetLibrary
    A = u.AssetToolsHelpers.get_asset_tools()
    L = u.MaterialEditingLibrary
    S = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if S is None:
        S = u.new_object(u.StaticMeshEditorSubsystem)
    if any(o.get('nanite', False) for o in manifest['objects']) and not hasattr(u, 'PlazaInstanceTools'):
        raise RuntimeError('Required compiled PlazaInstanceTools Nanite builder is absent; import not started')
    report_path = c.ROOT / 'Receipts/import.json'
    report = dict(revision=revision, stage='preflight', tests_run=False,
                  rendered=False, game_run=False, random_pool_registered=False,
                  saved_assets=[], reused_materials={}, meshes={}, textures={})
    material_assets = {}
    plans = []
    texture_plans = {}
    role_plans = {}
    slots_used = set(role for o in manifest['objects'] for role in o['materials'].values())
    slots_used.update(scene.get('required_material_roles', []))

    def save(asset, fingerprint):
        c.require_owned(asset.get_path_name())
        c.stamp_asset(u, asset, fingerprint, revision)
        if not E.save_loaded_asset(asset, False):
            raise RuntimeError('Asset save failed: ' + asset.get_path_name())
        report['saved_assets'].append(asset.get_path_name())
        c.write(report_path, report)

    def role_name(role):
        return re.sub('[^A-Za-z0-9_]', '_', role)

    def import_task(path, source, options=None):
        c.require_owned(path)
        task = u.AssetImportTask()
        task.filename = str(source)
        task.destination_path, task.destination_name = path.rsplit('/', 1)
        task.automated = True
        task.replace_existing = False
        task.save = False
        if options is not None:
            task.options = options
            task.factory = u.FbxFactory()
        A.import_asset_tasks([task])
        obj = u.load_asset(path)
        if not obj:
            raise RuntimeError('Import did not create expected asset: ' + path)
        for imported in task.get_editor_property('imported_object_paths'):
            c.require_owned(imported)
        return obj

    try:
        # Resolve all external dependencies and all source files BEFORE writes.
        # A preview texture in the package never substitutes for a missing
        # user-approved UE material or furniture asset.
        native_containers, outline = containers.specifications(scene)
        c.assert_dependencies(u, [p for p in c.external_dependencies(scene, roles, slots_used) +
                              containers.asset_paths(native_containers, outline)
                              if not p.startswith(c.OWNED_BASE + '/')])
        for role in sorted(slots_used):
            spec = roles[role]
            if spec.get('existing_ue_path'):
                material = u.load_asset(spec['existing_ue_path'])
                if not isinstance(material, u.MaterialInterface):
                    raise RuntimeError('Required material is not a MaterialInterface: ' + spec['existing_ue_path'])
                base = material.get_base_material()
                needs_nanite = any(o.get('nanite') and role in o['materials'].values() for o in manifest['objects'])
                # Do not trigger auto-usage changes on shared parents. A missing
                # flag needs a separately approved shared-asset change.
                if needs_nanite and not base.get_editor_property('used_with_nanite'):
                    raise RuntimeError('Shared material lacks Nanite usage; no shared edit permitted: ' + base.get_path_name())
                material_assets[role] = material
                report['reused_materials'][role] = material.get_path_name()
                continue
            if spec.get('new_authored') is not True:
                raise RuntimeError('New material must be explicitly new_authored:true: ' + role)
            if not all(key in spec for key in ('basecolor_linear', 'roughness', 'metallic')):
                raise ValueError('New authored material requires explicit basecolor_linear/roughness/metallic: ' + role)
            texture_fingerprints = {}
            for channel, entry in spec.get('textures', {}).items():
                if channel not in ('basecolor', 'normal', 'orm', 'emissive', 'labeloverlay'):
                    raise ValueError('Unsupported authored texture channel: ' + channel)
                relative = entry if isinstance(entry, str) else entry['path']
                convention = entry.get('normal_convention') if isinstance(entry, dict) else None
                if channel == 'normal' and convention not in ('DirectX', 'OpenGL'):
                    raise ValueError('New normal texture needs explicit normal_convention DirectX/OpenGL: ' + role)
                source = c.source_file(relative)
                path = c.OWNED_BASE + '/Textures/T_Power_' + role_name(role) + '_' + channel
                fp = c.digest(dict(revision=revision, channel=channel,
                                   normal_convention=convention, sha256=c.file_digest(source)))
                texture_plans[(role, channel)] = dict(path=path, source=source, fingerprint=fp,
                    existing=c.matching_asset(u, path, fp, revision), channel=channel,
                    normal_convention=convention)
                texture_fingerprints[channel] = fp
            path = c.OWNED_BASE + '/Materials/M_Power_' + role_name(role)
            fp = c.digest(dict(revision=revision, role=spec, textures=texture_fingerprints, pipeline=1))
            role_plans[role] = dict(path=path, fingerprint=fp, spec=spec,
                                  existing=c.matching_asset(u, path, fp, revision))
        for item in manifest['objects']:
            source = c.source_file(item['fbx'])
            path = c.OWNED_BASE + '/Meshes/' + item['name']
            sha = c.file_digest(source)
            fp = c.digest(dict(revision=revision, source_sha256=sha,
                import_spec={k: item.get(k) for k in ('materials', 'nanite', 'collision',
                    'simple_collision_hulls', 'guardrail_drop')},
                roles={r: roles[r] for r in item['materials'].values()}, pipeline=1))
            plans.append(dict(item=item, source=source, path=path, source_sha256=sha,
                fingerprint=fp, existing=c.matching_asset(u, path, fp, revision)))
        # Only after the complete preflight can any package be created/saved.
        report['stage'] = 'importing'
        c.write(report_path, report)
        textures = {}
        for key, plan in texture_plans.items():
            texture = plan['existing']
            if not texture:
                texture = import_task(plan['path'], plan['source'])
                channel = plan['channel']
                texture.set_editor_property('srgb', channel in ('basecolor', 'emissive', 'labeloverlay'))
                texture.set_editor_property('never_stream', False)
                if channel == 'normal':
                    texture.set_editor_property('flip_green_channel', plan['normal_convention'] == 'OpenGL')
                texture.set_editor_property('compression_settings',
                    u.TextureCompressionSettings.TC_NORMALMAP if channel == 'normal' else
                    u.TextureCompressionSettings.TC_MASKS if channel == 'orm' else
                    u.TextureCompressionSettings.TC_BC7)
                save(texture, plan['fingerprint'])
            textures[key] = texture
            report['textures'][plan['path']] = dict(fingerprint=plan['fingerprint'], channel=plan['channel'])
        for role, plan in role_plans.items():
            material = plan['existing']
            if not material:
                path = plan['path']
                material = A.create_asset(path.rsplit('/', 1)[1], path.rsplit('/', 1)[0], u.Material, u.MaterialFactoryNew())
                if not material:
                    raise RuntimeError('Material creation failed: ' + path)
                material.set_editor_property('used_with_nanite', True)
                material.set_editor_property('used_with_instanced_static_meshes', True)
                spec = plan['spec']
                slab = L.create_material_expression(material, u.MaterialExpressionSubstrateShadingModels)
                slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)

                def connect(node, output, prop, pin):
                    L.connect_material_property(node, output, prop)
                    L.connect_material_expressions(node, output, slab, pin)

                def scalar(value):
                    node = L.create_material_expression(material, u.MaterialExpressionConstant)
                    node.set_editor_property('r', float(value))
                    return node

                def color(value):
                    node = L.create_material_expression(material, u.MaterialExpressionConstant3Vector)
                    node.set_editor_property('constant', u.LinearColor(*value[:3], 1))
                    return node

                def sample(channel):
                    texture = textures.get((role, channel))
                    if not texture:
                        return None
                    node = L.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D)
                    node.set_editor_property('parameter_name', channel)
                    node.set_editor_property('texture', texture)
                    sampler = (u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == 'normal' else
                               u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel == 'orm' else
                               u.MaterialSamplerType.SAMPLERTYPE_COLOR)
                    node.set_editor_property('sampler_type', sampler)
                    return node

                base = sample('basecolor') or color(spec['basecolor_linear'])
                base_output = 'RGB' if (role, 'basecolor') in textures else ''
                overlay = sample('labeloverlay')
                if overlay:
                    blend = L.create_material_expression(material, u.MaterialExpressionLinearInterpolate)
                    L.connect_material_expressions(base, base_output, blend, 'A')
                    L.connect_material_expressions(overlay, 'RGB', blend, 'B')
                    L.connect_material_expressions(overlay, 'A', blend, 'Alpha')
                    base, base_output = blend, ''
                connect(base, base_output, u.MaterialProperty.MP_BASE_COLOR, 'BaseColor')
                orm = sample('orm')
                if orm:
                    connect(orm, 'G', u.MaterialProperty.MP_ROUGHNESS, 'Roughness')
                    connect(orm, 'B', u.MaterialProperty.MP_METALLIC, 'Metallic')
                    L.connect_material_property(orm, 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
                else:
                    connect(scalar(spec['roughness']), '', u.MaterialProperty.MP_ROUGHNESS, 'Roughness')
                    connect(scalar(spec['metallic']), '', u.MaterialProperty.MP_METALLIC, 'Metallic')
                normal = sample('normal')
                if normal:
                    normal_output='RGB'
                    if overlay:
                        flat=L.create_material_expression(material, u.MaterialExpressionLinearInterpolate)
                        L.connect_material_expressions(normal,'RGB',flat,'A')
                        L.connect_material_expressions(color([0,0,1]),'',flat,'B')
                        L.connect_material_expressions(overlay,'A',flat,'Alpha')
                        normal,normal_output=flat,''
                    connect(normal, normal_output, u.MaterialProperty.MP_NORMAL, 'Normal')
                strength = float(spec.get('emissive_strength', 0))
                if strength > 0:
                    if spec.get('emissive_from_basecolor'):
                        emitter, emitter_output=base,base_output
                    else:
                        emitter=sample('emissive') or color(spec.get('emissive_color_linear', spec['basecolor_linear']))
                        emitter_output='RGB' if (role, 'emissive') in textures else ''
                    multiply = L.create_material_expression(material, u.MaterialExpressionMultiply)
                    L.connect_material_expressions(emitter, emitter_output, multiply, 'A')
                    L.connect_material_expressions(scalar(strength), '', multiply, 'B')
                    connect(multiply, '', u.MaterialProperty.MP_EMISSIVE_COLOR, 'EmissiveColor')
                L.connect_material_property(slab, '', u.MaterialProperty.MP_FRONT_MATERIAL)
                errors = L.recompile_material(material)
                if errors:
                    raise RuntimeError('Material compilation failed: ' + str(errors))
                L.layout_material_expressions(material)
                save(material, plan['fingerprint'])
            material_assets[role] = material
        for plan in plans:
            item = plan['item']
            mesh = plan['existing']
            if not mesh:
                options = u.FbxImportUI()
                options.import_mesh = True
                options.import_materials = False
                options.import_textures = False
                options.import_as_skeletal = False
                options.automated_import_should_detect_type = False
                options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
                data = options.static_mesh_import_data
                data.combine_meshes = True
                data.convert_scene = True
                data.convert_scene_unit = True
                data.transform_vertex_to_absolute = True
                data.auto_generate_collision = False
                data.generate_lightmap_u_vs = False
                data.one_convex_hull_per_ucx = True
                data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
                data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
                data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
                mesh = import_task(plan['path'], plan['source'], options)
                if not isinstance(mesh, u.StaticMesh):
                    raise RuntimeError('FBX did not create a StaticMesh: ' + plan['path'])
                for index, slot in enumerate(mesh.get_editor_property('static_materials')):
                    name = re.sub(r'[._][0-9]{3}$', '', str(slot.material_slot_name))
                    if name not in item['materials']:
                        raise RuntimeError('Unexpected material slot in ' + item['name'] + ': ' + name)
                    mesh.set_material(index, material_assets[item['materials'][name]])
                build = S.get_lod_build_settings(mesh, 0)
                build.set_editor_property('use_full_precision_u_vs', True)
                build.set_editor_property('use_high_precision_tangent_basis', True)
                build.set_editor_property('recompute_tangents', True)
                S.set_lod_build_settings(mesh, 0, build)
                body = mesh.get_editor_property('body_setup')
                if item.get('collision'):
                    count = S.get_convex_collision_count(mesh)
                    if count != item['simple_collision_hulls']:
                        raise RuntimeError('UCX hull count differs for %s: expected %s, got %s' %
                            (item['name'], item['simple_collision_hulls'], count))
                    body.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
                settings = mesh.get_editor_property('nanite_settings').copy()
                settings.enabled = bool(item.get('nanite', False))
                settings.explicit_tangents = True
                settings.generate_fallback = u.NaniteGenerateFallback.ENABLED
                settings.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES
                settings.fallback_percent_triangles = 1.0
                settings.fallback_relative_error = 0.0
                mesh.set_editor_property('nanite_settings', settings)
                if settings.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):
                    raise RuntimeError('Nanite build failed: ' + plan['path'])
                save(mesh, plan['fingerprint'])
            report['meshes'][item['name']] = dict(path=plan['path'], source_sha256=plan['source_sha256'],
                fingerprint=plan['fingerprint'], source_triangles=item['triangles'], collision=item['collision'],
                simple_collision_hulls=item.get('simple_collision_hulls', 0), nanite=bool(item.get('nanite')))
            c.write(report_path, report)
        report.update(stage='assets_saved', material_paths={k: v.get_path_name() for k, v in material_assets.items()},
                      source_manifest_sha256=c.file_digest(c.ROOT / 'Authored/manifest.json'),
                      source_materials_sha256=c.file_digest(c.ROOT / 'Config/materials.json'))
        c.write(report_path, report)
        u.log('POWER_THEME_ASSETS_SAVED ' + revision)
    except Exception:
        report.update(stage='import_failed', error=traceback.format_exc())
        c.write(report_path, report)
        raise


if __name__ == '__main__':
    main()
