"""Read back the wildlife assets and write an evidence report. No gameplay is started."""
import json
from pathlib import Path

import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / 'SourceAssets/Wildlife20261022'
DEST_ROOT = '/Game/Monsters/Wildlife'
SPECIES = [('deer_doe', 'DeerDoe'), ('deer_stag', 'DeerStag'), ('boar', 'Pig'),
           ('fox', 'Fox'), ('crow', 'Crow')]
lib = u.EditorAssetLibrary

report = {'version': 1, 'read_back': True, 'species': [], 'problems': []}
for species_id, asset in SPECIES:
    folder = DEST_ROOT + '/' + asset
    entry = {'id': species_id, 'folder': folder}
    da_path = folder + '/DA_WL_' + asset + '_AnimationSet'
    dataset = u.load_asset(da_path)
    if dataset is None:
        report['problems'].append('missing dataset ' + da_path)
        continue
    actions = dataset.get_editor_property('actions')
    sequences = []
    for key in actions.keys():
        action = actions[key]
        seq = action.get_editor_property('sequence')
        sequences.append({
            'slot': str(key),
            'clip': seq.get_path_name() if seq else None,
            'seconds': round(seq.get_play_length(), 4) if seq else 0.0,
            'loop': action.get_editor_property('loop'),
        })
    mesh = dataset.get_editor_property('reference_mesh')
    entry.update({
        'dataset': da_path,
        'slot_count': len(actions),
        'reference_mesh': mesh.get_path_name() if mesh else None,
        'walk_speed': dataset.get_editor_property('walk_speed'),
        'run_speed': dataset.get_editor_property('run_speed'),
        'slots': sequences,
    })
    if not mesh:
        report['problems'].append('no reference mesh on ' + da_path)
    empty = [row['slot'] for row in sequences if not row['clip'] or row['seconds'] <= 0.0]
    if empty:
        report['problems'].append('%s empty clips: %s' % (species_id, ','.join(empty)))

    bp_path = folder + '/BP_WL_' + asset
    blueprint = u.load_asset(bp_path)
    if blueprint is None:
        report['problems'].append('missing blueprint ' + bp_path)
    else:
        cls = blueprint.generated_class()
        cdo = u.get_default_object(cls)
        capsule = cdo.get_editor_property('capsule_component')
        bp_anim = cdo.get_editor_property('animation_set')
        bp_mesh = cdo.get_editor_property('mesh').get_skeletal_mesh_asset()
        entry['blueprint'] = {
            'path': bp_path,
            'class': cls.get_path_name(),
            'species_id': cdo.get_editor_property('species_id'),
            'animation_set': bp_anim.get_path_name() if bp_anim else None,
            'mesh': bp_mesh.get_path_name() if bp_mesh else None,
            'capsule_radius': capsule.get_editor_property('capsule_radius'),
            'capsule_half_height': capsule.get_editor_property('capsule_half_height'),
            'is_animal': isinstance(cdo, u.ColdSteelAnimal),
        }
        if entry['blueprint']['species_id'] != species_id:
            report['problems'].append('%s blueprint species_id=%r' % (species_id, entry['blueprint']['species_id']))
        if not bp_anim:
            report['problems'].append('%s blueprint has no animation set' % species_id)
        if not entry['blueprint']['is_animal']:
            report['problems'].append('%s blueprint parent is not AColdSteelAnimal' % species_id)
    report['species'].append(entry)
    u.log('WILDLIFE_VERIFY %s slots=%d' % (species_id, len(actions)))

(OUT / 'verify_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('WILDLIFE_VERIFY_DONE problems=' + str(len(report['problems'])))
