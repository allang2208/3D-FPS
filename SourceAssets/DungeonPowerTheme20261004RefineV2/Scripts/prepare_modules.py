"""Write review-only AuthoredDungeonGenerator descriptors, never activate them.

Pure file authoring. Does not import Unreal, save .uassets, edit the production
catalog or call Generate. The hard-reference list is an integration plan, not
proof that a generator's ModuleAssets has been saved.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_common as c
import container_bridge as containers


def main():
    scene, manifest, roles = c.load_inputs()
    sections = scene['rooms'] + scene.get('connectors', [])
    native_containers, outline = containers.specifications(scene)
    reuse = list(c.existing_specs(scene))
    authored = list(c.existing_specs(scene, authored=True))
    meshes = {c.OWNED_BASE + '/Meshes/' + o['name']: o for o in manifest['objects']}
    used_roles = {role for item in manifest['objects'] for role in item['materials'].values()}
    used_roles.update(scene.get('required_material_roles', []))
    material_paths = {role: spec.get('existing_ue_path') or
                      c.OWNED_BASE + '/Materials/M_Power_' + role for role, spec in roles.items()
                      if role in used_roles}
    modules = []
    required_assets = set(c.external_dependencies(scene, roles, used_roles))
    required_assets.update(containers.asset_paths(native_containers, outline))
    required_assets.update(material_paths.values())

    def part(path, position_m, spec):
        required_assets.add(path)
        result = dict(mesh=path, position=c.vector_m(position_m), yaw=-float(spec.get('yaw_deg', 0)),
            scale=spec.get('scale', [1, 1, 1]), collision=bool(spec.get('collision', True)),
            cast_shadow=bool(spec.get('cast_shadow', True)))
        if spec.get('guardrail_drop'):
            result['guardrail_drop'] = True
        overrides = spec.get('materials', spec.get('material_overrides', [])) or []
        if overrides:
            if not isinstance(overrides, list):
                raise ValueError('Draft generator overrides must be a slot-ordered list; resolve the exact source slots first')
            result['materials'] = overrides
            required_assets.update(p for p in overrides if p)
        return result

    for section in sections:
        is_room = section['id'] in {r['id'] for r in scene['rooms']}
        cells = [c.cell_m(box) for box in section['cells_m']]
        minimum = [min(box['min'][i] for box in cells) for i in range(3)]
        maximum = [max(box['max'][i] for box in cells) for i in range(3)]
        ports = section.get('ports')
        if not ports:
            if is_room:
                raise ValueError('Room needs exact authored ports: ' + section['id'])
            length, width, _ = section['dimensions_m']
            ports = [dict(id='Entry', position=[-length / 2, 0, 0], normal=[-1, 0, 0], width=width, height=2.8),
                     dict(id='Exit', position=[length / 2, 0, 0], normal=[1, 0, 0], width=width, height=2.8)]
        converted_ports = [dict(id=p['id'], position=c.vector_m(p['position']), normal=c.direction(p['normal']),
                                width=p['width'] * 100, height=p['height'] * 100) for p in ports]
        parts = []
        for path, item in meshes.items():
            if item['room_id'] != section['id'] or item.get('prototype') or item.get('place_in_map') is False:
                continue
            position = item.get('placement_m', c.origin(section))
            local = [position[i] - c.origin(section)[i] for i in range(3)]
            parts.append(part(path, local, {k: item[k] for k in
                ('collision', 'guardrail_drop', 'cast_shadow') if k in item}))
        for parent, spec in reuse + authored:
            if parent['id'] != section['id']:
                continue
            if spec.get('container_id'):
                continue
            if spec['mesh'].startswith(c.OWNED_BASE + '/') and spec['mesh'] not in meshes:
                raise ValueError('Authored placement references a mesh outside manifest: ' + spec['mesh'])
            parts.append(part(spec['mesh'], spec['position_m'], spec))
        lights = []
        for raw in section.get('lights', []):
            light = c.light_spec(raw)
            # Native optimized generator multiplies spot intensity by this
            # cone factor. Undo it here to preserve the subject's real lumens.
            if light['type'] == 'spot':
                if raw.get('pitch_deg', -90) != -90 or raw.get('yaw_deg', 0) != 0:
                    raise ValueError('Current generator supports downward spotlights only; keep custom rotations subject-only')
                outer = max(10, min(85, light.get('outer_cone_degrees', 65)))
                light['intensity'] /= .5 * (1 - math.cos(math.radians(outer)))
                light.pop('yaw', None)
            light['optimized_radius_cm'] = light['radius']
            lights.append(light)
        anchor_role = section.get('encounter_role', 'power_combat')
        anchors = []
        for raw in section.get('encounter_anchors_m', []):
            if isinstance(raw, dict):
                anchors.append(dict(position=c.vector_m(raw['position_m']), role=raw.get('role', anchor_role)))
            else:
                anchors.append(dict(position=c.vector_m(raw), role=anchor_role))
        runtime = [spec for parent, _, spec in native_containers if parent['id'] == section['id']]
        modules.append(dict(id=section['id'], family_id=section['id'],
            role='room' if is_room else 'corridor', revision=scene['revision'],
            min=minimum, max=maximum, cells=cells, ports=converted_ports, port_pairs=[[0, 1]],
            parts=parts, lights=lights, anchors=anchors, props=[], runtime_actors=runtime,
            runtime_assets=containers.asset_paths(
                [(parent, name, spec) for parent, name, spec in native_containers if parent['id'] == section['id']],
                outline if runtime else None),
            walk_mask=[c.cell_m(box) for box in section.get('walk_mask_m', section['cells_m'])],
            selection=dict(chance_per_run=0.0, max_per_run=1), authoring_only=True,
            route_intent=dict(registration='pending_explicit_user_acceptance',
                              fixed_theme_order=scene.get('sequence', [r['id'] for r in scene['rooms']]))))
    draft = dict(revision=scene['revision'], status='draft_only_not_registered',
        schema_source='Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp',
        coordinate_space='UE centimetres, local to each module',
        modules=modules, proposed_sequence=scene.get('sequence', [r['id'] for r in scene['rooms']]),
        subject_placements=[dict(id=s['id'], position=c.vector_m(c.origin(s)), yaw=0) for s in sections],
        module_asset_paths=sorted(required_assets), hard_references_saved=False,
        runtime_activation=False, preview_caps_included=False,
        required_container_outline=outline, container_rewards_deferred=True,
        navigation_and_spawn_configuration='pending accepted production integration; no enemies spawned')
    import text_card_revision
    draft = text_card_revision.remap_draft(draft)
    import upper_control_revision
    draft = upper_control_revision.remap_draft(draft)
    import server_container_revision
    draft = server_container_revision.remap_draft(draft)
    import runpy
    treasure = runpy.run_path(str(c.PROJECT / 'SourceAssets/ThemeThirdRoomTreasure20261007/treasure.py'))
    draft = treasure['extend'](draft)
    c.write(c.ROOT / 'Config/module-drafts.json', draft)
    c.write(c.ROOT / 'Docs/required-assets.json', dict(revision=scene['revision'],
        external_required=sorted(set(c.external_dependencies(scene, roles, used_roles)) |
                                 set(containers.asset_paths(native_containers, outline))),
        authored_required=sorted(p for p in required_assets if p.startswith(c.OWNED_BASE + '/')),
        verified_in_target_unreal=False, authoring_only=True))
    print('POWER_THEME_DRAFT_MODULES_WRITTEN; production catalog unchanged')


if __name__ == '__main__':
    main()
