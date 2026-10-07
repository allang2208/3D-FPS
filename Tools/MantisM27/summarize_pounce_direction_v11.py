"""Compare user-requested blade orientation evidence and UE import readback."""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV11')
old = json.loads((ROOT / 'Inspection/PounceV10/directions.json').read_text())
new = json.loads((ROOT / 'Inspection/PounceV11/directions.json').read_text())
ue = json.loads((ROOT / 'ue_direction_readback.json').read_text())
report = {'revision': 'PounceV11', 'scope': 'Offline authored blade direction and UE RAW imported-pose readback',
          'runtime_tested': False, 'comparisons': [], 'ue_roundtrip': []}
for a, b in zip(old['samples'], new['samples']):
    report['comparisons'].append({'role': b['role'], 'time': b['time'], 'sides': {
        side: {'before_plane_error_deg': a['sides'][side]['blade_plane_error_deg'],
               'after_plane_error_deg': b['sides'][side]['blade_plane_error_deg']}
        for side in ['l', 'r']}})
for a, b in zip(new['samples'], ue['samples']):
    for side in ['l', 'r']:
        for axis in ['chord', 'bend']:
            src = a['sides'][side]['helper_axes'][axis]
            dst = b['sides'][side][axis]
            value = sum(x*y for x, y in zip(src, dst))
            angle = math.degrees(math.acos(max(-1., min(1., value))))
            report['ue_roundtrip'].append({'role': a['role'], 'time': a['time'], 'side': side,
                                           'axis': axis, 'error_deg': angle})
report['max_ue_direction_error_deg'] = max(r['error_deg'] for r in report['ue_roundtrip'])
report['continuity'] = new['continuity']
report['boundary_angles_deg'] = new['boundary_angles_deg']
(ROOT / 'direction_review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

frames = [('PounceFlight_200_side.png', 'RAISED / 0.20s'),
          ('PounceFlight_480_side.png', 'DOWNSWING / 0.48s'),
          ('PounceLand_000_side.png', 'TOUCHDOWN / 0.00s')]
sheet = Image.new('RGB', (1440, 1040), '#24272b')
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
for row, (version, label) in enumerate([('PounceV10', 'BEFORE V10'), ('PounceV11', 'REVISED V11')]):
    for col, (filename, title) in enumerate(frames):
        frame = Image.open(ROOT / 'Inspection' / version / filename).convert('RGB').resize((480, 480))
        sheet.paste(frame, (col*480, row*520+40))
        draw.text((col*480+12, row*520+10), label+'   '+title, fill='white', font=font)
sheet.save(ROOT / 'blade-direction-comparison.png')
print(json.dumps({'max_ue_direction_error_deg': report['max_ue_direction_error_deg'],
                  'comparison': str(ROOT / 'blade-direction-comparison.png')}, indent=2))
