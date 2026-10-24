"""Summarize completed background checks without claiming gameplay acceptance."""
import collections
import datetime
import json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME'); W=P/'SourceAssets/KaitlinPlayer20261023'; A=W/'Audit'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
c=read(A/'config.json'); r=read(A/'assets.json')
if c['issues'] or not r.get('passed') or not r.get('complete'):
    raise RuntimeError('Do not finalize incomplete or failing checks.')
counts=collections.Counter(row['kind'] for row in r['assets'].values())
body=read(P/'Content/ColdSteelData/player_body.json')['body_variants']['kaitlin']
if not set(body['clips'].values()) <= set(r['assets']): raise RuntimeError('Live animation catalog changed during review.')
summary={'completed_at':datetime.datetime.now().astimezone().isoformat(),
         'scope':'background source/configuration checks and saved-asset readback; no game or multiplayer execution',
         'fixed':'Retargeted and published six sofa exit clips updated upstream since the original integration.',
         'config':c['counts'],'asset_counts':dict(counts),'loaded_assets':len(r['assets']),
         'config_issues':0,'asset_issues':0,'runtime_tested':False,'visual_tested':False,
         'source_changes':['Tools/KaitlinPlayer/retarget.py input override and audit scripts'],
         'runtime_changes':['player_body.json.body_variants.kaitlin.clips: six sofa exit mappings','six saved female animation packages'],
         'publication':read(A/'sofa_publication.json')}
(A/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
text=f'''# Kaitlin 后台检查记录

检查时间：{summary['completed_at']}。用户本轮明确要求“检查一遍”。全程未启动交互编辑器、游戏或 PIE。

## 发现并修复

项目的六个沙发起身源动作已升级到 `ReversedExitV7`，女性配方仍使用此前版本。已为普通／公寓沙发的中央、左侧、右侧出口重新重定向、保存，并通过字段事务更新六个女性映射。没有覆盖其他功能已经制作的女性战锤动作，也没有替换男性配置。

首次发现证据：`SourceAssets/KaitlinPlayer20261023/Audit/config_before.json`；选定源与修复前映射：`sofa_source.json`、`sofa_before.json`；落盘回执：`sofa_publication.json`。

## 已完成的检查范围

| 路径 | 结果与覆盖 |
| --- | --- |
| F6 入口 | 代码追踪：按钮调用 SetBodyType → SetHeadAndHair → 档案持久化 → 异步 ApplyAppearance；检查加载禁用、旧请求取消、身体／装备重建与切回路径。未实际点击 UI。 |
| 存档与同步 | 代码追踪头型／发型字段持久化、档案上传、服务端影子档案、ReplicatedAppearance／OnRep，以及新 pawn 初始应用。未执行主客机联机。 |
| 配置与穿戴 | {c['counts']['references']} 个资源路径存在；{c['counts']['world_owner_combinations']} 种世界／本人身体组合、{c['counts']['view_combinations']} 种第一人称组合和 {c['counts']['backpack_combinations']} 种背包组合；检查实际裤靴、裤腰、内层、皮肤选择及身体切换预加载路径。无缺项或男性身体网格误选。 |
| 身体／装备保存资产 | {counts['world']} 份衣物及背包网格：已加载，女性骨架及 342 骨骼顺序一致，参考骨骼位置和保存顶点与制作数据误差小于 0.01 cm，材质槽顺序一致、3 级 LOD。 |
| 完整身体 | 30,455 顶点、60,816 三角面；17 个覆盖分区逐面一致；3 级实际渲染 LOD 均非空。 |
| 第一人称手部 | {counts['view']} 份派生网格加载成功，与源共享原生骨架，修正形态名称集合一致，使用女性肤色材质。沿用原 V9 手型。 |
| 头脸／毛发 | 原生头脸加载成功；带权重的共享骨骼及颈头绑定位置一致；3 份 Groom 绑定均指向正确女性脸网格及毛发资产。 |
| 长袍 | 两份布料绑定和各 66 个女性碰撞胶囊读回；实际渲染 LOD 非空。未运行动态布料。 |
| 动画 | {c['counts']['animation_roles']} 个角色映射、{counts['animation']} 个独立片段：骨架、时长、播放速率、根运动标志、通知名称集合与相应源一致；8 根关键骨骼在 5 个归一化时间点读取，未出现缺失或非有限姿态。 |

共完成 {len(r['assets'])} 个目标资产的独立进程读回。`Audit/assets.json`、`routes.json`、`config.json`、`summary.json` 保存机器可读证据。

## 已排除的检查假设

- 多次切换重复注册姿态回调：切换先调用 ClearMotion 注销旧回调，再重新初始化；代码路径未发现重复累积。
- 原生脸的 pelvis／下脊柱参考位置不同：这些原型关节不直接蒙皮当前脸网格，完整 CopyPose 链会被身体替换。实际带权重的共享关节及颈头位置一致；没有为这个检查误报修改原生资产。
- 首轮部分通知检查无法读取受保护 Notifies 属性：已改用引擎公开 AnimationLibrary 接口补跑。首轮记录保留在 `assets_first_pass.json`，重查范围见 `retry_scope.json`。

## 检查边界

本轮修复只改动画资产与 JSON 映射，不涉及运行时 C++，因此未追加整项目构建。没有执行 F6 实际切换、重新进档、主客机网络、动态布料、武器接触或穿模的实机验收；配置组合检查不等于逐套视觉验证。上述结果也不涵盖后续并行任务新加入或同路径修改的资源。
'''
report=P/'Docs/Characters/kaitlin-player-audit-20261023.md'
report.write_text(text,encoding='utf-8')
print(json.dumps({'report':str(report),'assets':len(r['assets']),'counts':dict(counts),'issues':0},ensure_ascii=False))
