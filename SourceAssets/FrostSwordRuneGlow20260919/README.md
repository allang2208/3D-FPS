# 寒晶剑剑身Ⅱ：银白荧光符文

> 2026-09-19 用户确认本轮最终结果成功、符合预期。此记录来自用户实机反馈；本次归档/文档整理没有重新测试。

2026-09-19。用户已接受配重锤修订，本次只调整剑身Ⅱ的共鸣、侵蚀、导魔三款符文显示。

## 外观

- 中心为柔和银白偏蓝，边缘增加淡冰蓝光晕。
- 中心有固定亮度，荧光层轻微呼吸／闪烁，最低亮度不会归零。
- 三种纹样继续使用原有遮罩和剑身投射范围；保留各自的节奏区别。
- 使用 Unlit 自发光并在输出前应用 `EyeAdaptationInverse`，抵消自动曝光对符文自身亮度的压暗。无需依赖夜间环境灯照亮符号，也不修改世界曝光或全局泛光。

此前运行材质的 Emissive／Opacity 已连接，`GlowStrength` 默认值为 8；本轮没有把黑色表现直接归因为贴图丢失。修改改用明确的银白中心、冰蓝发光色、非零亮度下限及局部曝光补偿。游戏内结果由用户测试。

## 可调参数

颜色为线性 RGB。

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| `RuneBaseColor` | 0.82, 0.89, 1.00 | 银白中心 |
| `RuneGlowColor` | 0.55, 0.78, 1.00 | 冰蓝荧光 |
| `BaseBrightness` | 1.35 | 固定亮度 |
| `GlowStrength` | 2.8 | 荧光强度，位于曝光补偿之前 |
| `RuneOpacity` | 0.96 | 纹样中心覆盖率 |
| `HaloOpacity` | 0.20 | 边缘光晕覆盖率 |
| `HaloRadiusTexels` | 2.5 | 遮罩采样光晕半径 |
| `ExposureCompensation` | 1.0 | 完整局部曝光补偿 |

## 接入与作者源

运行路径沿用 `/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2`，已有改造选项和存档无需迁移。

`apply_rune_glow.py` 修改现有 Custom 节点并接入颜色／亮度参数及曝光节点；不删除现有表达式表。升级前材质包和 HLSL 留在 `Before/`。支持重复执行，`install_receipt.json` 记录实际保存完成时间。

可通过 `Tools/AssetPipeline/ue_python_exec.py --script <本目录>/apply_rune_glow.py` 在编辑器执行。重建旧 SurfaceV2 资产后，应再次运行本升级入口恢复当前外观。

本轮编辑器实时编译期间无法接收远程写入，主工程命令行导入又被缺失的 AutoFootstep 模块阻止。最终通过既有 `RuneSwordImport` 精简宿主完成材质保存，并启用与主工程一致的 Substrate 设置。正在运行的编辑器需重启后读取更新；完成回执见 `install_receipt.json`。

仅保存符文材质，未修改剑网格、配重锤、战斗数值、存档、地图、天气或全局后期处理。未启动游戏、截图、渲染或执行验收测试。
