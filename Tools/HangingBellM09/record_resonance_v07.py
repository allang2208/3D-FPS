"""Record completed M09 V07 production, without launching or testing gameplay."""
import json
from pathlib import Path
from datetime import datetime
project=Path('D:/FPS3D/FPSGAME');records=project/'SourceAssets/HangingBellM09Meshy20261003/ResonanceV07/Records'
assets=json.loads((records/'import_saved.json').read_text(encoding='utf8'))
builds={}
for target in ('FPSGAMEEditor','FPSGAME'):
 log=records/f'build_{target}_stdout.log';text=log.read_text(encoding='utf-8-sig',errors='replace')
 builds[target]={'log':str(log),'succeeded':'Result: Succeeded' in text,'kind':'regular native build'}
receipt={'recorded_at':datetime.now().isoformat(timespec='seconds'),'production':'M09 Resonance V07',
 'assets':assets,'builds':builds,'complete':assets['complete'] and all(b['succeeded'] for b in builds.values()),
 'tested':False,'interactive_editor_or_game_launched':False,
 'contract':{'duration':5.6,'pulses':[1.1,1.8,2.5,3.2,3.9,4.6],'direction_lock':.8,
 'magic_multiplier_per_hit':.45,'range_cm':2000,'cone_full_angle':100,'sanity_loss_per_accepted_hit':2,
 'membrane_open_seconds':.12,'simultaneous_open':True,'wave_fade_in_seconds':.14,'wave_fade_out_seconds':.66,'wave_lifetime':.9},
 'preserved':['V03 skinning and geometry','V04 skeleton','V05 spawn and ceiling movement']}
(records/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
if receipt['complete']:
 with (project/'Docs/Monsters/HangingBellM09ResonanceV07_20261004.md').open('a',encoding='utf8') as f:
  f.write('\n\n## 实际落盘\n\n四项V07资产实际保存，后台导入返回0；FPSGAMEEditor和FPSGAME（Win64 Development）常规构建成功，基础DLL及游戏EXE已落盘。详见 `ResonanceV07/Records/delivery.json`。本任务未启动交互编辑器、游戏、PIE或执行测试。\n')
print(json.dumps({'complete':receipt['complete'],'builds':builds,'saved':len(assets['saved']),'tested':False},ensure_ascii=False))
