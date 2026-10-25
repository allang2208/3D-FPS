"""Update only the five members' set metadata; retain all individual item fields."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

P = Path(__file__).resolve().parents[2]
R = P / 'SourceAssets/OutdoorWorkSet20261024'
sys.path.insert(0, str(P / 'Tools/BrownLeatherSet'))
import json_entries as entries

MEMBERS = ('ue_cargo_pants', 'ue_boots', 'ue_original_gloves', 'ue_field_hat', 'ue_work_jacket')
FIELDS = dict(armorSet='workwear', setName='户外工作套装',
              setBonusDesc='集齐五件：所有动作体力消耗 -15%，移动速度 +10%，饥饿及口渴下降速度 -25%。')


def main():
    R.mkdir(parents=True, exist_ok=True)
    before_dir = R / 'Before'
    before_dir.mkdir(exist_ok=True)
    report = dict(completed=False, members=MEMBERS, set_name=FIELDS['setName'],
                  multipliers=dict(action_stamina=.85, movement=1.10, hunger=.75, hydration=.75),
                  individual_item_fields_changed=False, files=[], runtime_tested=False)
    for name in ('items.json', 'source-combat-items.json'):
        path = P / 'Content/ColdSteelData' / name
        before = path.read_bytes()
        text = before.decode('utf-8-sig')
        catalog = json.loads(text)
        for key in MEMBERS:
            for field, value in FIELDS.items():
                text = entries.replace(text, [key, field], value) if field in catalog[key] else entries.insert(text, [key], field, value)
        if not (before_dir / name).exists():
            (before_dir / name).write_bytes(before)
        output = (b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
        if output != before:
            if path.read_bytes() != before:
                raise RuntimeError('Catalog changed; merge from current contents: ' + name)
            temp = path.with_name(path.name + '.outdoor-' + uuid.uuid4().hex + '.tmp')
            temp.write_bytes(output)
            if path.read_bytes() != before:
                raise RuntimeError('Concurrent catalog edit; preserving current contents: ' + name)
            os.replace(temp, path)
        report['files'].append(dict(path=str(path), fields=list(FIELDS),
                                    before_sha256=hashlib.sha256(before).hexdigest(),
                                    after_sha256=hashlib.sha256(output).hexdigest()))
        (R / 'published.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    report['completed'] = True
    (R / 'published.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('OUTDOOR_WORK_SET_PUBLISHED: five members; only armorSet/setName/setBonusDesc updated')


if __name__ == '__main__':
    main()
