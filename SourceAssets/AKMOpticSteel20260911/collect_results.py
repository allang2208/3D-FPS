from pathlib import Path
import json,re,hashlib
O=Path(__file__).parent;r={}
for k in ('holographic','panoramic','scope2x','lpvo'):
 p=O/(k+('-steel4' if k in ('scope2x','lpvo') else '-steel2'))/'write.log';s=p.read_text(encoding='utf-8',errors='replace');m=re.search(r'M4_GUNSMITH: COMPLETE checks=(\d+) failures=(\d+)',s);assert m and m[2]=='0',k
 assert 'Failed to compile Material' not in s,k
 r[k]={'checks':int(m[1]),'failures':0,'material_compile_fallback':False}
P=Path('D:/FPS3D/FPSGAME/Content/Weapons/AKMIntegration/SovietFab/OpticSteel');r['assets']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.glob('*.uasset')}
(O/'acceptance.json').write_text(json.dumps(r,indent=2));print('AKM_OPTIC_STEEL_ACCEPTANCE_PASS',sum(r[k]['checks'] for k in ('holographic','panoramic','scope2x','lpvo')))
