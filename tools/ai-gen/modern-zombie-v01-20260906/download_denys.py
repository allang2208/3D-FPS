"""Download the author's publicly linked CC-BY model/animation resources."""
import urllib.request,urllib.parse,json,concurrent.futures
from pathlib import Path
R=Path(__file__).resolve().parent
BASE='https://denysalmaral.com/gamedev/free-zombies/'
FILES=['rig-gltf_joined/ZombieMale_'+x+'_joined.gltf' for x in 'ABCDE']
FILES+=['animations-gltf/gltf_ZombieMale/ZombieMale@'+x+'.gltf' for x in ['attack_left_70f','attack_right_70f','idle2_220f','idle_220f','idle_alert_120f','running_58f','slowWalk_85f','walk_64f','walk_agressive_64f','walk_limp_60f']]
def fetch(rel):
 url=urllib.parse.urljoin(BASE,rel);path=R/'denys'/rel
 path.parent.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen(url,timeout=30) as r:path.write_bytes(r.read())
 data=json.loads(path.read_text())
 dependencies=[]
 for item in data.get('buffers',[])+data.get('images',[]):
  uri=item.get('uri','')
  if not uri or uri.startswith('data:'):continue
  local=(path.parent/urllib.parse.unquote(uri)).resolve()
  assert local.is_relative_to((R/'denys').resolve())
  local.parent.mkdir(parents=True,exist_ok=True)
  dependency_url=urllib.parse.urljoin(BASE,'zcolors.png') if uri=='zcolors.png' else urllib.parse.urljoin(url,uri)
  with urllib.request.urlopen(dependency_url,timeout=30) as r:local.write_bytes(r.read())
  dependencies.append(uri)
 return {'url':url,'file':str(path.relative_to(R)),'dependencies':dependencies,'animations':[a.get('name') for a in data.get('animations',[])]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 report=list(ex.map(fetch,FILES))
(R/'denys-download-report.json').write_text(json.dumps(report,indent=2))
print('DENYS_PUBLIC_ASSETS_READY',json.dumps(report))
