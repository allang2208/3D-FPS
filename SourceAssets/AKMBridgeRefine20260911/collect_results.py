from pathlib import Path
import json,re,hashlib
O=Path(__file__).parent
r={}
for k in ('panoramic','scope2x','lpvo'):
 p=O/(k+'-bridge2')/'write.log';s=p.read_text(encoding='utf-8',errors='replace');m=re.search(r'M4_GUNSMITH: COMPLETE checks=(\d+) failures=(\d+)',s);assert m and m[2]=='0',k
 r[k]={'checks':int(m[1]),'failures':0,'log':str(p)}
assets=Path('D:/FPS3D/FPSGAME/Content/Weapons/AKMIntegration/SovietFab/Optics')
r['assets']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in assets.glob('SM_AKM_Mount_*.uasset')}
(O/'acceptance.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print('AKM_BRIDGE_FINAL_PASS',sum(r[k]['checks'] for k in ('panoramic','scope2x','lpvo')))
