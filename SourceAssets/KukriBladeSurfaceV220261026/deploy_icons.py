"""Publish only the three revised blade icons and advance their master references."""
import hashlib,json,shutil
from datetime import datetime
from pathlib import Path
P=Path(__file__).resolve().parent
final=P.parent/'KukriFinalIntegration20261026'
manifest_path=final/'manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
surfaces=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
variants={v['icon_key']:v for v in surfaces['variants']}
for v in variants.values():
    if not Path(v['icon']).exists():raise RuntimeError('Generated icon missing: '+v['icon'])
backup=P/'Before/final-icon-manifest.json'
if not backup.exists():shutil.copy2(manifest_path,backup)
receipt={'complete':False,'started':datetime.now().astimezone().isoformat(),
         'bindings':[],'numeric_changes':False,'runtime_tested':False}
for binding in manifest['bindings']:
    if binding['master'] not in variants:continue
    v=variants[binding['master']];source=Path(v['icon']);target=Path(binding['runtime_png'])
    for original in [target,target.with_suffix('.uasset')]:
        backup=P/'Before'/original.name
        if original.exists() and not backup.exists():shutil.copy2(original,backup)
    shutil.copy2(source,target)
    receipt['bindings'].append({**binding,'source':str(source),
                               'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
for master in manifest['masters']:
    if master['id'] in variants:
        v=variants[master['id']]
        master['source']=v['icon_input'];master['input']=v['icon_input'];master['output']=v['icon']
        master['surface_revision']='KukriBladeSurfaceV220261026'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
receipt['complete']=True
(P/'Receipts/deployment.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('KUKRI_SURFACE_V2_ICONS_DEPLOYED '+str(len(receipt['bindings'])))
