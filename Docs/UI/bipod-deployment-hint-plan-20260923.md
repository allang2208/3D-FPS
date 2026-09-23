# 脚架部署提示与架枪属性

2026-09-23，阶段：制作并接入游戏源码，必要后台构建；未要求预览或测试。

## 范围与布局

- 复用 `ColdSteelStaminaHUD.cpp` 体力条上方的 `DashAttackReadyText` 文字控件、位置、尺寸、字号和阴影；不新建面板或输入区域。
- 屏幕底部居中，相对体力条上移 25 px，沿用 DPI 换算及窄窗宽度限制。主题继续使用 `ColdSteelUI::TextFont`、`TextPrimary` 和 `TextSecondary`。
- 显示优先级：脚架部署中/已部署，然后原有冲刺攻击准备/就绪；二者都未激活则隐藏。取消 ADS、移动、换弹等解除架枪后，不残留成功或百分比文本。

## 数据与状态

| 状态 | 显示 | 数据 |
| --- | --- | --- |
| Deploying | 部署脚架 0～99% | 组件实际 `GetDeploymentBlend()`；完成前向下取整，避免提前显示100% |
| Deployed（进度完成） | 已部署脚架 | `IsDeployed()`，保持到解除 |
| Releasing / 未部署 | 恢复冲刺攻击提示，或隐藏 | 保留 `DashReadyFraction()` 规则 |

UI 只读组件状态，沿用现有 HUD 更新，不新增计时器、射线或独立进度动画。文本只有变化时才写入。进入 ADS 自动架枪、取消 ADS 解除的操作保持不变。

## 属性合同

- 完全部署时后坐力倍率 0.34，即减少66%。继续覆盖现有垂直/水平弹道后坐及枪体反馈接入。
- 稳定性按项目既有0～100评分，在已计算配件后的当前评分上乘1.66并封顶100；通过同一个评分反算公式驱动开火抖动幅度和回稳速度，不把“稳定性+66%”解释为“抖动-66%”。例如50分变83分。
- 使用临时派生的运行时操控值，不回写武器配件、基础属性、存档；解除时随原有过渡恢复。原有脚架晃动/散布规则保持。

## 文件与交付

`WeaponBipodDeploymentComponent`、`WeaponHandling`、角色开火/回稳代码和 `ColdSteelStaminaHUD.cpp`。复用现有主题与资产，无新增图像或许可素材。完成常规 Editor 目标后台构建，不启动 UE 编辑器或游戏；效果由用户测试。

源码与文档已实现。用户保存并关闭编辑器后，后台 `FPSGAMEEditor Win64 Development` 常规构建成功，退出码 0，耗时 87.74 秒，正式构建产物已落盘。日志为 `SourceAssets/PKMLowpoly20260922/BipodDeploy28/build_console_handling_hud.log` 与 `build_editor_handling_hud.log`。没有启动编辑器、运行游戏测试或渲染，效果由用户测试。
