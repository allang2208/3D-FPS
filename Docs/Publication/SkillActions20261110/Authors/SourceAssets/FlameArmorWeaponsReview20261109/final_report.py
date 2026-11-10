"""Merge completed visual runs; keep the latest evidence for each catalogue case."""
import json
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
expected = json.loads((ROOT / 'ordered-all.json').read_bytes())
latest = {}
for run in ['all_after', 'final_after', 'bows_hands_after']:
    path = ROOT / run / 'runtime.json'
    if not path.exists():
        continue
    for case in json.loads(path.read_bytes())['cases']:
        if case['reason'].startswith('Captured') and len(case['samples']) == 9:
            latest[case['id']] = (run, case)

rows = []
for definition in expected:
    case_id = definition['id']
    if case_id not in latest:
        rows.append(dict(id=case_id, issues=['No complete run']))
        continue
    run, case = latest[case_id]
    issues = []
    root_error = 0.
    minimum_core = 100000
    sections = set()
    flying_samples = 0
    for sample in case['samples']:
        image_path = ROOT / run / case_id / sample['image']
        if not image_path.exists():
            issues.append('Missing image: ' + sample['image'])
        expected_sections = Counter(a['section'] for a in sample['attachments'])
        held = [e for e in sample['effects'] if 'anchor_error_cm' in e]
        actual_sections = Counter(e['section'] for e in held)
        if expected_sections != actual_sections:
            issues.append('Attachment/effect mismatch: ' + sample['image'])
        sections.update(expected_sections)
        for effect in sample['effects']:
            if 'BowArrow' in effect['owner']:
                flying_samples += 1
            root_error = max(root_error, effect.get('anchor_error_cm', 0.))
            if not effect['visible'] or effect['paused'] or sum(effect['particles']) == 0:
                issues.append('Inactive visual: ' + sample['image'])
            if sum(p['invalid'] for p in effect.get('particle_samples', [])):
                issues.append('Invalid particle sample: ' + sample['image'])
            if 'AllWeaponsV12' in effect['asset'] and effect in held:
                minimum_core = min(minimum_core, effect['particles'][0])
    if root_error > .1:
        issues.append('Sampled attachment root error exceeds 0.1 cm')
    if minimum_core == 0:
        issues.append('Persistent core missing')
    rows.append(dict(id=case_id, name=definition.get('name', case_id), family=definition['family'],
                     run=run, images=len(case['samples']), sections=sorted(sections),
                     maximum_sampled_root_error_cm=root_error,
                     minimum_warm_core_particles=None if minimum_core == 100000 else minimum_core,
                     flying_arrow_samples=flying_samples, issues=sorted(set(issues))))

report = dict(expected_cases=len(expected), complete_cases=len(latest),
              cases_with_issues=[r['id'] for r in rows if r['issues']],
              screenshots=sum(r.get('images', 0) for r in rows),
              maximum_sampled_root_error_cm=max(r.get('maximum_sampled_root_error_cm', 0.) for r in rows),
              scope='Factory weapon configurations and ten held/offhand configurations, local first-person view.',
              limitations='Not every gunsmith permutation, multiplayer or an FPS benchmark. Root error is a sampled component metric, not a pixel drift metric.',
              cases=rows)
(ROOT / 'final-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

selection = [('ue_tang_dao', '02'), ('ue_kukri', '03'), ('staff_hatchet', '02'),
             ('ue_m4a1', '02'), ('bow_woodsteel', '05'), ('ue_thunder_god_hammer', '09')]
sheet = Image.new('RGB', (1280, 1164), (24, 24, 24))
draw = ImageDraw.Draw(sheet)
for index, (case_id, shot) in enumerate(selection):
    if case_id not in latest:
        continue
    run, _ = latest[case_id]
    path = ROOT / run / case_id / (shot + '.png')
    x, y = index % 2 * 640, index // 2 * 388
    with Image.open(path) as frame:
        sheet.paste(frame.resize((640, 360)), (x, y + 28))
    draw.text((x + 8, y + 6), case_id + ' / ' + shot, fill='white')
sheet.save(ROOT / 'review-preview.jpg', quality=94)
print(json.dumps({k: v for k, v in report.items() if k != 'cases'}, ensure_ascii=False, indent=2))
