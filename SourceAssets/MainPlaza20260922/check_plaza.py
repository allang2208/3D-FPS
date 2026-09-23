"""Read-only structural read-back of plaza v2.

Reports grounding of the pavilion / fountain / altar, the plaza extent, samples of every
generated prop type, and verifies that each of the eight gateways is actually clear of
balusters and rails. No edits, no save, no PIE.
"""
import json
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
TAG = 'ColdSteel.MainPlaza'
TAG_GEN = TAG + '.Generated'
CX, CY = 1350.0, -975.0

# (name, axis of the side, fixed perpendicular coord, gate centre along the side, half width)
GATES = [
    ('outer_N', 'x', CY + 4900.0, CX, 300.0),
    ('outer_S', 'x', CY - 4900.0, CX, 300.0),
    ('outer_W', 'y', CX - 4900.0, CY, 300.0),
    ('outer_E', 'y', CX + 4900.0, CY, 300.0),
    ('precinct_W', 'y', CX - 900.0, CY, 200.0),
    ('precinct_E', 'y', CX + 900.0, CY, 200.0),
    ('precinct_N', 'x', CY + 1200.0, CX, 300.0),
    ('precinct_S', 'x', CY - 1200.0, CX, 300.0),
]

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def box(actor):
    center, extent = actor.get_actor_bounds(False)
    return dict(min_z=round(center.z - extent.z, 1), max_z=round(center.z + extent.z, 1),
                center=vec(center), extent=vec(extent))


def run():
    actors = api.get_all_level_actors()
    out = dict(actor_total=len(actors))

    gen = [a for a in actors if TAG_GEN in [str(t) for t in a.tags]]
    if gen:
        out['generated'] = len(gen)
        out['generated_extent_cm'] = dict(
            x=[round(min(a.get_actor_location().x for a in gen), 1),
               round(max(a.get_actor_location().x for a in gen), 1)],
            y=[round(min(a.get_actor_location().y for a in gen), 1),
               round(max(a.get_actor_location().y for a in gen), 1)])

    pav = [a for a in actors if a.get_actor_label().startswith('RomanPavilion2_')]
    if pav:
        out['pavilion'] = dict(actors=len(pav),
                               min_z=round(min(a.get_actor_bounds(False)[0].z -
                                               a.get_actor_bounds(False)[1].z for a in pav), 1),
                               max_z=round(max(a.get_actor_bounds(False)[0].z +
                                               a.get_actor_bounds(False)[1].z for a in pav), 1))

    for label, key in (('RomanFountain1', 'fountain'), ('Expedition_SquareAltar', 'altar')):
        a = next((x for x in actors if x.get_actor_label() == label), None)
        if a:
            out[key] = box(a)

    samples = {}
    for a in gen:
        tags = [str(t) for t in a.tags]
        for kind, tag in (('paving', TAG + '.Paving'), ('colonnade', TAG + '.Colonnade'),
                          ('entablature', TAG + '.Entablature'),
                          ('balustrade', TAG + '.Balustrade'),
                          ('precinct', TAG + '.Precinct')):
            if tag in tags and kind not in samples:
                samples[kind] = dict(label=a.get_actor_label(), box=box(a),
                                     scale=vec(a.get_actor_scale3d()))
    out['samples'] = samples

    # Gateways must be free of balusters and rails.
    violations = []
    checked = 0
    for a in actors:
        tags = [str(t) for t in a.tags]
        if TAG_GEN not in tags:
            continue
        if not (TAG + '.Balustrade' in tags or TAG + '.Precinct' in tags):
            continue
        checked += 1
        p = a.get_actor_location()
        for name, axis, fixed, centre, half in GATES:
            if axis == 'x':
                if abs(p.y - fixed) < 60.0 and abs(p.x - centre) < half:
                    violations.append(dict(actor=a.get_actor_label(), gate=name, loc=vec(p)))
            else:
                if abs(p.x - fixed) < 60.0 and abs(p.y - centre) < half:
                    violations.append(dict(actor=a.get_actor_label(), gate=name, loc=vec(p)))
    out['gate_check'] = dict(examined=checked, violations=violations)
    return out


try:
    result = run()
    (HERE / 'plaza_readback.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                              encoding='utf-8')
    print('READBACK_OK actors=%d generated=%s pavilion_min_z=%s fountain=%s..%s altar_min_z=%s'
          % (result['actor_total'], result.get('generated'),
             result.get('pavilion', {}).get('min_z'),
             result.get('fountain', {}).get('min_z'), result.get('fountain', {}).get('max_z'),
             result.get('altar', {}).get('min_z')))
    print('GATE_CHECK examined=%d violations=%d'
          % (result['gate_check']['examined'], len(result['gate_check']['violations'])))
    for s, row in result['samples'].items():
        print('  %-12s %-24s z=%s..%s scale=%s' % (s, row['label'], row['box']['min_z'],
                                                   row['box']['max_z'], row['scale']))
except Exception:
    (HERE / 'plaza_readback_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('READBACK_FAILED')
    raise
