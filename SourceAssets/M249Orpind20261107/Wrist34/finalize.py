"""Write delivery evidence only after the final saved-asset runs complete."""
from pathlib import Path
import json,hashlib,datetime
r=Path(__file__).resolve().parent;project=r.parents[2];old=r.parent/'Wrist33'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
saved=read(r/'install_receipt.json');native=read(r/'native_delivered/receipt.json');surface=read(r/'geometry_review_final.json');owner=read(r/'owner_pose_review.json');payload=read(r/'payload_review.json')
wire_dir=sorted(p for p in (r/'Wire').iterdir() if p.is_dir())[-1];wire=read(wire_dir/'receipt.json');host=read(wire_dir/'host.json');client=read(wire_dir/'client.json')
assert saved['complete'] and len(saved['saved'])==6
assert len(native['cases'])==48 and native['failures']==0 and all(x['passed'] for x in native['cases'])
assert len(surface)==12 and all(x['finite'] for x in surface.values())
assert min(s['min_convex_clearance_cm'] for x in surface.values() for s in x['box_samples'])>=0
assert not payload['failures'] and len(payload['cases'])==65
assert wire['passed'] and host['passed'] and client['passed'] and len(host['cases'])==24 and len(client['cases'])==12
expected=read(old/'Followup/state.json')['saved_hashes']|read(old/'Followup/entry_saved.json')['saved']|saved['saved']
actual={p:sha(project/'Content'/(p.removeprefix('/Game/')+'.uasset')) for p in expected}
assert actual==expected,'Saved input changed after review; retain it.'
remote=[x for x in host['cases'] if x['owner']=='client']
delivery=dict(date=datetime.datetime.now().isoformat(timespec='seconds'),formal_assets_saved=True,
    saved_profiles=saved['saved'],source_mesh_weights_fingers_and_bone_dimensions_unchanged=True,
    unchanged_tracked_assets=len(expected)-6,asset_hashes=actual,
    allowed_rotation_bones=['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l'],
    backups=[p.name for p in r.glob('before*.zip')],
    build=dict(new_cpp_change=False,existing_review_build='Saved/BuildEditor/build-20261110-210205.log',dll_sha256=sha(project/'Binaries/Win64/UnrealEditor-FPSGAME.dll')),
    payload=dict(cases=65,failures=0,receipt='payload_review.json'),
    native=dict(cases=48,failures=0,receipt='native_delivered/receipt.json',rates='30/60/120 FPS and intermittent 120 ms hitch'),
    surfaces=dict(cases=12,pose_frames=sum(x['frames'] for x in surface.values()),surface_samples=sum(len(x['box_samples']) for x in surface.values()),sampled_vertices_inside_box_hull=0,receipt='geometry_review_final.json',scope='Selected actual morphed left forearm/hand vertices versus visible ammo-box hull, not every triangle at every frame.'),
    owner=dict(cases=len(owner),frames=sum(x['frames'] for x in owner.values()),near_plane_skin_vertices=sum(x['owner_camera_near_plane_vertices'] for x in owner.values()),receipt='owner_pose_review.json',scope='Native camera-component projection, not rendered gameplay acceptance.'),
    multiplayer=dict(passed=True,unique_owner_cases=24,server_observed_client_cases=len(remote),minimum_remote_samples=min(x['remote_samples'] for x in remote),wrong_remote_equipment_frames=sum(x['remote_wrong_equipment_frames'] for x in remote),receipt=str((wire_dir/'receipt.json').relative_to(r)),lag_ms_each_peer=80,loss_percent_each_peer=2,scope='Local UDP listen host/client with production profile transport and body state; NullRHI, no dedicated/public-network/reconnect test.'),
    visual_review='Final native morphed wrist/palm close views; user feel acceptance pending.',
    manually_viewed_native_images=['base_hold','vertical_hold','tactical_vertical_hold','tactical_vertical_hold_palm','angled_hold','canted_hold','prism_hold','prism_hold_palm','prism_entry','prism_travel'],
    editor_opened=False,pie_started=False)
(r/'delivery.json').write_text(json.dumps(delivery,indent=2,ensure_ascii=False),encoding='utf-8')
text=f'''# M249 左腕返修：只调整认可手模的关节

2026-11-10。六份正式握姿配置已保存，后台实际蒙皮和联机复核完成。UE 保持关闭，游戏手感交由用户检查。

用户指出 Wrist33 的战术垂直握把近景仍有腕部拧折、收窄。本轮遵照“使用认可源手、只调整关节”：保留 V9 网格、权重、基础动画、骨长、比例和手指抓握，只写左侧锁骨、上臂、前臂、辅助旋转骨及手腕的局部旋转。局部位置、缩放及其他骨骼的旋转没有改变。

按真实握把轴调整支撑方向，再由肩肘关节衔接，覆盖原厂、垂直、战术垂直、斜握、侧倾和棱形六种实际配置；脚架共用的基础持握配置同步写入。基础操作动作和时钟保持，离手/回握以连续关节旋转交接。

棱形第一次实际复核发现旧离手前移与新关节姿态叠加，导致臂展比超过 1 并短暂翻转。已用新关节轨道替换旧起手修正，未增加骨长或拉伸；起手臂展比回到约 0.949。离手段补入平滑肘部绕行，掌部位置误差小于 0.000004 cm、朝向误差小于 1e-8 度；局部位移和缩放仍不改变。回握在原手重新贴合时完整接入新握姿，消除临近结束仍混用旧折腕的情况。

## 最终证据

- `payload_review.json`：65 个动作组合，局部位移、缩放、非负责旋转及手指姿态检查，零失败。
- `native_delivered/receipt.json`：六配置 × 两类换弹 × 30/60/120 FPS/120ms 间歇卡顿，共 48 组，零失败；覆盖待机、瞄准、普通/空仓换弹、回握与重复镜像应用。
- `geometry_final/`（其他配置）、`geometry_prism_final/`（棱形终版）、`geometry_review_final.json`：12 组、{delivery['surfaces']['pose_frames']} 帧、{delivery['surfaces']['surface_samples']} 次实际蒙皮表面采样，采样左前臂/手部顶点未进入可见弹箱凸包。此结论不等于全时间、全三角形碰撞证明。
- `owner_pose_review.json`：{delivery['owner']['frames']} 帧，未发现近裁剪面皮肤穿入；这是相机组件投影检查，不冒充带渲染的游戏手感。
- `{delivery['multiplayer']['receipt']}`：本机 UDP listen host/client 各 12 组，共 24 个独立持枪者用例，通过。每端配置 80ms 延迟和 2% 丢包；装备配置、瞄准/换弹、结束归位和远端接触状态通过，服务器观察客户端配置错误帧为 0。
- `views/`：`*_hold.png`、`*_hold_palm.png`、`*_entry.png`、`*_travel.png` 为实际 UE 蒙皮输出的中性材质近景。带 `candidate` 的文件是早期线性蒙皮候选，不作为最终图。

正式资产路径、哈希和备份见 `install_receipt.json`、`delivery.json`。本轮 {len(expected)-6} 项其他受跟踪资产（包括源手模、基础动画和握把模型）哈希保持不变。没有新增 C++ 改动，复用已成功构建的检查入口 DLL。

制作复现顺序为 `author.py` → `fit_prism_entry.py` → `check_payload.py`；棱形肘部绕行不能省略，也不能对已加过绕行的 payload 重复叠加。`fit_hold.py` 与 `fit.json` 保存支撑关节拟合，`prism_entry_arc.json` 保存离手绕行及掌部补偿回读。安装前保留现有资产并核对回执，勿直接覆盖后续任务修改。

未打开编辑器或 PIE。曾因用户重新进入 PIE 导致首次保存被拒绝，已保留现场并在用户保存关闭后完成；后台脚本的 LevelEditor 查询不适用于 commandlet，已移除，并改为进程入口检查。早期 `geometry/`、`native/` 保留为返修过程证据，最终使用 `geometry_final/`、`geometry_prism_final/`、`native_delivered/` 和本页列出的联机目录。

未做公网、专用服务器或重连验证。最终自然度与游戏手感待用户验收，历史数值 PASS 不再当作用户视觉认可。
'''
(r/'README.md').write_text(text,encoding='utf-8')
p=old/'README.md';prior=p.read_text(encoding='utf-8-sig');notice='> 本轮持握视觉被用户指出仍有拧折，已继续按“认可源手、只调关节”返修。当前结果见 [Wrist34/README.md](../Wrist34/README.md)；下文保留为历史记录。\n\n'
if notice not in prior:p.write_text(prior.replace('\n\n','\n\n'+notice,1),encoding='utf-8')
pd=read(old/'delivery.json');pd.update(historical_receipt=True,visual_hold_rejected=True,superseded_by='../Wrist34/delivery.json');(old/'delivery.json').write_text(json.dumps(pd,indent=2,ensure_ascii=False),encoding='utf-8')
print('M249_JOINT_DELIVERY_COMPLETE',len(expected),'hashes; 65 payload; 48 native; 24 UDP owner cases')
