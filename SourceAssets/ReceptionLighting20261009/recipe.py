"""Bind reception lights to their existing diffuser faces. Geometry stays authored."""
from pathlib import Path
import copy
import json

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
REVISION = 'reception_fixture_downlight_20261009'
MODULE_ID = 'FacilityReceptionHall'
# The diffuser is centered at anchor Z + 14.4 cm and is 1.2 cm thick.
# Put the emitter 1 cm below its underside; leave the mesh and fault masks fixed.
EMITTER_OFFSET_CM = 12.8
MAIN_RADIUS_CM = 2000.
COVERAGE_REVISION = 'reception_atrium_floor_coverage_20261009'


def apply_coverage(module):
    """Extend the open-atrium downlights; gallery lights remain local to their floor."""
    rows = []
    for light in module['lights']:
        if not light.get('id', '').startswith('Atrium_'):
            continue
        before = copy.deepcopy(light)
        light.update(radius=MAIN_RADIUS_CM, optimized_radius_cm=MAIN_RADIUS_CM,
                     coverage_revision=COVERAGE_REVISION)
        # Wider reach must respect the gallery slab and enclosing walls.
        # Only the formerly unshadowed, lit center fixture adds a shadow light.
        if light['intensity'] > 0:
            light['cast_shadows'] = True
        rows.append(dict(id=light['id'], before=before, after=copy.deepcopy(light)))
    module['coverage_revision'] = COVERAGE_REVISION
    return rows


def apply_subject_coverage(light):
    light.set_attenuation_radius(MAIN_RADIUS_CM)
    if light.intensity > 0:
        light.set_cast_shadows(True)


def layout():
    return json.loads((PROJECT / 'SourceAssets/DungeonReceptionHall20261006/Config/layout.json').read_text('utf8'))


def anchor(light):
    x, y, z = light['position_m']
    return [x * 100, -y * 100, z * 100]


def apply_module(module):
    """Update only fixture-bound light fields; keep current night-entry overrides."""
    if module['id'] != MODULE_ID:
        return []
    authored = layout()['lights']
    original_lights = [p for p in module['lights'] if p.get('ground_continuity_revision') != 'reception_ground_continuity_20261010']
    if len(original_lights) != len(authored):
        raise RuntimeError('Reception lamp count changed; inspect the new fixtures first')
    changes = []
    used = set()
    for light in original_lights:
        original = copy.deepcopy(light)
        pos = light.get('fixture_anchor_cm', light['position'])
        matches = [p for p in authored if all(abs(a-b) < .05 for a,b in zip(anchor(p), pos))]
        if len(matches) != 1 or matches[0]['id'] in used:
            raise RuntimeError('Unmatched or duplicate reception fixture: ' + str(pos))
        p = matches[0]
        used.add(p['id'])
        local = p['role'] != 'main'
        # Point lumens use 4*pi, while rectangular lights use pi. Preserve the
        # original downward central brightness rather than quadrupling it.
        if local and light.get('type', 'point') == 'point':
            light['intensity'] *= .25
        elif local and light.get('type') != 'rect':
            raise RuntimeError('Unexpected local reception light type')
        light.update(id=p['id'], fixture_anchor_cm=anchor(p),
            position=[pos[0], pos[1], pos[2] + EMITTER_OFFSET_CM],
            fixture_lighting_revision=REVISION, pitch=-90)
        if local:
            light.update(type='rect', yaw=0, roll=90,
                source_width_cm=123., source_height_cm=32.)
        else:
            # A spot's default vertical source segment can protrude through its
            # housing. Its emitter is just below the glass and points down.
            light.update(source_radius=1., source_length=0.)
            light.pop('yaw', None)  # Legacy spot assembler resets pitch on yaw.
        changes.append(dict(id=p['id'], before=original, after=copy.deepcopy(light)))
    module['fixture_lighting_revision'] = REVISION
    apply_coverage(module)
    for change, light in zip(changes, original_lights):
        change['after'] = copy.deepcopy(light)
    return changes


def installed():
    receipt = ROOT / 'Receipts/install.json'
    return receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage') == 'maps_saved'


def reapply_catalog(catalog, contract_hash):
    if not installed():
        return catalog
    result = copy.deepcopy(catalog)
    module = next(m for m in result['modules'] if m['id'] == MODULE_ID)
    apply_module(module)
    bank = result['facility_flow']['layout_bank']
    bank['contract_sha1'] = contract_hash(result)
    return result


def apply_subject():
    """Patch the existing reception subject only; the caller owns map saving."""
    import unreal as u
    aa = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    by_label = {a.get_actor_label(): a for a in aa.get_all_level_actors()}
    result = []
    for p in layout()['lights']:
        label = 'Reception_' + p['id']
        old = by_label.get(label)
        if not old:
            continue
        light = old.get_component_by_class(u.LocalLightComponent)
        if not light:
            raise RuntimeError('Reception fixture label has no light: ' + label)
        pos = anchor(p)
        location = u.Vector(pos[0], pos[1], pos[2] + EMITTER_OFFSET_CM)
        local = p['role'] != 'main'
        rotation = u.Rotator(pitch=-90, yaw=0, roll=90 if local else 0)
        actor = old
        if local and not isinstance(light, u.RectLightComponent):
            actor = aa.spawn_actor_from_class(u.RectLight, location, rotation)
            if not actor:
                raise RuntimeError('Could not replace reception light: ' + label)
            actor.set_actor_label(label + '_Downlight')
            actor.set_folder_path(old.get_folder_path())
            actor.set_editor_property('tags', list(old.tags))
            light = actor.get_component_by_class(u.RectLightComponent)
        actor.modify(); light.modify()
        actor.set_actor_location(location, False, False)
        actor.set_actor_rotation(rotation, True)
        light.set_mobility(u.ComponentMobility.MOVABLE)
        light.set_editor_property('intensity_units', u.LightUnits.LUMENS)
        light.set_intensity(p['intensity'] * (.25 if local else 1.))
        light.set_light_color(u.LinearColor(*p['color'], 1))
        light.set_cast_shadows(p['cast_shadows'])
        for key, value in dict(attenuation_radius=p['radius']*100,
            max_draw_distance=p['max_draw_distance_cm'], max_distance_fade_range=p['fade_range_cm'],
            indirect_lighting_intensity=p['indirect_lighting_intensity'],
            volumetric_scattering_intensity=p['volumetric_scattering_intensity']).items():
            light.set_editor_property(key, value)
        material = u.load_asset(p['light_function']) if p.get('light_function') else None
        if p.get('light_function') and not material:
            raise RuntimeError('Missing reception fault material')
        light.set_light_function_material(material)
        if material:
            light.set_editor_property('light_function_fade_distance', p['light_function_fade_distance'])
        if local:
            light.set_editor_property('source_width', 123.)
            light.set_editor_property('source_height', 32.)
        else:
            light.set_editor_property('source_radius', 1.)
            light.set_editor_property('source_length', 0.)
            apply_subject_coverage(light)
        if actor != old:
            if not aa.destroy_actor(old):
                raise RuntimeError('Old reception light could not be removed')
            actor.set_actor_label(label)
        result.append(dict(id=p['id'], type=light.get_class().get_name(),
            position=[location.x, location.y, location.z],
            forward=[light.get_forward_vector().x, light.get_forward_vector().y, light.get_forward_vector().z]))
    ground_recipe = PROJECT / 'SourceAssets/ReceptionGroundLighting20261009/recipe.py'
    if ground_recipe.exists():
        import runpy
        ground = runpy.run_path(str(ground_recipe))
        if ground['installed']():
            result.extend(ground['apply_subject'](u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()))
    finish_recipe = PROJECT / 'SourceAssets/ReceptionFinish20261010/recipe.py'
    if finish_recipe.exists():
        import runpy
        finish = runpy.run_path(str(finish_recipe))
        if finish['installed']():
            finish['apply_subject'](u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world())
    return result
