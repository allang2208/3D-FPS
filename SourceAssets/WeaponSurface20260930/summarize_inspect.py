"""Print a compact view of inspect/runtime_materials.json (plain CPython)."""
import json
import sys
from pathlib import Path

d = json.loads((Path(__file__).parent / 'inspect' / 'runtime_materials.json').read_text(encoding='utf-8'))
only = sys.argv[1:] or None
for path, m in d['materials'].items():
    if only and not any(o in path for o in only):
        continue
    print('==', path.split('.')[-1], '| base', (m.get('base') or '').split('/')[-1], '| exprs', m.get('expression_count'),
          '|', m.get('shading_model'), m.get('blend_mode'), 'skel', m.get('used_with_skeletal_mesh'))
    print('   outputs', m.get('outputs'))
    p = m.get('parameters', {})
    for kind in ['scalar', 'vector', 'static_switch']:
        if p.get(kind):
            print('  ', kind, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in p[kind].items()})
    for k, t in (p.get('texture') or {}).items():
        print('   texparam', k, t and (t['path'].split('/')[-1], t['size'], t['srgb'], t['compression']))
    for t in m.get('used_textures', []):
        if t:
            print('   used', t['path'].split('.')[-1], t['size'], 'srgb', t['srgb'], t['compression'], (t.get('source_file') or '')[-80:])
    if '--graph' in sys.argv or (only and len(only) == 1):
        for e in m.get('expressions', []):
            print('     ', {k: v for k, v in e.items() if k != 'code'}, ('CODE:' + e['code'][:300].replace('\n', ' | ')) if 'code' in e else '')
        for fn, items in m.get('functions', {}).items():
            print('    FUNCTION', fn, len(items) if isinstance(items, list) else items)
