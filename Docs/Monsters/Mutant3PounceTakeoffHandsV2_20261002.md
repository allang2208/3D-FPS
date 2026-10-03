# 突变体-3：起跳即完成手型与早期压腕下挥 V2

**状态更新：用户已通过游戏截图明确否定 V2 的掌面与手指朝向。最新要求是把双手方向整体反转，向前挥舞；后续修订见 `Mutant3PounceForwardFlipV3_20261002.md`。本页保留失败版本的制作与保存记录，不作为认可模板。**

2026-10-02，用户判定前版飞扑手部修订不合格，明确要求起跳时就调整手型。前版仅在蓄力中准备掌面方向，指爪下抓和压腕到腾空后 0.32 秒才启动；该版本不能继续作为认可模板。

## 本轮修改

从原身体源 `pounce_arm_refine/Mutant3_Pounce_ReferenceRake.blend` 重新制作手部旋转，不在前版翻腕上叠加修正。

- 蓄力 0.08–0.38 秒同时准备双腕掌面朝下及完整指爪下抓。蓄力仍为 0.60 秒，起跳前提前 0.22 秒准备好，持续保持到离地。
- 腾空第 0 帧已是掌心向下、指爪张开的完整下抓手型，取消原来腾空后 0.32 秒才开始卷指的延迟。
- 腾空 0.00–0.18 秒从水平掌面连续压腕至 18°，配合现有身体飞扑，起跳即开始下挥。
- 落地先延续 18°压腕及指爪姿势；0.16–0.64 秒释放局部修正，接回原收势。
- 四指额外卷曲 3°/10°/6°，拇指 1°/4°/3°，继续保留外展和拇指开口。

三段正式动画的时长仍为 0.60、0.65、0.80 秒，60 fps。每段只写入左右 Hand 与 30 根新增 Claw 指骨，共 32 根骨的旋转轨。位移、缩放从正式动画原轨保留；肩、肘、前臂、身体、骨盆、腿及其他旋转轨不写入。没有修改原生 C++、模型、蒙皮、骨架、材质、飞行轨迹或伤害合同。

## 实际保存

制作源在 `SourceAssets/Mutant3Khaimera20260923/pounce_takeoff_hands_v2_20261002/`：

- `author_takeoff_hands.py`、`Mutant3_Pounce_TakeoffHandsV2.blend`、`animations/`：重建脚本、可编辑源和三个 FBX。
- `animation_contract.json`、`authoring_basis.json`：时序、骨骼范围和复用的实际掌面基准。
- `install_takeoff_hands.py`、`production_hand_keys.json`：正式动画旋转轨安装及其原位移／缩放。
- `before_content/`：覆盖前的三段正式资产本机恢复副本，保留前版不合格结果用于追溯。
- `install_state.json`、`install-editor-02.txt`：三个正式包的实际保存回执。

目标仍是 `/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_Pounce{Windup,Flight,Land}`，运行时继续引用原路径。通过现有编辑器的 Python 桥及 `mcp_call_codex.ps1` 批次互斥完成修改和保存，没有启动新编辑器。

第一次保存被正在运行的 PIE 阻止，当时只有蓄力动画的本任务旋转轨已写入内存，尚未保存。结束已有 PIE 后，`resume_owned_tracks.py` 从已物化的手部数据续接并保存三段正式动画；没有重导入或覆盖其他包。完成标记为 `MUTANT3_TAKEOFF_HANDS_INSTALL_COMPLETE 3 production clips`。安装入口已增加 PIE 前置条件，避免再次在播放中修改到一半。

未进行游戏测试、截图、渲染或视觉验收，实际手腕形变与动作观感由用户测试。上述受许可来源约束的 Blend、FBX、uasset 和密集轨道继续仅在本机保留，不随源码公开。
