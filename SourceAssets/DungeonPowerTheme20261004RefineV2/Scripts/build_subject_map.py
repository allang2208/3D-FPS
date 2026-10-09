"""Future authorized commandlet: assemble a static independent subject map.

No runtime generator, production-map edits, monster spawning, default-map/cook
changes, PIE, rendering or tests. All dependencies resolve before world creation.
"""
import math
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
    receipt_path = c.ROOT / 'Receipts/subject-map.json'
    imported = c.read(c.ROOT / 'Receipts/import.json')
    if (imported.get('stage') != 'assets_saved' or imported.get('revision') != revision or
            imported.get('source_manifest_sha256') != c.file_digest(c.ROOT / 'Authored/manifest.json') or
            imported.get('source_materials_sha256') != c.file_digest(c.ROOT / 'Config/materials.json')):
        raise RuntimeError('Current matching asset import receipt is required; no map was created')
    native_containers, outline = containers.specifications(scene)
    used_roles = {role for item in manifest['objects'] for role in item['materials'].values()}
    used_roles.update(scene.get('required_material_roles', []))
    fingerprint = c.digest(dict(scene=scene, manifest=manifest, material_roles=roles,
        containers=[spec for _, _, spec in native_containers], outline=outline,
        meshes=imported['meshes'], map_pipeline=2))
    E = u.EditorAssetLibrary
    map_disk = c.PROJECT / 'Content' / (c.SUBJECT_MAP.removeprefix('/Game/') + '.umap')
    if map_disk.exists() and not E.does_asset_exist(c.SUBJECT_MAP):
        raise RuntimeError('Unregistered existing map file must be preserved: ' + str(map_disk))
    if E.does_asset_exist(c.SUBJECT_MAP):
        old = u.load_asset(c.SUBJECT_MAP)
        matches = old and all(E.get_metadata_tag(old, c.OWNER + '.' + k) == v for k, v in
            {'Owner': c.OWNER, 'Revision': revision, 'Fingerprint': fingerprint}.items())
        if matches and receipt_path.exists() and c.read(receipt_path).get('stage') == 'map_saved':
            u.log('POWER_THEME_SUBJECT_ALREADY_SAVED ' + c.SUBJECT_MAP)
            return
        raise RuntimeError('Existing subject map differs or lacks ownership. No overwrite/delete is permitted: ' + c.SUBJECT_MAP)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    if actors is None:
        actors = u.new_object(u.EditorActorSubsystem)
    sections = scene['rooms'] + scene.get('connectors', [])
    by_id = {s['id']: s for s in sections}
    reused = list(c.existing_specs(scene))
    authored = list(c.existing_specs(scene, authored=True))
    paths = set(c.external_dependencies(scene, roles, used_roles))
    paths.update(containers.asset_paths(native_containers, outline))
    paths.update(c.OWNED_BASE + '/Meshes/' + o['name'] for o in manifest['objects'])
    paths.update(p['mesh'] for _, p in authored)
    preview_caps = bool(scene.get('preview_port_caps', False))
    cap_material = scene.get('preview_cap_material', '/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete')
    if preview_caps:
        paths.update(['/Engine/BasicShapes/Cube', cap_material])
    c.assert_dependencies(u, sorted(paths))
    game_mode = u.load_class(None, '/Script/FPSGAME.FPSGAMEGameMode')
    if not game_mode:
        raise RuntimeError('Compiled normal FPSGAMEGameMode is missing')
    if native_containers and (not hasattr(u, 'ColdSteelSceneContainer') or not hasattr(u, 'ColdSteelContainerMotion')):
        raise RuntimeError('Required compiled native scene-container class/enum is missing')
    # Never trust a receipt as evidence that another revision of a mesh matches.
    for item in manifest['objects']:
        record = imported['meshes'].get(item['name'])
        if not record or c.file_digest(c.source_file(item['fbx'])) != record['source_sha256']:
            raise RuntimeError('Authored FBX changed after import: ' + item['name'])
        c.matching_asset(u, record['path'], record['fingerprint'], revision)
    lights = [(section, raw, c.light_spec(raw)) for section in sections for raw in section.get('lights', [])]
    budget = scene.get('lighting_budget', {})
    if len(lights) > budget.get('max_total_lights', 32):
        raise RuntimeError('Authored local-light count exceeds the explicit subject budget')
    if sum(int(s['cast_shadows']) for _, _, s in lights) > budget.get('max_shadowed_lights', 8):
        raise RuntimeError('Shadowed local-light count exceeds the explicit subject budget')
    for section in sections:
        if sum(int(s['cast_shadows']) for room, _, s in lights if room['id'] == section['id']) > budget.get('max_shadowed_per_section', 3):
            raise RuntimeError('Shadowed-light budget exceeded in ' + section['id'])
    report = dict(stage='assembling', map=c.SUBJECT_MAP, revision=revision, fingerprint=fingerprint,
        tests_run=False, rendered=False, game_run=False, editor_opened=False, generated=False,
        random_pool_registered=False, monster_spawning=False, runtime_generator=False,
        navigation='not authored; subject movement only', reused_assets=sorted(paths -
            {p for p in paths if p.startswith(c.OWNED_BASE + '/')}),
        chinese_material_bindings=[],
        counts=dict(authored_mesh_actors=0, reused_mesh_actors=0, lights=0, guardrails=0, interactive_containers=0),
        lighting='Native finite draw/fade bounds; production room/portal scheduler is not active in this static map')

    def v(values):
        return u.Vector(*values)

    def spawn(cls, position, label, folder, yaw=0, pitch=0, extra=()):
        actor = actors.spawn_actor_from_class(cls, v(position), u.Rotator(pitch=pitch, yaw=yaw, roll=0))
        if not actor:
            raise RuntimeError('Actor creation failed: ' + label)
        actor.set_actor_label('PowerTheme_' + label)
        actor.set_folder_path('PowerTheme/' + folder)
        actor.set_editor_property('tags', [u.Name('PowerTheme.Subject'), *(u.Name(t) for t in extra)])
        return actor

    def mesh_actor(path, world_m, spec, label, folder, external=False):
        rail = bool(spec.get('guardrail_drop', False))
        tags = ['PowerTheme.Room.' + folder]
        if rail:
            tags.append('Traversal.GuardrailDrop')
        actor = spawn(u.StaticMeshActor, c.vector_m(world_m), label, folder,
                      yaw=-float(spec.get('yaw_deg', 0)), extra=tags)
        component = actor.static_mesh_component
        mesh = u.load_asset(path)
        component.set_mobility(u.ComponentMobility.STATIC)
        component.set_static_mesh(mesh)
        collidable = bool(spec.get('collision', True))
        if rail and not collidable:
            raise RuntimeError('Guardrail needs real query/blocking collision: ' + label)
        component.set_collision_profile_name('BlockAll' if collidable else 'NoCollision')
        component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if collidable else u.CollisionEnabled.NO_COLLISION)
        component.set_cast_shadow(bool(spec.get('cast_shadow', True)))
        component.set_editor_property('component_tags', [u.Name(t) for t in tags])
        actor.set_actor_scale3d(v(spec.get('scale', [1, 1, 1])))
        overrides = spec.get('materials', spec.get('material_overrides', [])) or []
        if isinstance(overrides, dict):
            for key, material in overrides.items():
                if not material:
                    continue
                index = int(key) if str(key).isdigit() else component.get_material_index(key)
                if index < 0:
                    raise RuntimeError('Unknown component material slot ' + str(key) + ' in ' + label)
                component.set_material(index, u.load_asset(material))
                if '/RefineV2/Materials/' in material:
                    actual = component.get_material(index).get_path_name()
                    report['chinese_material_bindings'].append(dict(actor=label, component='static_mesh', index=index, material=actual))
        else:
            for index, material in enumerate(overrides):
                if material:
                    component.set_material(index, u.load_asset(material))
                    if '/RefineV2/Materials/' in material:
                        actual = component.get_material(index).get_path_name()
                        report['chinese_material_bindings'].append(dict(actor=label, component='static_mesh', index=index, material=actual))
        report['counts']['reused_mesh_actors' if external else 'authored_mesh_actors'] += 1
        report['counts']['guardrails'] += int(rail)
        return actor

    try:
        # Optional template is strictly a named existing nav bounds volume. No
        # automatic production-map discovery and no navigation build are done.
        nav_template = None
        nav = scene.get('nav_template')
        if nav:
            source = u.EditorLoadingAndSavingUtils.load_map(nav['map'])
            if not source:
                raise RuntimeError('Named navigation source map is absent: ' + nav['map'])
            matches = [a for a in u.GameplayStatics.get_all_actors_of_class(source, u.NavMeshBoundsVolume)
                       if a.get_actor_label() == nav['actor_label']]
            if len(matches) != 1:
                raise RuntimeError('Named navigation template is missing or ambiguous')
            nav_template = matches[0]
            # Keep source object loaded while creating a blank destination.
        world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
        if not world:
            raise RuntimeError('New blank subject world could not be created')
        world.get_world_settings().set_editor_property('default_game_mode', game_mode)
        for item in manifest['objects']:
            if item.get('prototype') or item.get('place_in_map') is False:
                continue
            section = by_id[item['room_id']]
            mesh_actor(c.OWNED_BASE + '/Meshes/' + item['name'], item.get('placement_m', c.origin(section)),
                       {k: item[k] for k in ('collision', 'guardrail_drop', 'cast_shadow') if k in item},
                       item['name'], section['id'])
        for external, entries in ((True, reused), (False, authored)):
            for index, (section, spec) in enumerate(entries):
                if external and spec.get('container_id'):
                    continue  # Native container owns this exact body/moving mesh pair.
                mesh_actor(spec['mesh'], c.add(c.origin(section), spec['position_m']), spec,
                           spec.get('id', section['id'] + '_Part_' + str(index)), section['id'], external)
        for section, identity, spec in native_containers:
            native = containers.spawn(u, actors, spec, section, identity, u.load_asset)
            for key, component in (('body_materials', native.body), ('door_materials', native.door)):
                for index, material in enumerate(spec.get(key, [])):
                    if material:
                        actual = component.get_material(index).get_path_name()
                        if c.package_path(actual) != c.package_path(material):
                            raise RuntimeError('Container material binding failed: ' + identity)
                        report['chinese_material_bindings'].append(dict(actor=identity, component=key, index=index, material=actual))
            report['counts']['interactive_containers'] += 1
        if outline:
            containers.outline_volume(u, actors, outline, u.load_asset)
            report['container_outline'] = outline
        report['container_rewards_deferred'] = True
        for section, raw, spec in lights:
            spot = spec['type'] == 'spot'
            actor = spawn(u.SpotLight if spot else u.PointLight,
                c.add(c.vector_m(c.origin(section)), spec['position']),
                section['id'] + '_' + raw.get('id', 'Light' + str(report['counts']['lights'])), section['id'],
                yaw=-float(raw.get('yaw_deg', 0)), pitch=float(raw.get('pitch_deg', -90 if spot else 0)),
                extra=['DungeonLight.' + spec['role'], 'PowerTheme.Room.' + section['id']])
            component = actor.get_component_by_class(u.PointLightComponent)
            component.set_mobility(u.ComponentMobility.MOVABLE)
            component.set_editor_property('intensity_units', u.LightUnits.LUMENS)
            # Config lumens are actual authored spotlight/point-light lumens.
            # Draft catalog conversion accounts for the generator's cone factor.
            component.set_intensity(spec['intensity'])
            component.set_editor_property('attenuation_radius', spec['radius'])
            component.set_editor_property('cast_shadows', spec['cast_shadows'])
            component.set_editor_property('max_draw_distance', spec['max_draw_distance_cm'])
            component.set_editor_property('max_distance_fade_range', spec['fade_range_cm'])
            component.set_light_color(u.LinearColor(*spec.get('color', [1, 1, 1]), 1))
            for key, default in (('source_radius', 6), ('source_length', 0),
                                 ('indirect_lighting_intensity', 1), ('volumetric_scattering_intensity', .3)):
                component.set_editor_property(key, spec.get(key, default))
            if spot:
                outer = max(10, min(85, spec.get('outer_cone_degrees', 65)))
                component.set_editor_property('outer_cone_angle', outer)
                component.set_editor_property('inner_cone_angle', max(0, min(outer, spec.get('inner_cone_degrees', outer - 15))))
            report['counts']['lights'] += 1
        first = scene['rooms'][0]
        port = first['ports'][0]
        entry = c.add(c.origin(first), port['position'])
        normal = port['normal']
        player = scene.get('player_start_m', c.add(entry, [-normal[0] * 1.4, -normal[1] * 1.4, 1.05]))
        yaw = -float(scene['player_yaw_deg']) if 'player_yaw_deg' in scene else math.degrees(math.atan2(normal[1], -normal[0]))
        spawn(u.PlayerStart, c.vector_m(player), 'PlayerStart', 'PreviewOnly', yaw=yaw, extra=['PowerTheme.PreviewOnly'])
        report['player_start_m'] = player
        if preview_caps:
            for label, room, p in [('EntryCap', first, first['ports'][0]),
                                  ('ExitCap', scene['rooms'][-1], scene['rooms'][-1]['ports'][-1])]:
                position = c.add(c.origin(room), p['position'])
                position[2] += p['height'] * .5
                cap = mesh_actor('/Engine/BasicShapes/Cube', position,
                    dict(scale=[.18, p['width'], p['height']], yaw_deg=math.degrees(math.atan2(p['normal'][1], p['normal'][0])),
                         collision=True, materials=[cap_material]), label, 'PreviewOnly')
                cap.set_editor_property('tags', [u.Name('PowerTheme.Subject'), u.Name('PowerTheme.PreviewOnly')])
        if nav_template:
            # Only a valid loaded template is duplicated. If new_blank_map has
            # invalidated it, duplication fails and the target is never saved.
            duplicate = actors.duplicate_actor(nav_template, world, v([0, 0, 0]))
            if not duplicate:
                raise RuntimeError('Navigation template could not be safely copied; map not saved')
            duplicate.set_actor_label('PowerTheme_NavBounds')
            duplicate.set_actor_location(v(c.vector_m(nav['position_m'])), False, False)
            duplicate.set_actor_scale3d(v(nav['scale']))
            report['navigation'] = 'Existing named bounds copied; navigation data not built or tested'
        # Optional fixed exposure is local to the new map, not the day/night map.
        if scene.get('exposure') or scene.get('postprocess'):
            exposure = scene.get('exposure', scene.get('postprocess'))
            ev = exposure.get('ev100', exposure.get('exposure_ev', .7))
            actor = spawn(u.PostProcessVolume, [0, 0, 0], 'Exposure', 'Environment')
            actor.set_editor_property('unbound', True)
            settings = actor.get_editor_property('settings')
            for key, value in [('auto_exposure_min_brightness', ev),
                               ('auto_exposure_max_brightness', ev),
                               ('auto_exposure_bias', exposure.get('bias', exposure.get('exposure_bias', 0))),
                               ('indirect_lighting_intensity', exposure.get('indirect_intensity', 1)),
                               ('vignette_intensity', exposure.get('vignette', .25)),
                               ('bloom_intensity', exposure.get('bloom', .2))]:
                settings.set_editor_property('override_' + key, True)
                settings.set_editor_property(key, value)
            actor.set_editor_property('settings', settings)
        import text_card_revision
        report['text_card_revision_actors'] = text_card_revision.patch_world()
        import upper_control_revision
        report['upper_control_revision'] = upper_control_revision.patch_world()
        import server_container_revision
        report['server_container_revision'] = server_container_revision.patch_world()
        import runpy
        treasure = runpy.run_path(str(c.PROJECT / 'SourceAssets/ThemeThirdRoomTreasure20261007/treasure.py'))
        room = by_id['AccumulatorControl']
        treasure['spawn_subject'](actors, u.load_asset, treasure['spec'](room['id']),
            dict(id=room['id'], position=c.vector_m(c.origin(room)), yaw=0),
            c.SUBJECT_MAP, 'PowerTheme.Subject')
        for key, value in [('Owner', c.OWNER), ('Revision', revision), ('Fingerprint', fingerprint)]:
            E.set_metadata_tag(world, c.OWNER + '.' + key, value)
        # Save exactly one newly owned map after every requested actor exists.
        if not u.EditorLoadingAndSavingUtils.save_map(world, c.SUBJECT_MAP):
            raise RuntimeError('Subject map save failed')
        report['component_material_bindings'] = list(report['chinese_material_bindings'])
        report['chinese_material_bindings'] = [b for b in report['component_material_bindings'] if b['material'].startswith(c.OWNED_BASE + '/Materials/')]
        report.update(stage='map_saved', return_map=c.RETURN_MAP,
                      console_command='open ' + c.SUBJECT_MAP)
        c.write(receipt_path, report)
        u.log('POWER_THEME_CHINESE_MATERIAL_BINDINGS ' + str(len(report['chinese_material_bindings'])))
        u.log('POWER_THEME_SUBJECT_SAVED ' + c.SUBJECT_MAP)
    except Exception:
        report.update(stage='map_authoring_failed', error=traceback.format_exc())
        c.write(receipt_path, report)
        raise


if __name__ == '__main__':
    main()
