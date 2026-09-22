"""Record completed production/import/build without running acceptance work."""
import json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
spec=json.loads((P/'production.json').read_text(encoding='utf-8'))
installed=json.loads((P/'install_receipt.json').read_text(encoding='utf-8'))
build=(P/'build-native.log').read_text(encoding='utf-8-sig',errors='replace')
if not installed['complete'] or 'Result: Succeeded' not in build:raise RuntimeError('Import or required build remains incomplete.')
delivery={'time':datetime.now().isoformat(),'name':'裂角护手','slot':'guard','option':spec['option'],
          'source':P.name,'mesh':installed['mesh'],'ue_integrated':True,'stats':spec['stats'],
          'native_build':'FPSGAMEEditor Win64 Development: Succeeded','tested':False,
          'icon_source':'Actual delivered guard mesh; matching Highland camera and neutral lighting',
          'gameplay':'Parry -> 4s one-charge next normal press becomes instant heavy release, physical x1.25 and poise x1.4'}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=P.parent/'DELIVERY.json';old=path.read_bytes();root=json.loads(old.decode('utf-8-sig'))
root.setdefault('exclusive_modifications',{})[spec['option']]=delivery
if path.read_bytes()!=old:raise RuntimeError('Concurrent delivery edit preserved.')
temp=path.with_suffix('.cloven.tmp');temp.write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
print('CLOVEN_GUARD_DELIVERY_COMPLETE')
