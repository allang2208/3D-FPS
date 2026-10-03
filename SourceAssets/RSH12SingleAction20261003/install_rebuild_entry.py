"""Keep the original weapon producer from restoring obsolete double action."""
from pathlib import Path
import json
O=Path(__file__).parent;P=O.parents[1]
path=O.parent/'RSH12Integration20261003/publish_catalog.py';raw=path.read_bytes();text=raw.decode('utf-8-sig').replace('\r\n','\n')
flag='RSH12_SINGLE_ACTION_AMENDMENT'
if flag not in text:
    insert='''# RSH12_SINGLE_ACTION_AMENDMENT: preserve the saved single-action revision on reimport.
amendment=O.parent/'RSH12SingleAction20261003'
single_action=None
if (amendment/'import_receipt.json').exists() and json.loads((amendment/'import_receipt.json').read_text(encoding='utf8')).get('complete'):
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_single_action_catalog',amendment/'publish_catalog.py')
 single_action=importlib.util.module_from_spec(spec);spec.loader.exec_module(single_action)
'''
    text=text.replace("items=json.loads((D/'items.json')",insert+"items=json.loads((D/'items.json')",1)
    text=text.replace("key(D/'items.json',ID,item)","if single_action:single_action.apply_item(item)\nkey(D/'items.json',ID,item)",1)
    text=text.replace("path=D/'gunsmith.json';", "if single_action:single_action.apply_weapon(w)\npath=D/'gunsmith.json';",1)
    backup=O/'BeforeSource/SourceAssets/RSH12Integration20261003/publish_catalog.py';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent producer edit')
    path.write_text(text,encoding='utf8')
print('RSH12_SINGLE_ACTION_REBUILD_ENTRY_SAVED')
