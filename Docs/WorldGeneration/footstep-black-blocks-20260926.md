# 脚步黑色方块排查与修复

用户现象：每走一步脚下冒出几块黑色方片，随后消失。

## 用户截图确认的原因：脚印贴花

用户反馈首轮粒子修正后仍有黑块，并提供截图。右下角明确提示贴花材质必须使用延迟贴花材质域，指向 `MID_M_GrassTrampleDecal_0`；画面上的完整矩形也沿步行路径贴在地面上。因此，截图中这一问题应归因于脚印贴花，首轮仅修正扬尘粒子未解决它。

`GrassFootstepFeedbackComponent::EnsureDecalPool` 为每个池槽创建 `M_GrassTrampleDecal` 的动态材质，`PlaceDecal` 放置贴花，Tick 改变 `Fade`。但 `setup_assets_m3.py::build_decal_material` 只写了 Translucent/Unlit 和传统 BaseColor/Opacity，遗漏了 `MD_DEFERRED_DECAL`，也没有 Substrate 贴花输出。

本轮修正正式作者函数：显式设置 Deferred Decal 材质域，接入 Default Lit 的 `SubstrateShadingModels → SubstrateConvertToDecal → Front Material`，将原圆形柔边遮罩乘 `Fade` 同时接至实际 `Coverage`，避免默认满覆盖留下投影矩形。保留原参数名、池、寿命、路径和地面材质。局部落盘入口为 `Tools/GrassDeform/repair_footstep_decal.py`，不重建整个 M3。

## 首轮粒子排查（未解决截图中的贴花问题）

`FPSFootstepAudioComponent::Play` 发出的脚步事件被 `GrassFootstepFeedbackComponent` 接收，后者每步激活 `DA_GrassFootstepFeedback.PuffSystem` 指定的 `NS_GrassFootstepPuff`。

保存资产的只读诊断位于 `Saved/FootstepBlocks20260926/diagnosis.json`。其中 `GrassPuff` 的 Sprite Renderer 实际仍绑定 `MI_VFX_HeatDistortion_Strong`，来自 `NE_Heat`。原 M3 脚本删去了热扭曲模板的驱动模块，却未替换材质、明确粒子尺寸与颜色或恢复运动、淡出；Renderer 的 Color/Velocity 绑定在已保存数据里均显示没有对应输出。原脚本还向被静态开关隐藏的 Lifetime 写值，并用 HLSL 字符串设置枚举 Loop Behavior，不能确保生命周期真正生效。

这条触发链与用户描述的逐步产生、短暂消失吻合。未进行游戏内复现，视觉修复结果仍由用户确认。

## 修改

- 保留原系统资产路径，现有 DataAsset 和 C++ 引用自动使用修正内容。
- 新增 `M_GrassFootstepDust`：程序化圆形柔边覆盖率、粒子颜色与透明度、接触深度淡化、明确的 Substrate 输出；边界透明，不依赖外部贴图或热扭曲。
- 一次产生 8 个尘土粒子，直径从 4 cm 扩散至 10 cm，寿命 0.55–0.75 秒，透明淡入淡出。出生位置保留在世界空间，随后缓慢向外及向上扩散。
- 发射器明确为 CPU、Self/Once，保留原组件池和并发上限，关闭粒子投影。
- 新作者脚本 `Tools/GrassDeform/author_footstep_puff.py` 与 M3 正式入口同步，避免以后重跑时恢复错误模板设置。

首轮只修改脚步粒子和它自己的材质；第二轮补充修正脚印贴花。草地形变、地面材质、移动逻辑和高炉效果不在本次修改范围。旧系统及贴花材质副本存于 `SourceAssets/GrassFootstepRepair20260926/BeforeRepair`。

## 首轮交付记录

后台 D3D12/SM6 作者 commandlet 已完成，退出码 0。`M_GrassFootstepDust` 与原路径 `NS_GrassFootstepPuff` 已保存，Niagara 编译返回 `valid=1`，保存后的 Renderer 材质引用和 Self/Once 枚举已读回。

回执：`SourceAssets/GrassFootstepRepair20260926/receipt-20260926-173318.json`；构建日志：`Saved/Logs/footstep-puff-author-20260926.log`。仅有资产制作与针对性诊断；未启动游戏、PIE、预览或截图，不宣称视觉验收通过。

## 第二轮贴花交付记录

后台 D3D12/SM6 commandlet 于 18:18:44 保存 `M_GrassTrampleDecal`，报告 0 错误。读回结果为：原材质域 `MD_SURFACE`、原 Front Material 为空；修改后材质域为 `MD_DEFERRED_DECAL`，Front Material 为 `SubstrateConvertToDecal`，其真实 Coverage 输入节点与原 Opacity 的柔边/Fade 遮罩一致。

回执：`SourceAssets/GrassFootstepRepair20260926/decal-receipt-20260926-181844.json`；日志：`Saved/Logs/footstep-decal-repair-20260926.log`。编辑器在桥接前已退出，桥没有执行资产修改或停止试玩；实际修复由后台 commandlet 完成。未启动编辑器或游戏，视觉结果仍待用户重新进入试玩确认。
