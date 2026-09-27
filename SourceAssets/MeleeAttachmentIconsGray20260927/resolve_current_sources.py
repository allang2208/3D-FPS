"""Reuse the preceding UE source snapshot only while the live modular catalog matches."""
from pathlib import Path
import json,copy
P=Path(__file__).resolve().parent;DATA=P.parents[1]/'Content/ColdSteelData'
read=lambda n:json.loads((DATA/n).read_text(encoding='utf-8-sig'))
previous=json.loads((P/'runtime_sources.json').read_text(encoding='utf-8'))
result={}
for name in ['rune-sword-modules.json','frost-sword-modules.json','highland-claymore-modules.json']:
    cat=read(name);profile=cat['pommel_profile'];lib=read(profile['library'])
    for oid,base in lib['options'].items():
        spec=copy.deepcopy(base);fitting=profile.get('interfaces',{}).get(spec['interface'],{})
        for key in ['location_cm','rotation_deg','scale','adapter']:
            if key in profile:spec[key]=profile[key]
            if key in fitting:spec[key]=fitting[key]
        spec.update(lib.get('finishes',{}).get(profile['finish'],{}).get(oid,{}))
        cat['slots']['pommel'][oid]=spec
    result[cat['weapon']]=cat==previous['catalogs'][cat['weapon']]
(P/'current-catalog-sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result)
if not all(result.values()):raise RuntimeError('Resolve changed source references before importing icons.')
