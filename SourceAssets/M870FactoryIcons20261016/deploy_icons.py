"""Save generated masters and publish only the six requested M870 factory keys."""
import json,shutil,hashlib
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
DEST=ROOT/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
data=json.loads((OUT/'generation_manifest.json').read_text())
targets=[DEST/(key+'.png') for item in data['entries'] for key in item['keys']]
for path in targets:
    if path.exists():raise RuntimeError('A previously absent M870 key appeared during authoring; preserve it: '+str(path))
(OUT/'Generated').mkdir(exist_ok=True)
saved=[]
for item in data['entries']:
    master=OUT/'Generated'/(item['name']+'.png')
    shutil.copy2(item['generated_file'],master)
    for key in item['keys']:
        path=DEST/(key+'.png');shutil.copy2(master,path)
        saved.append({'key':key,'source':str(master.relative_to(ROOT)),'runtime_png':str(path.relative_to(ROOT)),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'previous_weapon_specific_icon':None})
report={'entries':saved,'unique_masters':len(data['entries']),
    'stock_reargrip_shared_reason':'Same native one-piece stock with integral grip neck',
    'unchanged_shared_empty_slots':['reload_device_false','tactical_false'],
    'runtime_resolution':'M4GunsmithLayout factory false resolves weapon-specific FramedFirearms PNG before shared fallback',
    'cpp_changed':False,'game_tested':False}
(OUT/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M870 factory PNGs saved:',len(saved))
