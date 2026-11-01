"""Collect completed receipts; never turn a failed/incomplete run into a pass."""
import json,datetime
from pathlib import Path
P=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
native=[]
for name in ('heavy-formula','thor-assets-mods','zhenting','recall','switch','preview','storm-lifecycle'):
    data=read(P/(name+'.json'))
    failed=data.get('failures',data.get('failed'))
    assert failed==0,(name,failed)
    native.append(dict(case=name,checks=len(data['checks']),failures=failed,receipt=name+'.json'))
grips=read(P.parent/'ConductiveGripAudit20261101/audit.json')
assert grips['passed'] and grips['failures']==0
native.append(dict(case='conductive-grips',checks=grips['count'],failures=0,receipt='../ConductiveGripAudit20261101/audit.json'))
network=[]
for mode in ('Listen','Dedicated'):
    folder=max(P.glob(mode+'-*'),key=lambda x:x.name)
    receipt=read(folder/'receipt.json');result=read(folder/'host.json')
    assert receipt['passed'] and result['passed'] and len(result['cases'])==11,(mode,folder)
    network.append(dict(mode=mode,cases=len(result['cases']),passed=True,receipt=str((folder/'receipt.json').relative_to(P)),results=str((folder/'host.json').relative_to(P)),lag_ms_each_peer=60,loss_percent_each_peer=3))
assert read(P/'build_receipt.json')['exit_code']==0
assert read(P/'seat_tangent_receipt.json')['saved']
report=dict(date=str(datetime.datetime.now()),scope='Thor hammer complete feature audit, emphasizing multiplayer',
    fixes=[
        dict(issue='GuanLei actor replication crashed the server: RecallAt/CaughtAt were not reflected',files=['Production/ThunderHammerThrown.h']),
        dict(issue='Shared lightning arc had the same unreflected NetBrightness/NetChargeRatio fields',files=['Skills/FPSLightningArc.h']),
        dict(issue='100ms catch phase could be skipped before actor destruction under network loss',fix='Ordered reliable catch receipt; existing one-shot guard prevents duplicates',files=['Production/ThunderHammerRecall.cpp','Production/ThunderHammerRecallAudio.cpp']),
        dict(issue='Catch/flight audio waited for the entire high-resolution visual load',fix='Independent high-priority sound load plus equipped-weapon preloading',files=['Production/ThunderHammerThrown.cpp','Production/ProductionToolComponent.cpp']),
        dict(issue='Outbound hammer could fall past world bounds and leave the weapon permanently away',fix='Authority retires below KillZ/outside bounds; grounded hammers still have no timeout',files=['Production/ThunderHammerThrown.cpp']),
        dict(issue='Recall and heavy shockwave used incomplete friendly filtering',fix='Use shared enemy predicate, including companion/team protection',files=['Production/ThunderHammerRecall.cpp','Production/WarhammerShockwave.cpp']),
        dict(issue='JiLei V14 mesh suffix no longer matched the aura finder',files=['Production/ProductionStormDriveLightning.cpp']),
        dict(issue='LeiXi buff replicated but remote equipment core brightness was not updated',files=['Production/ThunderHammerPommel.cpp','Production/ProductionStormDriveLightning.cpp']),
        dict(issue='Approved GuanLei V12 closed-crown model was not published; catalog still used V9',fix='Saved V12 mesh/PBR and regenerated the matching framed production icon; updated the actual catalog'),
        dict(issue='GuanLei collapsed UVs and both seats invalid tangent frames/fallback settings',fix='Repaired 32717 UV polygons; baked orthogonal tangents while retaining original source geometry/normals; explicitly selected full-detail Nanite fallback',evidence='seat_tangent_receipt.json'),
        dict(issue='Prior conductive-grip audit found duplicate listen-host release procs, mutable item snapshots, stale field pulses, missing remote grip profile and arc publication dependent on cosmetic loading',evidence='../ConductiveGripAudit20261101/repair.json')],
    contracts=[
        'Heavy attack multiplier follows player heavy-strike skill level.',
        'GuanLei landing = heavy physical component + native lightning magic component; native lightning uses 100% magic attack with the applicable damage modifiers, without a second heavy multiplier.',
        'JiLei converts the ordinary heavy plus its native lightning into the intended magic payload once.',
        'Native, thrown and JiLei lightning add 2 electrified stacks; overload threshold is 5. Echo adds 0.25s to base overload stun and retains 2 stacks.',
        'LeiXi grants existing magic inspiration for 10s; additional receipts refresh, never stack.',
        'ZhenTing extra strikes use diameter spacing and 0.25/0.50/0.75s sequencing; committed launch direction and item snapshot survive switching.',
        'Switching active slots preserves the equipped thrown instance. Removing it from equipment retires the world actor.',
        'Recall is nonblocking and lasts 1s; each enemy is hit once. Beyond 60m the entire return is transport only.',
        'Static Field and Coil use enemy-only targeting and authoritative release/pulse processing.'
    ],validation=dict(editor_build='Succeeded',native=native,native_total=sum(r['checks'] for r in native),network=network,
        saved_seat_basis_invalid_axes=0,gui_editor_opened=False,profiles='Isolated audit profiles; UDP peers use private per-run UserDir save roots'),
    limits=[
        'NullRHI/NoSound network runs check actors, RPCs, status/damage and audio event dispatch. They do not accept rendered hand animation, material appearance or audible mixing.',
        'Wire fixtures seed deterministic profiles and exercise production combat RPCs; complete inventory UI/profile-upload transactions are not covered.',
        'Level-transition cleanup was checked via EndPlay fixture, not live ServerTravel. Rejoin/late observer joins and more than one client were not exercised.',
        'No FPS/VRAM benchmark. Both seats retain their detailed Nanite source and full-detail fallback; this is not a low-poly optimization claim.',
        'Earlier failed receipts are retained. Test-only fixes covered initial queued movement, unresolved target references, duplicate delegate binding and counting previous fading effects.'
    ])
(P/'review_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {r['case']} | {r['checks']} | 0 |" for r in native)
netrows='\n'.join(f"| {r['mode']} | {r['cases']} / {r['cases']} | [{r['results']}]({r['results']}) |" for r in network)
text=f'''雷神之锤检查与修复记录（2026-11-01）

已完成本轮代码、保存资产与后台联机检查。后台编译成功，{report['validation']['native_total']} 项隔离检查通过；监听主机和专用服务器各 11 个独立进程联机场景通过。每端配置 60ms 延迟、3% 丢包。完整条目见 [review_report.json](review_report.json)。

主要修复：投掷锤和共用电弧的复制字段遗漏、接锤回执丢失、音效等待模型加载、飞出世界边界后无法恢复、友方过滤不全、疾雷 V14 环绕闪电识别、远端雷吸亮度更新。前一阶段静电场和线圈的服务器重复触发、状态快照和外观同步修复也纳入记录。

贯雷之前仍引用 V9，本轮已把批准的 V12 闭合顶冠、PBR 和对应图标接入实际目录。贯雷与疾雷的 UV/切线和 Nanite 回退设置已修复、保存，重新读取后的切线异常计数为 0。原始几何、顶点法线和接口保留。

| 隔离检查 | 数量 | 失败 |
|---|---:|---:|
{rows}

| 真实 UDP 模式 | 通过 | 回执 |
|---|---:|---|
{netrows}

联机场景包括：投掷及四道落雷、切换保留、切回召回与一次接锤音效事件、再次投掷、卸下清理、疾雷资源与四道落雷、回响与雷吸状态、静电场感电、线圈伤害与电弧复制、退出连接清理。

本轮使用无画面、静音进程，不代表动作观感或音效听感验收；完整背包界面交易、中途加入/重连、实际服务器换图和帧率测试未覆盖。两款锤座保留高精度源模型与完整回退网格，不宣称已做低模优化。
'''
(P/'README.md').write_text(text,encoding='utf-8')
print('THOR_REVIEW_COMPLETE',report['validation']['native_total'],[(r['mode'],r['cases']) for r in network])
