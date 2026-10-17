"""Reuse the existing neutral empty-slot symbol for M870 manual loading only."""
import json,hashlib,shutil
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
directory=ROOT/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
source=directory/'tactical_false.png';key='ue_m870_reload_device_false';dest=directory/(key+'.png')
if dest.exists():raise RuntimeError('Preserve unexpected M870 manual-load icon')
shutil.copy2(source,dest)
manifest=OUT/'deployment.json';data=json.loads(manifest.read_text())
data['entries'].append({'key':key,'source':str(source.relative_to(ROOT)),'runtime_png':str(dest.relative_to(ROOT)),
    'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'previous_weapon_specific_icon':None,
    'reason':'Manual loading has no loader attachment; replace inherited colored ammunition-prohibition artwork with existing neutral empty-slot symbol.'})
data['unchanged_shared_empty_slots']=['tactical_false']
data['reused_existing_masters']=1
temporary=manifest.with_suffix('.pending');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(manifest)
print('M870 manual loading PNG published; factory keys:',len(data['entries']))
