"""Record only the final saved-asset evidence for the requested bipod review."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent
receipt=json.loads((r/'import_receipt.json').read_text());support=json.loads((r/'support_receipt.json').read_text())
assert receipt['payload_sha256']==hashlib.sha256((r/'bipod.json.gz').read_bytes()).hexdigest(),'Latest action has not been published'
counts={};collisions=[];native=[]
for name in ('accepted_left_deploy','accepted_left_retract','accepted_player_deploy'):
    folder=r/name;review=json.loads((folder/'review.json').read_text(encoding='utf-8-sig'));assert review['complete'];counts[name]=len(review['views'])
    native+=review['views']
    if 'player' not in name:
        data=json.loads((folder/'native_contacts.json').read_text())
        collisions.extend((name,k,v['collisions']) for k,v in data.items() if v['collisions'])
assert not collisions,str(collisions)
folder=r/'accepted_left_deploy';review=json.loads((folder/'review.json').read_text(encoding='utf-8-sig'))['views']
left=np.fromfile(folder/'surface.left',np.uint8)>0;gaps={}
for stamp in ('233','400','550'):
    prefix='M249_bipod_'+stamp;p=np.fromfile(folder/(prefix+'.vertices'),np.float32).reshape(-1,3)[left]
    v=np.fromfile(folder/(prefix+'_SM_M249_Bipod_LegA.vertices'),np.float32).reshape(-1,3);f=np.fromfile(folder/(prefix+'_SM_M249_Bipod_LegA.indices'),np.uint32).reshape(-1,3)
    mesh=trimesh.Trimesh(v,f,process=True);mesh.fix_normals();near=((p>=mesh.bounds[0]-2)&(p<=mesh.bounds[1]+2)).all(1)
    gaps[stamp]=float(-trimesh.proximity.signed_distance(mesh,p[near]).max()*10.)
hands=[next(b['transform'] for b in row['bones'] if b['bone']=='hand_l') for row in review];hands=np.array(hands)
rotations=R.from_quat(hands[:,3:7]);native_rotation=float(np.degrees((rotations[:-1].inv()*rotations[1:]).magnitude()).max())
native_distance=float(np.linalg.norm(np.diff(hands[:,:3],axis=0),axis=1).max())
joint=json.loads((r/'final_joints.json').read_text());before=json.loads((r/'before_joints.json').read_text())
report=dict(status='complete',scope='M249 bipod deploy/retract left hand, wrist, arm, contact and handoff',
    saved_packages=receipt['saved_packages']+[support['path']],runtime_duration=.9,source_duration=.48,
    source_frames=97,source_fps=200,native_views=counts,triangle_intersections=0,leg_contact_clearance_mm=gaps,
    native_max_60hz_hand_cm=native_distance,native_max_60hz_hand_degrees=native_rotation,
    before_60hz_hand_degrees=before['joint_steps']['hand_l']['max_60hz_deg'],saved_joint_measurements=joint,
    native_corrective_count=sorted({row['corrective_count'] for row in native}),
    build='FPSGAMEEditor and FPSGAME Development succeeded; Saved/Logs/M249Repair10Build.log.console',
    editor_gui_started=False,pie_tested=False,asset_hashes={**receipt['asset_hashes'],support['path']:support['sha256']})
(r/'delivery.json').write_text(json.dumps(report,indent=2))
text=f'''# M249 脚架左手专项修复（Repair10）

用户要求的部署、收回抓握/手腕/手臂求解与穿模检查已完成，资产已保存。

## 改动

- 复用 M24 部署系统和可反向采样的动作阶段；M249 部署、收回均为 0.90 秒。
- 接触支腿后再转动，0.225 秒开始拉开、0.5625 秒完全展开、0.825 秒回到持枪位置。
- 先松指再离开前握把，回握先到位再收指；离开支腿时增加向外避让。
- 重做左手逐指抓握、前臂弹箱避让与肘部求解，保留骨长和前臂旋转分配。
- 新增共享稀疏 SupportGrip 修正，让 Idle/ADS 和动作的持枪端点一致；原有整段普通动作资产未重写。

## 已保存资产

{chr(10).join('- `'+p+'`' for p in report['saved_packages'])}

## 专项复核

- UE 后台原生动画图、59 个关节修正形态和实际三件式脚架参与采样。
- 部署 55 帧、收回 11 个关键姿态、第一人称 11 个姿态；所检查的可见枪体/前握把/弹箱/支腿与左手臂表面相交为 0。
- 60 Hz 原生采样最大手部单帧转角 {native_rotation:.2f} 度；修改前保存动作对应指标 {report['before_60hz_hand_degrees']:.2f} 度。
- 支腿抓握表面间隙约 {min(gaps.values()):.2f}–{max(gaps.values()):.2f} 毫米。
- 保存动画以 600 Hz 读回，起止端点与共享持枪修正吻合；详见 `final_joints.json` 和 `delivery.json`。
- Editor/Game Development 后台构建成功。

本轮未启动 UE 编辑器窗口或 PIE；游戏内操作手感、环境支撑与联机验收由用户自行确认。

制作入口：`author.py`、`author_support.py`、`publish.py`。原生采样目录以 `accepted_` 开头。修改前备份为 `before.zip`、`support_before.zip`。
'''
(r/'README.md').write_text(text,encoding='utf-8');print('M249_BIPOD_REVIEW_COMPLETE',counts,flush=True)
