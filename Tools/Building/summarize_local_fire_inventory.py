"""Summarize the current read-only ObjectExporterT3D output without loading UE."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'SourceAssets/Campfire20261012'

def parse_export(file):
    objects, stack = {}, []
    for line in file.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if line.startswith('Begin Object'):
            cls, key = re.search(r'ExportPath="([^\']+)\'([^\']+)\'', line).groups()
            node = objects.setdefault(key, {'class': cls.rsplit('.', 1)[-1], 'props': {}, 'children': []})
            if stack and key not in stack[-1]['children']: stack[-1]['children'].append(key)
            stack.append(node)
        elif line == 'End Object':
            stack.pop()
        elif stack and '=' in line:
            key, value = line.split('=', 1)
            stack[-1]['props'][key] = value
    root = next(k for k, v in objects.items() if v['class'] == 'ParticleSystem')
    def deref(value, owner=root):
        name = re.search("'([^']+)'", value).group(1)
        key = name if name.startswith('/Game/') else root + ':' + name.split(':', 1)[1] if ':' in name else owner + ('.' if ':' in owner else ':') + name
        return key, objects[key]
    rows = []
    for key, value in objects[root]['props'].items():
        if not key.startswith('Emitters('): continue
        ek, emitter = deref(value)
        _, lod = deref(emitter['props']['LODLevels(0)'], ek)
        _, required = deref(lod['props']['RequiredModule'])
        row = {'name': emitter['props'].get('EmitterName'), 'required': required['props'], 'modules': []}
        for module_key, module_value in lod['props'].items():
            if not (module_key.startswith('Modules(') or module_key == 'SpawnModule'): continue
            _, module = deref(module_value)
            row['modules'].append({'class': module['class'], 'props': module['props'],
                'distributions': [objects[c] for c in module['children']]})
        rows.append(row)
    return {'path': root, 'emitters': rows}

result = {p.stem: parse_export(p) for p in (DEST / 'InventoryExports').glob('*.t3d')}
(DEST / 'local-fire-cascade-profiles.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
for name, data in result.items():
    print(name, len(data['emitters']))
    for emitter in data['emitters']:
        props = emitter['required']
        print(emitter['name'], props.get('Material'), props.get('SubImages_Horizontal', '1'), props.get('SubImages_Vertical', '1'))
