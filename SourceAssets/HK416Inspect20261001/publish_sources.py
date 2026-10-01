"""Publish source references after the editor has recorded the asset saves."""
import json
from pathlib import Path

O=Path(__file__).parent
catalog_path=O.parent/'HK416CommonAttachments20260930/animations.json'
receipt_path=O/'import_receipt.json'
source=json.loads((O/'inspect_animations.json').read_text(encoding='utf-8'))
receipt_text=receipt_path.read_text(encoding='utf-8')
receipt=json.loads(receipt_text)
if set(receipt['animations'])!=set(source['clips']) or not all(row.get('saved') for row in receipt['animations'].values()):
    raise RuntimeError('Animation saves are incomplete; leave the published source catalog unchanged')
if not all(receipt['runtime_profiles'].get(f,{}).get('saved') for f in ('vertical','canted','prism','angled','drum')):
    raise RuntimeError('Grip-profile saves are incomplete; leave the published source catalog unchanged')
old_text=catalog_path.read_text(encoding='utf-8')
catalog=json.loads(old_text)
catalog['clips'].update(source['clips'])
catalog['inspect_reference']=source['reference']
catalog['inspect_revision']='HK416Inspect20261001: 4.2 s shared rifle inspection; six families; five runtime profiles'
backup=O/'Before/authoring_catalog_animations.json'
if not backup.exists():
    backup.parent.mkdir(parents=True,exist_ok=True)
    backup.write_text(old_text,encoding='utf-8')
if catalog_path.read_text(encoding='utf-8')!=old_text or receipt_path.read_text(encoding='utf-8')!=receipt_text:
    raise RuntimeError('Publication files changed; preserve concurrent edits')
catalog_path.write_text(json.dumps(catalog,indent=2),encoding='utf-8')
receipt['source_catalog_published']=True
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('HK416_INSPECT_SOURCE_PUBLISHED',len(source['clips']))
