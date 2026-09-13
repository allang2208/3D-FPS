"""Read-only Blender source audit; run explicitly with blender --background --python.

Optional arguments after --: --project D:/FPS3D/FPSGAME --output <report.json>.
No assets are saved or exported.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--project', default='D:/FPS3D/FPSGAME')
parser.add_argument('--output')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
root = Path(args.project)
source = root / 'SourceAssets/M1911RearRain20260913/M1911_RearFinish_Editable.blend'
output = Path(args.output) if args.output else root / 'Saved/M1911Audit/author-source.json'
warnings = []
try:
    bpy.ops.wm.open_mainfile(filepath=str(source))
except RuntimeError as exc:
    if 'Missing library override hierarchy root data' not in str(exc):
        raise
    warnings.append(str(exc))
rig = bpy.data.objects.get('SK_M1911_Manny')
low = bpy.data.collections.get('M1911_LOW')
assert rig and low, 'Required current author rig and low collection missing'
rows = []
failures = []
for obj in sorted(low.objects, key=lambda x: x.name):
    if obj.type != 'MESH':
        continue
    groups = {g.index: g.name for g in obj.vertex_groups}
    invalid = 0
    used = set()
    for vertex in obj.data.vertices:
        influences = [(groups[g.group], g.weight) for g in vertex.groups
                      if groups[g.group] in rig.data.bones and g.weight > 0]
        used.update(name for name, _ in influences)
        if abs(sum(weight for _, weight in influences) - 1) > .001:
            invalid += 1
    material_error = any(p.material_index >= len(obj.data.materials)
                         or obj.data.materials[p.material_index] is None for p in obj.data.polygons)
    row = {'object': obj.name, 'vertices': len(obj.data.vertices), 'bones': sorted(used),
           'invalid_weights': invalid, 'missing_material': material_error}
    rows.append(row)
    if invalid or material_error:
        failures.append(row)
    if obj.name == 'M1911_GripSafety' and used != {'WPN_root'}:
        failures.append({'object': obj.name, 'error': 'grip safety must remain with frame'})
    if obj.name == 'M1911_Slide' and used != {'WPN_Slide'}:
        failures.append({'object': obj.name, 'error': 'slide must keep its mechanical bone'})
required = {'M1911_Frame', 'M1911_Slide', 'M1911_GripSafety'}
missing = sorted(required - {row['object'] for row in rows})
if missing:
    failures.append({'missing_parts': missing})
report = {'source': str(source), 'read_only': True, 'objects': rows, 'warnings': warnings,
          'failures': failures, 'note': 'Weights/material slots do not establish visual hand-contact or audio acceptance.'}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding='utf8')
print(f'M1911_AUTHOR_AUDIT objects={len(rows)} failures={len(failures)} report={output}', flush=True)
if failures:
    raise RuntimeError('M1911 author audit failed; see report')
