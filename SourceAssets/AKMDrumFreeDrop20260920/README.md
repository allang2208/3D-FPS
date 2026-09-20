# AKM 大弹鼓自然掉落与装入抓握 · 2026-09-20

用户反馈升级鼓壳在 AKM 手部拔下动作中穿模，指定取消手部拔鼓，让旧鼓自然掉落。随后提供左手托瓶照片，明确改成掌心向上、从鼓底托举；最新反馈要求四指并拢并弯曲关节形成抓握，当前修订为 `PalmGripV3`。

- 保留各握把原来的起始和回握动作、右手、枪根、机械骨骼、原时长及弹药结算。只修改 AKM 的弹鼓普通/空仓动作，覆盖 base、angled、vertical、prism、canted 共十条；战术垂直握把沿用 vertical。
- 120 Hz 作者帧 12 后左手向外退开并直接移向取弹位置，取消原来的握鼓拔出段。帧 36 从在枪上的位置释放旧鼓，初速度继承角色移动，加 20 cm/s 向下速度及轻微转动，由重力落下。保留原帧 112 的新鼓出现时点。
- 新鼓沿用当前弹匣骨骼的装入轨迹。保留 V2 的掌心与手腕位置，四指收拢、分别弯曲 MCP/PIP/DIP 包住鼓壳下缘，拇指在另一侧对握。固定骨长、缩放及掌骨，使用连续的语义屈曲轴，避免指节越过 90° 时发生翻转。
- 取弹前先张手，帧 76–112 逐指收拢，接触期间保持闭合抓握；退出的前 40% 逐渐开指，再接回各握把原动作。原四指扇形展开角与过小的屈曲值不再用于持鼓段。
- 手腕、肘和前臂同步求解，前臂 roll 跟随掌心，辅助骨随完整骨段运动，保留骨长和缩放。普通在帧 236–278、空仓在帧 220–256 退出托举；先向下和外侧让开鼓壳，再接回原回握或拉栓动作。
- 拔匣音效与释放统一到源时间 0.3 秒；其余声音、基础动作时长（400/120、515/120 秒）、倍率及补弹逻辑保留。
- 修正 `SetGunsmithMagazineAttachment`：AKM 已配置本枪弹鼓后，后续 M4 分支不再覆盖其网格和挂载。使用此前已接入的 `SM_AKM_drum` 与原 AKM socket-space 变换。

## 制作与接入

当前运行来源记录在 `source_manifest.json`。此前参考 `AKMReloadPolish20260911/Delivery/extraction-sequence.jpg`；本次用户明确要求继续检查，已查看 V2 与 V3 的实际蒙皮手模和当前弹鼓模型，评审图位于 `Revisions/PalmGripV3/BeforeRender/` 与 `Revisions/PalmGripV3/DeliveryRender/`。图中隔离了手部和弹鼓，仅用于判断姿态与接触。

当前制作入口为 `Scripts/author_palm_grip.py` → `Scripts/build_animations.py` → `Scripts/import_animations.py`。生成五个子目录中的可编辑 Blend 和 FBX，通过本机批次互斥桥 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 接入，重导入并保存至原 `/Game/Weapons/AKMDrumFreeDrop20260920/<握把>/` 路径。仅在用户要求关节检查时使用 `Scripts/import_palm_grip_and_readback.py`。本次只更新动画，无需 C++ 修改或重新编译。

旧侧握/张掌方法、V1/V2 动画备份与中间候选已归档至 `trash/attachments-grip-drum-20260920/SourceAssets/AKMDrumFreeDrop20260920/`（项目根目录下）。当前作者链所需的 V2 掌心锚点与开指参数已独立保存在 `Inputs/palm_support_anchor.json`；用户照片仍在 `Revisions/PalmSupportV2/`。正式 Blend/FBX、最终图与前后对比保留原位。

`contact_fit.json` 是制作参数，`build_receipt.json`、`import_receipt.json` 是导出/保存记录，不是游戏验收。作者 Blend 包含当前带材质鼓壳，隐藏旧鼓的时段与游戏一致；实际掉落实体由运行时物理生成。

源码接入：`FPSGAMECharacter.cpp`、`Weapons/AKMAttachmentVisual.h`、`Weapons/M4DrumVisual.cpp`；`Config/DefaultGame.ini` 将新动画目录纳入打包资源。必要常规 Editor 构建已与巫婆任务合并完成并重新打开编辑器；共享构建记录 `Saved/BuildEditor/build-20260920-005740.log`，基础 DLL 已更新。

本次只检查相关源手模接触，并在重导入时读取十条动作的左手指 SOURCE/COMPRESSED 姿态；记录分别为 `DeliveryRender/contact_distances.json` 与 `ue_finger_readback.json`，都在 `Revisions/PalmGripV3/` 下。未主动启动 PIE，未做整套实机换弹或玩法回归；最终第一人称观感由用户实测。
