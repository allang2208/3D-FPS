"""Publish two independently reserved sides for the seven current double beds."""
import copy
import json
import os
from pathlib import Path
import runpy
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/FurnitureRest20261022/DoubleOccupancy20261025'
helper = runpy.run_path(str(ROOT / 'Tools/PlayerBody/config_transaction.py'))
receipts = []
with helper['_lock'](ROOT / 'Saved/FurnitureRestConfigWrites/writer.lock'):
    pending = []
    for filename in ('furniture_rest.json', 'apartment_furniture_rest.json'):
        path = ROOT / 'Content/ColdSteelData' / filename
        before = path.read_bytes()
        data = json.loads(before.decode('utf-8-sig'))
        text = before.decode('utf-8-sig')
        furniture = copy.deepcopy(data['furniture'])
        changed = []
        for index, original in enumerate(data['furniture']):
            if original.get('auto_select_free_slot') and len(original['slots']) == 2:
                continue
            if len(original['slots']) != 1:
                continue
            donor = original['slots'][0]
            if donor['kind'] not in ('Bed', 'BedKing', 'ApartmentBed'):
                continue
            profile = copy.deepcopy(original)
            center = donor['seat']
            scale = profile.get('scale', [1, 1, 1])
            # Current bed meshes have their width along local X. Native donor
            # BedKing enters from +X; Bed/ApartmentBed enter from -X.
            native_side = 1 if donor['kind'] == 'BedKing' else -1
            slots = []
            for side, label in ((-1, '左侧'), (1, '右侧')):
                slot = copy.deepcopy(donor)
                slot['seat'] = [center[0] + side * 10.0 / scale[0], center[1], center[2]]
                slot['focus'] = [center[0] + side * 50.0 / scale[0], center[1], center[2]]
                slot['label'] = label
                slot['mirror'] = side != native_side
                slots.append(slot)
            profile['slots'] = slots
            profile['auto_select_free_slot'] = True
            profile['caption'] = '双人床'
            furniture[index] = profile
            changed.append(profile['mesh'])
        if changed:
            text = helper['_set'](text, ('furniture',), furniture)
            pending.append((path, before, (b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')))
        receipts.append({'file': filename, 'double_bed_models_updated': changed})
    for path, before, result in pending:
        if path.read_bytes() != before:
            raise RuntimeError('Furniture config changed concurrently: ' + str(path))
        backup = OUT / 'Before/Content/ColdSteelData' / path.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(before)
        temporary = path.with_name('.double-bed-' + uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_bytes(result)
            if path.read_bytes() != before:
                raise RuntimeError('Furniture config changed during publication: ' + str(path))
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
(OUT / 'publication.json').write_text(json.dumps({'files': receipts, 'runtime_tested': False,
    'animation': 'Existing native sequences, mirrored in bind space for the opposite side; no mesh negative scale.',
    'slot_policy': 'Two slots per double bed; one occupant per chair/single-bed slot, reserved through exit.'},
    ensure_ascii=False, indent=2), encoding='utf-8')
print('Double-bed slot configuration published:', sum(len(r['double_bed_models_updated']) for r in receipts), 'models')
