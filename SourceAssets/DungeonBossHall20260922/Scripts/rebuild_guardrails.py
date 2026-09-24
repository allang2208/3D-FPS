"""Replace only the two stair groups and gallery rails in the existing authored assembly."""
import json
import re
import shutil
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
source = root/'Scripts/author.py'
blend = root/'Authored/Dungeon_BossPumpHall.blend'
backup = root/'Sources/BeforeGuardrailPolish20260923'
backup.mkdir(parents=True, exist_ok=True)
kinds = ('StairWest', 'StairEast', 'GalleryRails')
for path in (blend, root/'Authored/manifest.json', *(root/'Authored'/f'SM_RS_BossPumpHall_{k}.fbx' for k in kinds)):
    target = backup/path.name
    if not target.exists():
        shutil.copy2(path, target)

code = source.read_text(encoding='utf-8')
scope = {'__file__': str(source), '__name__': 'guardrail_partial_build'}
exec(compile(code.split('# Floor, high walls and roof')[0], str(source), 'exec'), scope)
for stair in scope['room']['stairs']:
    scope['staircase'](stair)
gallery = next(line for line in code.splitlines() if line.startswith('for a,b in [') and line.endswith(':rail(a,b)'))
exec(compile(gallery, str(source), 'exec'), scope)
from export_boss import export
export(scope['H'])
records = scope['H']['RECORDS']
names = [r['name'] for r in records]
parts = root/'Authored/GuardrailReplacement.blend'
bpy.data.libraries.write(str(parts), {bpy.data.objects[n] for n in names})

bpy.ops.wm.open_mainfile(filepath=str(blend))
for name in names:
    previous = bpy.data.objects.get(name)
    if not previous:
        raise RuntimeError('Missing source group '+name)
    bpy.data.objects.remove(previous, do_unlink=True)
with bpy.data.libraries.load(str(parts), link=False) as (src, dst):
    dst.objects = list(names)
for obj in dst.objects:
    bpy.context.scene.collection.objects.link(obj)
    for slot in obj.material_slots:
        key = re.sub(r'\.\d{3}$', '', slot.material.name)
        if key in bpy.data.materials:
            slot.material = bpy.data.materials[key]
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest_path = root/'Authored/manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
updates = {r['kind']: r for r in records}
manifest['objects'] = [updates.get(r['kind'], r) for r in manifest['objects']]
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
receipt = {'groups': names, 'source': str(blend), 'backup': str(backup), 'rendered': False}
(root/'Receipts/guardrails-authored-20260923.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('BOSS_GUARDRAILS_AUTHORED', json.dumps(receipt), flush=True)
