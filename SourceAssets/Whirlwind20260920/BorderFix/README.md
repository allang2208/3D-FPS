# 大旋风屏幕黄晕移除

2026-09-20 用户反馈释放时屏幕四周出现黄色边框，并确认是较宽的黄色光晕／拖影。

已读取当前 `M_WhirlwindFocus` 材质图表及源码：没有独立黄色边框或着色节点，旋转期间会采样位移后的背景颜色，原采样会将边缘坐标夹在画面边界上。根据描述针对这一边缘拖色来源修改；未进行实机截图或视觉测试，不将推断写成已实测定位。

`WindupV2/focus_blur.hlsl` 现在让外缘 2.5% 直接输出原画面，向内平滑过渡，距边缘 7.5% 后恢复原背景模糊。越出画面的位移采样直接跳过，颜色和前景遮罩 UV 均限制在各自有效纹理范围内，避免重复拉伸边缘颜色。双手／剑的前景保护、动作、镜头发力、命中反馈与技能数值不变。

`apply_border_fix.py` 更新同一个材质，完成必要 shader 编译后保存；回执为 `apply-receipt.json`。首次通过项目桥接入时编辑器已关闭、未发现 Python 节点，因此没有发送材质写入。后续沿用桥的 `Local\CodexUeMcp-Port-8000` 批次互斥，等待已有资源命令退出，再以离线 Python commandlet 保存本材质，记录为 `apply-commandlet.log`。本轮不涉及原生 C++ 编译，不启动 PIE、截图、预览渲染或游戏测试，由用户自行观察效果。

修改前的图表代码和作者源分别保留在 `material-before.json` 与 `focus_blur_before.hlsl`。制作回读不作为游戏视觉验收。

## 用户截图后的定位与修正（同日）

用户随后提供截图，明确指向覆盖四周的宽黄褐色渐变。此前的模糊 UV 边缘处理没有解决其所指效果，不能将上次修改称为该截图问题已经消除。

本轮读取 `DayNight_Lighting` 当前后处理来源：日夜组件没有额外 blendable，暗角为 0.1。读取引擎 `/Engine/EngineMaterials/DefaultPostProcessMaterial` 图表，发现其将 `DefaultDiffuse` 与场景颜色按屏幕边缘遮罩混合；引擎 `PostProcessMaterial.cpp::GetMaterialInfo` 在原材质所需 shader 不可用时沿 fallback 查找替代材质。这与截图中的黄褐色四周替代画面相符。`M_WhirlwindFocus` 自身仍无黄色着色项，实际读取记录为 `fallback-material-source.json`。

旧 `BeginWhirlwindFocus` 即使把 Strength 设为 0，也会立刻以权重 1 挂载后处理；若 shader 正在构建，默认替代材质不认识 Strength 参数，仍会绘制边框。此次只修改 `Source/FPSGAME/Weapons/RuneSwordWhirlwindFocus.cpp`：

- 蓄势入口只准备模糊材质，不立即把它加入镜头 blendable。
- `SetWhirlwindFocus` 在强度大于零、当前 shader platform 的材质资源及完整 shader map 已就绪时才挂载。
- 强度归零或 shader 尚未就绪时移除 blendable，保持原画面；不会等待 shader 而卡住技能时钟。

通过项目桥完成 Live Coding，返回 `Result: Success`，结果在 `compile-no-fallback-01.txt`。`finish_focus_shader_build.py` 完成现有材质的待处理 shader 构建，结果保存在 `focus-build-no-fallback.json`。首次附带保存返回失败；本轮并未修改材质图表，因此取消了这一步无必要的包重存，仅完成 shader 派生缓存构建。热更新适用于当前编辑器；基础 DLL 的后续常规构建会纳入本源码。

未改动引擎默认材质、全局编辑器边框、其他后处理或 Recover V6 动画。未启动 PIE、运行测试或截图验证；截图外观与回退机制的对应属于源码和资产定位，最终显示效果由用户测试。
