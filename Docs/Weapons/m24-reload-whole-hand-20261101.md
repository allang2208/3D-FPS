# M24 换弹整手复用交付（2026-11-01）

> **已按用户要求撤回（2026-11-01）**：本整手版本不再生效。10 个配置、20 个换弹分支已恢复到最初改手指前的左手轨道，脚架及其他动作保留。实际保存回执：`SourceAssets/M24ReloadDonor20261101/rollback_whole_receipt.json`。以下制作、检查与录像均为已撤回版本的历史记录；本次回退未运行游戏测试。

用户在拇指单独复用方案未达到要求后，明确授权“复用整只左手抓匣姿态，继续完成”，并要求完成后自行检查。本次已实际保存 10 个握姿资产中的 20 个普通／空仓换弹分支。

## 最终动作

采用 SKILL 已记录认可的 `SVDThumbUp20260923` 整手抓匣供体及 UE 原生 `A_SVD_reload` 指节曲线。保留供体五指相对关系，按弹匣真实截面配准掌腕，连同肩肘、前臂方向和松手轨迹适配 M24。没有采用被否定版本的拇指 Euler 修正，也没有对单个手指进行角度拟合。原厂 5 发与 10 发弹匣共用上段接口，使用同一组最终握点。

制作过程中确认 M4 的实际换弹入口覆盖为 `ExtMagContact20260919`，早期列出的 TacticalToss / SlapImpact 基础动画不是现行整手抓握。M4 候选的尺寸与腕臂适配不如最终 SVD 候选，未发布；保留在 `SourceAssets/M24ReloadDonor20261101/M4WholeTrials/` 追溯。

最终仅合入左锁骨以下的左手链旋转及左手 IK 目标。变形骨的局部位移、缩放、骨长保持原有数据；右手、枪根、弹匣、机械事件、时长及非换弹条目保留。前一轮脚架修改也保留，本轮没有修改 C++。

## 已保存范围

- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip`、`DA_M24_Mag10`。
- `/Game/Weapons/M24/ReceiverGripRebuild20261031/Profiles/DA_M24_skeleton_base`、`DA_M24_skeleton_mag10`，以及各自的 `_balanced`、`_phantom`、`_stable`。
- 每个配置均包含 `A_M24_reload` 和 `A_M24_reload_empty` 两条换弹。

发布前备份为 `SourceAssets/M24ReloadDonor20261101/BeforeWholePublish/`。发布只合并目标轨道，未整包覆盖旧资产或其他会话的非目标动作。

## 本次检查结果

1. 后台 UE commandlet 实际保存 10 个资产；独立进程重新读取，全体条目与预期一致。
2. 20 个分支重建保存后的骨骼姿态，最大位置偏差 0.023 mm，骨段长度偏差小于 0.009 mm。
3. 以本次读取的原生裸手蒙皮复核 5 发／10 发关键接触与过渡帧，拇指对机匣和弹匣的抽样最小净空约 12.84 mm；该数值仅针对拇指抽样，不表示所有网格之间绝对无相交。
4. 独立审查存档运行后台 `-game -RenderOffscreen`，完成现有 M24 动态检查夹具，生成 1085 张实际画面。重点查看普通／空仓换弹的伸手、抓匣、插入和回握，未复现前次明显的拇指扭曲及腕部折叠。
5. 普通／空仓各取 37 个抓匣运行时样本，实际手掌相对枪根位置与新保存姿态最大误差 0.035 mm；与回退版的平均差约 53.7 mm，确认新轨道实际生效。普通换弹弹量 4→5，空仓 0→5。

运行时回放使用原厂 5 发配置；其他握把和 10 发配置完成资产读回、骨骼与离线接触检查，未逐配置做游戏回放。本轮没有检查音频或联机。未打开 UE 编辑器；隔离游戏进程已自行退出，未使用用户存档。

## 证据与制作入口

目录：`SourceAssets/M24ReloadDonor20261101/`。

- `publish_whole_receipt.json`：实际保存回执。
- `readback_receipt.json`、`saved_pose_check.json`：独立读回与 20 分支姿态检查。
- `whole_contact.json`：原生手部蒙皮接触抽样。
- `WholeHandFinal_2206/runtime.json`、`runtime_pose_match.json`：实际运行与姿态生效证据。
- `M24_WholeHand_Normal_Empty.mp4`：普通／空仓换弹实际画面录像，无音频，按记录时间合成。
- `whole.py`、`whole_registration.json`、`author_whole.py`：最终动作生成与烘焙。
- 重新制作顺序为 `read_whole_donor.py` → `register_whole.py` → `fit_registered_grip.py` → `select_grasp.py` → `author_whole.py`。最终选中的配准结果已保存在 `whole_registration.json`；发布与检查入口均需显式执行，制作脚本不会自动启动游戏。
