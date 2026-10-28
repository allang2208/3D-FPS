"""Publish precisely the authored grip textures once the project window is clear."""
import json, hashlib, shutil, os
from datetime import datetime
from pathlib import Path
P = Path(__file__).resolve().parent
receipt = json.loads((P / 'Receipts/import-assets.json').read_text(encoding='utf-8'))
if not receipt['complete']:
    raise RuntimeError('Texture import is incomplete')
originals = json.loads((P / 'Receipts/staging-inputs.json').read_text(encoding='utf-8'))
for item in originals:
    target, source = Path(item['target']), Path(item['staged'])
    if not source.exists():
        raise RuntimeError('Saved output missing: ' + str(source))
    if hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
        raise RuntimeError('Target changed during authoring; preserved: ' + str(target))
publication = {'complete': False, 'started': datetime.now().astimezone().isoformat(), 'files': [],
               'geometry_changed': False, 'numeric_changes': False, 'runtime_tested': False}
for item in originals:
    target, source = Path(item['target']), Path(item['staged'])
    backup = P / 'Before' / target.name
    if not backup.exists():
        shutil.copy2(target, backup)
    temporary = target.with_name(target.name + '.kukri-grip-' + str(os.getpid()) + '.tmp')
    shutil.copy2(source, temporary)
    os.replace(temporary, target)
    publication['files'].append({'target': str(target), 'source': str(source)})
    (P / 'Receipts/publication.json').write_text(json.dumps(publication, ensure_ascii=False, indent=2), encoding='utf-8')
surfaces = json.loads((P / 'surfaces.json').read_text(encoding='utf-8'))
variants = {v['icon_key']: v for v in surfaces['variants']}
final_path = P.parent / 'KukriFinalIntegration20261026/manifest.json'
manifest = json.loads(final_path.read_text(encoding='utf-8'))
shutil.copy2(final_path, P / 'Before/final-icon-manifest.json')
for master in manifest['masters']:
    if master['id'] in variants:
        v = variants[master['id']]
        master.update(source=v['icon_input'], input=v['icon_input'], output=v['icon'],
                      surface_revision='KukriGripSurfaceV220261027', source_blend=v['source_blend'],
                      surface_materials={v['material']: v['textures']})
final_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
components_path = P.parent / 'KukriComponentVariants20261026/components.json'
components = json.loads(components_path.read_text(encoding='utf-8'))
shutil.copy2(components_path, P / 'Before/components.json')
for entry in components['variants']:
    if entry['icon_key'] in variants:
        v = variants[entry['icon_key']]
        entry.update(textures=v['textures'], icon=v['icon'], source_blend=v['source_blend'],
                     surface_revision='KukriGripSurfaceV220261027')
components_path.write_text(json.dumps(components, ensure_ascii=False, indent=2), encoding='utf-8')
publication['complete'] = True
(P / 'Receipts/publication.json').write_text(json.dumps(publication, ensure_ascii=False, indent=2), encoding='utf-8')
print('KUKRI_GRIP_SURFACE_V2_PUBLISHED ' + str(len(publication['files'])))
