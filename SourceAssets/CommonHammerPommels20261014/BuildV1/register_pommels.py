"""Merge the three saved pommel assets into the shared catalogue and host slot."""
import json, runpy
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT/'Content/ColdSteelData'
catalog = runpy.run_path(str(P/'catalog.py'))
options = catalog['OPTIONS']
library = DATA/'common-hammer-pommels.json'
data = json.loads(library.read_text(encoding='utf-8-sig')) if library.exists() else {'version':1,'slot':'pommel','options':[]}
incoming = {o['id']:o for o in options}
merged = []
for old in data['options']:
    option = incoming.pop(old['id'],None)
    if option:
        # Re-authoring appearance must not undo a later approved balance table.
        for key in ('stats','effects','special_effects'):
            if key in old: option[key]=old[key]
        merged.append(option)
    else: merged.append(old)
data['options'] = merged+list(incoming.values())
library.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path = DATA/'warhammer-modules.json'
data = json.loads(path.read_text(encoding='utf-8-sig'))
for row in json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']:
    option = next(o for o in options if o['id']==row['id'])
    package = catalog['MESH_DIR']+'/'+row['mesh']
    data['slots']['pommel'][row['id']] = {'mesh':package+'.'+row['mesh'],
        'location_cm':row['location_cm'],'appearance':option['appearance'],
        'interface':'warhammer_factory_v1','shared_option_library':library.name,'model_revision':'BuildV1'}
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path = DATA/'warhammer-gunsmith.json'
data = json.loads(path.read_text(encoding='utf-8-sig'))
next(c for c in data['columns'] if c['key']=='pommel')['options_library'] = library.name
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COMMON_HAMMER_POMMELS_REGISTERED')
