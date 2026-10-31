from pathlib import Path
import json,collections
R=Path(__file__).resolve().parent
source=json.loads((R/'native_manifest.json').read_text())
published=json.loads((R/'publish_manifest.json').read_text())
attrs=json.loads((R/'native_instance_attributes.json').read_text())['attributes']
original={r['actor']+'|'+r['component']:r for r in source['rows']}
def key(t):return tuple(t['p']+t['q']+t['s'])
values=0;instances=0
for row in published['rows']:
    ident=row['actor']+'|'+row['component'];a=attrs.get(ident)
    row['custom_stride']=a['stride'] if a else 0
    if not a:continue
    origin=original[ident];n=a['stride']
    if len(a['data'])!=n*len(origin['transforms']):raise RuntimeError('Instance attribute order mismatch '+ident)
    lookup=collections.defaultdict(collections.deque)
    for i,tr in enumerate(origin['transforms']):lookup[key(tr)].append(a['data'][i*n:(i+1)*n])
    for tr in row['transforms']:
        tr['custom']=lookup[key(tr)].popleft();values+=n;instances+=1
published['native_material_attributes_preserved']=True
(R/'publish_manifest.json').write_text(json.dumps(published,separators=(',',':')),encoding='utf8')
(R/'material_attributes_delivery.json').write_text(json.dumps(dict(stage='composed',instances=instances,float_values=values),indent=2),encoding='utf8')
print('NATIVE_ATTRIBUTES_COMPOSED',instances,values,flush=True)
