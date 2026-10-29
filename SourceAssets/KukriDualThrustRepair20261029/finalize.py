"""Write the completed local handoff after saved-pose checks and publication."""
import hashlib,json
from pathlib import Path
from datetime import datetime
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
checks=read('source-checks.json');saved=read('saved-checks.json');assets=read('assets-saved.json');publication=read('published.json')
assert not checks['failures'] and not saved['failures'] and assets['complete']
config=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'));manifest=[]
for label,d in assets['bodies'].items():
    active=config if label=='jason' else config['body_variants'][label]
    for role,asset in d['clips'].items():
        assert active['clips'][role]==asset
        path=ROOT/'Content'/(asset.removeprefix('/Game/').split('.')[0]+'.uasset')
        raw=path.read_bytes();manifest.append({'body':label,'role':role,'asset':asset,'file':str(path.resolve()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
receipt={'completed_at':datetime.now().astimezone().isoformat(),'assets':manifest,'source_checks':len(checks['checks']),
    'saved_checks':len(saved['checks']),'failures':0,'native_cpp_changed':False,'first_person_changed':False,
    'gameplay_clock_changed':False,'editor_started_by_task':False,'pie_started_by_task':False,'multiplayer_runtime_tested':False,
    'runtime_final_pose_verified':False,'config_receipt':publication['transaction']}
(OUT/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
before=read('before-metrics.json');after=read('after-metrics.json')
worst_step=max(c['value'] for c in checks['checks'] if c['case'].endswith('no rotational frame jump'))
error=max(c['source_rotation_error_degrees'] for c in saved['checks'])
report=ROOT/'Docs/Weapons/kukri-dual-thrust-repair-20261029.md'
report.write_text(f'''# 双持弯刀第三段突刺修订 — 2026-10-29

Jason、Kaitlin 两套第三人称 `Kukri.FullBody.Dual.Thrust` 已保存并接入 `ThrustNaturalV220261029/A_Kukri_Dual_Thrust_NaturalV2`。本批只更新这两个配置叶节点与对应动画资产，未修改第一人称、单持第三段、伤害、攻速、位移和网络消息，也无需编译 C++。

## 定位结果

当前双持第三段仍使用 `DualCombat20261028`。它把第一人称画框中的双臂轨迹拟合到完整身体，长时间保持双肘横抬，主要伸臂发生在作者时间 0.54–0.60 秒，接触时肘部仍约弯曲 40°。

当前 `items.json` 中弯刀的 `attack_seconds` 是 0.8 秒，旧 `KukriRhythm.h` 注释中的基础速率 0.64 已不能代表当前目录。代码没有对第三人称重复乘攻速；当前目录对应基础作者播放速率 `(38/30)/0.8 = 1.5833`。旧版主要伸臂约 38 ms，的确很容易看不清。装备实例、强化及增益仍可能改变实际速度。

## 修订

- 重做两侧肩、肘、前臂与手腕整链，双肘从身体两侧较低的位置推进；刀柄固定在原生握持内，改为自然侧握。
- 将主要推进分配在 0.30–0.60 作者秒，当前目录基础速度下约 190 ms；0.60–0.80 作者秒保留伸展，之后平顺回收。
- 接触时肩腕距离约为实际臂长的 97.5%，肘部约弯曲 25.7°，保留自然活动余量，不锁死关节。
- 伸展超过臂长 90% 的可见阶段从约 0.28 延至 0.44–0.46 作者秒。保留已有 2.05 秒作者总长、0.60 秒接触、0.72 秒释放及现有下半身支撑。
- 修订过程中查出左手回收跨 180° 时逐帧最短路径插值换向；现在整段选用连续旋转分支，消除跳帧，并重新生成原生前臂扭转辅助骨。
- 首尾接入当前双持待机。第二段实际尾帧与此待机的手臂旋转差 Jason 约 0.154°、Kaitlin 约 0.071°。

## 检查与落盘证据

42 项源动作检查通过，包含原生骨段与缩放、手腕、伸展、逐帧位移、逐帧旋转、首尾衔接、双手间距和命中时钟。两套源动作手腕最大折角约 43°；120 Hz 作者采样下，所查手臂/手腕/扭转辅助骨最大相邻帧旋转 {worst_step:.2f}°。

两条 UE 保存资产已读取压缩姿态并通过对照，最大旋转压缩误差 {error:.3f}°，骨架与 `NativeSwordGrip`、`Contact`、`Release` 标记匹配。配置经共享事务只改两项，随后重新读取确认指向新包。

[保存及哈希汇总](../../SourceAssets/KukriDualThrustRepair20261029/delivery.json) · [源动作检查](../../SourceAssets/KukriDualThrustRepair20261029/source-checks.json) · [保存回读检查](../../SourceAssets/KukriDualThrustRepair20261029/saved-checks.json)

## 预览与边界

[Jason 双持第三段预览 GIF](../../SourceAssets/KukriDualThrustRepair20261029/Preview/jason-after-Kukri.FullBody.Dual.Thrust.gif)

GIF 为离线原生动作预览，按当前目录基础攻击速度播放；首尾额外停留便于循环观看，不代表游戏停顿。它不是慢放或实机录像。归一化 Kaitlin 网格的预览出现身体接缝显示问题，原因未在本批确认，不据此宣称服装适配通过。

没有启动编辑器或游戏，没有运行真实客户端联机，未采集此次修改后的最终游戏姿态。用户下次进入游玩会读取新配置；实际观感、运行时层以及不同服装仍以游戏内观察为准。
''',encoding='utf-8')
print(json.dumps({'report':str(report),'assets':len(manifest),'source_checks':len(checks['checks']),'saved_rotation_error':error},ensure_ascii=False))
