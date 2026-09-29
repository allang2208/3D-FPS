"""Publish only the captured chainmail firearm mappings; retain concurrent edits."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailReloadFit20260929';config=P/'Content/ColdSteelData/modular_outfits.json'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'saved.json');sources=read(R/'sources.json');report=read(R/'diagnosis.json')
if set(saved)!=set(sources) or set(report)!=set(sources):raise RuntimeError('Incomplete saved set or clip report')
c=read(config);mapping=c['items']['ue_chainmail_shirt']['rig_meshes']
for rig,entry in saved.items():
 if mapping[rig] not in [entry['previous'],entry['asset']]:raise RuntimeError('Concurrent chainmail mapping edit: '+rig)
 if len(report[rig])!=len(sources[rig]['clips']):raise RuntimeError('Missing reload comparison '+rig)
 for row in report[rig].values():
  if row['after_max']>row['before_max']+.01:raise RuntimeError('Reload stretch regression '+rig)
(R/'config-before-publication.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
for rig,entry in saved.items():mapping[rig]=entry['asset']
config.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'published.json').write_text(json.dumps(saved,indent=2))
lines=['# 锁子甲换弹形变修复 — 2026-09-29','',
'已保存并接入 15 套枪械衣袖网格，每套 3 档 LOD。仅更新锁子甲的对应 rig_meshes，不修改换弹动画、枪械或手套。', '',
'## 原因与调整','',
'原衣袖继承的权重与各枪可见手臂不同，部分肩臂顶点含较大躯干影响，换弹时局部被拉扯。按同侧原生裸臂三角面的重心权重重新分配衣袖、金属袖口和内衬。保留内收黑色收边、袖口几何及共享轻摆参数。', '',
'201 保留 ADS34 右肩区域专用修复，沿用此前左腕收边几何。ASH12、M16 重新将衣袖输送到各自参考姿态；ASH12 肘部单独平滑，距肘部 10 cm 外不参与该平滑。', '',
'## 逐动作离线排查','',
'以实际 UE 压缩动画在 10 Hz 加首尾帧采样，使用保存后 LOD0 权重计算蒙皮。统计外层衣袖边长相对参考姿态的最大拉伸倍率（忽略原参考长度不大于 1 mm 的边）。数值是定位局部形变的指标，不是穿模面积或视觉验收结论。', '',
'| 配置 | 换弹动画数 | 采样帧数 | 修复前最大倍率 | 修复后最大倍率 |', '|---|---:|---:|---:|---:|']
for rig in sources:
 rows=report[rig].values();lines.append(f"| {rig} | {len(report[rig])} | {sum(x['samples'] for x in rows)} | {max(x['before_max'] for x in rows):.2f} | {max(x['after_max'] for x in rows):.2f} |")
lines+=['',f"合计 {sum(len(v) for v in report.values())} 条动画，{sum(sum(x['samples'] for x in v.values()) for v in report.values())} 个采样帧。包含普通/空仓、弹鼓、各握把、201 布弹箱、左轮逐发/快速及双持左右手换弹。各条动画具体路径和对应结果见 `SourceAssets/ChainmailReloadFit20260929/sources.json` 与 `diagnosis.json`。",'',
'## 范围限制','',
'未启动 UE 编辑器界面或游戏；没有进行运行时 IK、镜头、LOD 切换或穿模面积验收。离散采样不能保证帧间绝无形变，仍需用户在游戏中复测。这里报告的是已保存资产与逐动画离线对比，不宣称视觉问题已全部验证消失。','',
'## 重制顺序','',
'`collect.py`（UE commandlet）→ `author.py`（Blender 后台）→ `smooth_ash.py`（Python）→ `install.py`（UE commandlet）→ `diagnose.py`（Python，自动使用保存后权重）→ `publish.py`。', '',
'新资产目录：`/Game/Characters/ModularOutfit20260924/ChainmailReloadFit20260929/`。旧资产保留，发布前配置快照位于同名 SourceAssets 目录。']
(P/'Docs/Characters/chainmail-reload-fit-20260929.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('CHAINMAIL_PUBLISHED',len(saved))
