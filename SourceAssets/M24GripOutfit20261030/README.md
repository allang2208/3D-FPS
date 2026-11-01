# M24 拇指、检视臂根与装备外观修订（2026-10-30）

本轮针对用户截图及反馈制作，保留标准 V9 手模、原生骨长、枪械位置和手腕接触位置。没有修改枪体网格、枪械属性或脚架部署时长。

## 已制作与接入

- 左拇指针对 AdvancedAction FullBodyV3 金属护木做对握，MCP/IP 几何弯曲约 38.4°/16.5°；右拇指沿保留的原装后握部收拢，约 32.2°/20.4°。仅三节拇指局部旋转，保留其余手指与手掌。
- 拇指修订按各自握点与手型接入持握、松握及回握。正常开火、独立拉栓、装备、空仓换弹的拉栓接触区间，右拇指新增修订权重均为 0；保留此前枪栓接触动作。脚架左手拉开接触阶段同样保持原动作。
- 检视肩部回到身体一侧，按原生骨长解算双臂并保持手腕/枪械世界接触。前臂扭转沿标准 twist_01 100%、twist_02 50% 分配。肘部避让使用连续有界转动，避免跨角度分支跳变。
- 当前 `ColdSteelPlayer_PIE_0_A.sav` 的 `PlayerHeadId` 为 `kaitlin`，最近游戏日志也加载了 Kaitlin。此前 `body_variants.kaitlin.profiles` 缺少当前 M24，运行时查找直接跳过装备外观；现已加入当前 MotionV9 路径，沿用 Kaitlin 的 M4 原生手臂派生和现有衣袖/手套映射，源材质隐藏索引为 M24 的 0、1。

## 正式产物

- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip`
- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_Mag10`
- `Content/ColdSteelData/modular_outfits.json`：仅新增 Kaitlin 当前 M24 配置字段。
- 作者源：`M24_GripOutfit_Editable.blend`、`author.py`、`thumb.py`、`fit_right_thumb.py`、`inspect_arm.py`。
- 原始资产及配置备份位于 `Before/`；保存状态与哈希以 `install_receipt.json`、`outfit_receipt.json` 为准。

## 定向检查与边界

`targeted_review.json` 记录 5 发与 10 发检视全序列：原版离线重建发现的是左侧臂根外露，右侧在该固定机位没有复现；修订后两侧臂根开口采样均不在视锥内。最大相邻帧旋转约 3.00°，骨长误差小于 0.001 mm，手腕/枪根位置误差小于 0.001 mm。检视左腕最大轴线夹角约 31.8°，右腕约 27.7°。

`right_contact_mask.json` 保存拉栓保护权重。`Review/` 是按实际骨架、保存动作和原生装备网格重建的 Blender 灰模画面，含野行上衣、ST6 衣袖与黑色手套组合；它不代表 UE 材质、镜头叠加或运行时换装验收。`readback.json` 为正式动作资产保存后的轨道数据读回，最终修订以保存回执中的 `patch_sha256` 对应作者数据。

没有打开 UE 编辑器、启动游戏或执行玩法验收；实际镜头和装备切换由用户体验确认。本轮是动画资产及外观配置修改，无需新增 DLL 编译。
