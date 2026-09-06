import json,base64,copy
from pathlib import Path
R=Path(__file__).resolve().parent
def embedded(path):
 d=json.loads(path.read_text())
 for item in d.get('buffers',[])+d.get('images',[]):
  uri=item.get('uri','')
  if uri and not uri.startswith('data:'):
   mime='image/png' if uri.endswith('.png') else 'application/octet-stream'
   item['uri']='data:'+mime+';base64,'+base64.b64encode((path.parent/uri).read_bytes()).decode()
 return d
for variant in 'ABCDE':
 d=embedded(R/f'denys/rig-gltf_joined/ZombieMale_{variant}_joined.gltf');d['animations']=[]
 names={n.get('name'):i for i,n in enumerate(d['nodes'])}
 for path in sorted((R/'denys/animations-gltf/gltf_ZombieMale').glob('*.gltf')):
  s=embedded(path);bo=len(d['buffers']);vo=len(d['bufferViews']);ao=len(d['accessors'])
  for view in s['bufferViews']:view['buffer']+=bo
  for acc in s['accessors']:
   if 'bufferView' in acc:acc['bufferView']+=vo
  for anim in s['animations']:
   for sm in anim['samplers']:sm['input']+=ao;sm['output']+=ao
   for ch in anim['channels']:ch['target']['node']=names[s['nodes'][ch['target']['node']]['name']]
   anim['name']=anim['name'].split('@')[-1]
  d['buffers']+=s['buffers'];d['bufferViews']+=s['bufferViews'];d['accessors']+=s['accessors'];d['animations']+=s['animations']
 (R/f'denys-{variant}-motions.gltf').write_text(json.dumps(d,separators=(',',':')))
print('DENYS_FIVE_MODELS_TEN_NATIVE_CLIPS_MERGED')
