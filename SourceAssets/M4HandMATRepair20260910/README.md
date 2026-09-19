# M4 手部形变修正与 MAT 编辑入口

2026-09-10。保留现有 M4、Manny 手臂、材质和枪械层级。

## 已接入游戏

替换 `/Game/Weapons/M4HK416Replica/` 下的 `A_M4_HK416_reload`、`A_M4_HK416_reload_empty`、`A_M4_HK416_equip_charge`。原资产备份在 `Before/`。没有修改 C++、模型、蒙皮权重或音效文件。弹鼓动作仅导入本目录的候选区；没有覆盖并行任务的弹鼓握持资源。

上一版把不同骨架的手掌/手指旋转直接叠加，部分指尖弯折超过 140°，参考过渡帧还含单帧大幅旋转。单独限制腕角或重新求解肘部仍会破坏接触与连续性，因此最终采用 `repair_authored.py`：保留原 M4 作者的手腕、前臂及扭转骨关系，用关键接触姿态驱动整条第一人称手臂，再重建局部手指动作。肩部使用第一人称自由控制，不能直接作为第三人称全身动画使用。

普通换弹采用原 M4 的有效弹匣握姿；空仓释放采用自然弯曲的指节，并对实际蒙皮表面计算枪身外侧绕行距离；装备采用两指钩住后部拉柄的姿态，平滑参考过渡帧的枪身姿态。普通换弹 2.1 秒、空仓 2.7 秒、装备源片段 38/60 秒，装备游戏时长仍由已有逻辑控制为 0.62 秒。机械部件行程和既有音效事件时间保持一致。

## 可编辑文件

- `M4_Hand_MAT_Editable.blend`：最终可编辑骨架、网格、五个 `M4_MAT_*` 候选动作。
- `repair_authored.py`：最终生成脚本；`release_path_clearance.json`：按实际手套表面拟合的空仓绕行曲线。
- `A_M4_MAT_*.fbx`：导出动画。
- `/Game/Weapons/M4HandMATRepair/CR_M4_Hand_MAT`：具备正解、反解的 FK Control Rig。
- `/Game/Weapons/M4HandMATRepair/LS_M4_Hand_reload`、`LS_M4_Hand_reload_empty`、`LS_M4_Hand_equip_charge`：60 fps 的可编辑序列。

`repair.py` 是被放弃的单独 IK/限角实验，不是交付生成入口。E 盘最初的同名暂存目录也不是最终版本。重新生成请运行本目录的 `repair_authored.py`；重拟合绕行曲线应从没有已有曲线位移的基线计算，不能在已位移结果上重复累加。

## MAT 手册与已验证操作

官方说明：[Locodrome MAT / Fab](https://www.fab.com/listings/843baea2-8298-4b07-8db2-7ca18b026b7c)，[作者页面](https://locodrome.gumroad.com/l/Metahuman_Animation_Tool)。MAT 是编辑器工具控件，用来辅助 Sequencer/Control Rig 操作，不会自动修复任意网格的蒙皮。

1. 打开上述任一 `LS_M4_Hand_*` 序列。
2. 在 `/Game/Locodrome/MAT/` 对 `Locodrome_MAT` 执行 **Run Editor Utility Widget**。
3. 在 MAT 的 Rig 列表选择 `CR_M4_Hand_MAT`；必要时刷新。仅打开骨骼网格不够，序列必须含 Control Rig 轨道。
4. 选择 `hand_l_fk_ctrl` / `hand_r_fk_ctrl` 或 `index_02_l_ctrl` 等手指控制器。在正确帧使用 MAT 的微调和关键帧操作。
5. 本次实测第 115 帧的左食指控制器，MAT 的 W 将角度从约 -36.999° 改为 -35.999°，S 恢复原值，见 `mat_nudge.json`。测试变动已恢复。选骨、关键帧调用和序列保存均已验证；Tween 在当前密集烘焙曲线上的测试未产生数值变化，不能作为 Tween 已修改动作的证据。

这个定制架目前只有 FK。MAT 的 MetaHuman 专用 Keep Aligned、手指自动插值及完整 FK/IK 切换依赖对应控制通道；当前架没有这些通道，不应启用，也没有宣称本次已经使用这些功能。

## 验证与预览

- `published_pose_validation.json`：游戏资源与已检查候选逐帧一致性。
- `deformation_validation.json`：120 Hz 采样关节旋转；最终三个动作最大半帧局部变化约 5.0–6.5°，没有上一版的大幅瞬时反折。
- `surface_validation.json`：空仓释放 2.0–2.283 秒的实际左手套表面与机匣侧面检查；最小间隙约 0.75 mm，接触帧距目标约 1.42 mm。此项不是全动画、全角色的碰撞证明。
- `import_report.json`：时长、压缩误差、Control Rig 序列烘焙。
- 实际 UE 运行：`m4-mat-repair-av60` 50 项、`m4-mat-repair-equip` 20 项通过。运行断言不代替视觉质量判断。
- 实际混音检测：11 个换弹事件、2 次装备音效和开火波形均匹配原 HK416 音源；无削波。音频输出仍有混音缓冲延迟。
- `Delivery/` 两个视频来自同一次实际游戏画面与混音录音，20 fps 截图采样；少量缺帧沿用前一帧，具体见 `preview_manifest.json`。没有按事件重新拼接替代录音。

如果另一个已经打开的 UE 编辑器仍显示旧动作，需要重新加载这些动画资源或重启该编辑器。当前修改没有要求重新编译原生模块。
