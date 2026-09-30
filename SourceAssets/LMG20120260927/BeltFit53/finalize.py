"""Record the completed scoped delivery after the background saves finish."""
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((O/'delivery.json').read_text());a=json.loads((O/'animation_delivery.json').read_text())
if r['status']!='current_body_saved' or a['status']!='ten_reload_belt_tracks_saved' or len(a['saved'])!=10:
 raise RuntimeError('Asset saves not complete; receipt not finalized')
build=(O/'build_console.log').read_text(encoding='utf-8-sig',errors='replace')
if 'Result: Succeeded' not in build:raise RuntimeError('Native build not complete')
saved={**r['saved'],**a['saved']}
for name,row in saved.items():
 if sha(P/'Content'/(name.removeprefix('/Game/')+'.uasset'))!=row['sha256']:
  raise RuntimeError('Saved file changed; retain current asset '+name)
r.update(status='body_and_ten_reload_belt_tracks_saved',animations_modified=True,
 animation_receipt='animation_delivery.json',modified_animation_count=10,
 native_build={'status':'succeeded','log':'build_console.log','dll_sha256':sha(P/'Binaries/Win64/UnrealEditor-FPSGAME.dll'),
 'source':{str(p.relative_to(P)):sha(p) for p in [P/'Source/FPSGAME/Weapons/LMG201BeltDynamics.cpp',P/'Source/FPSGAME/Weapons/LMG201BeltLayout.h']}},
 offline_inspection={'scope':'current reload source poses and unchanged left glove geometry','frames':[209,222,458,489,526,574],'rendering':'diagnostic materials, not UE runtime'},runtime_tested=False)
(O/'delivery.json').write_text(json.dumps(r,indent=2))
path=O.parent/'README.md';text=path.read_text(encoding='utf-8-sig')
old=next(line for line in text.splitlines() if line.startswith('- 布箱弹链：'))
new='- 布箱弹链：当前为 **[BeltFit53](BeltFit53/README.md)**，替代 BeltMotion49／BeltRebuild52 的弹链布局。连续袋内段、独立连接片和转入机匣的上端，已连同 ClothReload44.3 现用十条动作中的弹链骨骼补丁后台保存；手臂、袋体及换弹时序保持原样。对应进弹／阻尼源码已构建，完成用户指定的离线换弹关键姿态排查，未启动游戏。后续不可直接用 R44 旧整段导入器覆盖本轮补丁。'
path.write_text(text.replace(old,new,1),encoding='utf-8')
print('B53_DELIVERED',len(saved),'assets; native build succeeded; runtime not tested')
