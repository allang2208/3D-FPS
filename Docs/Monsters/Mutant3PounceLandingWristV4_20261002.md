# 突变体-3：落地手腕衔接 V4

2026-10-02，用户确认 V3 起跳和空中的手部方向正确，但指出落地瞬间手掌方向和手腕扭曲。本轮范围限定为落地动画的左右手腕；已认可的蓄力与腾空正式资产不写入。

V3 落地手腕继承了 V2 的掌面向下定向与压腕，并继续叠加 180° 翻掌；两层修正又在落地 0.16–0.64 秒同时释放。本轮移除落地段这两层旋转，恢复 `pounce_arm_refine/Mutant3_Pounce_ReferenceRake.blend` 内与同帧肩、肘、前臂配合的原始局部手腕旋转，从落地第 0 帧即使用自然腕姿。

实际落地仍通过原生 `Landed` 进入落地阶段。保留现有 0.14 秒上身姿态快照过渡，空中的实际姿势由该过渡接入自然落地动作；没有增加瞬时手腕覆盖或另一套落地计时。

- 只写 `A_Mutant3_PounceLand` 的 `LeftHand`、`RightHand` 两条旋转轨。
- 落地指型、指间外展、肩肘前臂、身体、脚部及全部位移／缩放保留正式资产原值。
- 落地时长仍为 0.80 秒，60 fps、0–48 帧；伤害、飞行轨迹、回收与恢复时序不变。
- 未修改 C++、模型、蒙皮、骨架或材质，本轮无需原生构建。

## 制作与保存

目录为 `SourceAssets/Mutant3Khaimera20260923/pounce_landing_wrist_v4_20261002/`。

- `author_landing_wrist.py`、`Mutant3_Pounce_LandingWristV4.blend`：制作脚本和可编辑源，源内继续保留 V3 的起跳与腾空动作。
- `animations/A_Mutant3_PounceLand.fbx`：仅导出落地片段，用作临时旋转轨输入。
- `animation_contract.json`：本轮范围、源路径、覆盖前目标散列与未测试状态。
- `install_landing_wrist.py`、`production_hand_keys.json`：导入临时动画、仅写双腕旋转，并保留正式资产原位移和缩放。
- `before_content/`、`install_state.json`、`install-editor-01.txt`：安装生成的覆盖前恢复副本、保存状态和桥回执。

目标为 `/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_PounceLand`。制作源、落地 FBX 及正式落地动画均已保存；桥回执为 `success=True`，完成标记 `MUTANT3_LANDING_WRIST_INSTALL_COMPLETE 1 production clip`。仅写入落地双腕旋转，起跳与腾空正式包未写入。接入通过当前编辑器与桥的批次互斥完成；取得窗口时编辑器处于可保存状态，本轮没有结束试玩、开启新编辑器或新试玩。

未进行游戏测试、截图、渲染或验收。用户对 V3 的认可范围仅为起跳和空中方向，本轮落地效果仍由用户测试。Blend、FBX、uasset 与密集动作轨道继续遵守现有 Khaimera／Meshy 来源许可，仅在本机保留。
