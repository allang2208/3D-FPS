# 冷钢装备改造工作台表现升级

2026-09-10。采用已选的 02 工作台布局，融合 03 改造前后对比；参照 Godot `ui/gunsmith_panel.gd` 的配件说明和整枪汇总层级。使用现有 ColdSteelUI 字体、冷灰背景、银色主按钮和绿色收益/琥珀色代价规则。

## 页面

后续布局回查、滚轮配件列表和缺陷修复见 [回查记录](D:/FPS3D/FPSGAME/Docs/UI/gunsmith-layout-review-20260910.md)。当前底部为固定宽度的横向滚轮配件列表，右侧改造说明与整枪数值分别滚动；历史截图保留用于比较。

- 左侧：配件类别导航，当前 M4 支持瞄具、弹匣；其他类别明确标记待扩展。
- 中央：新生成的工作间背景，包括穿孔工具墙、侧边收纳、顶灯、工作垫和台沿细节。背景不含枪械和界面文字。
- 枪械：使用装备实例的真实模型、原材质、骨骼姿态和配件，在独立预览场景中同步显示；中性主光、补光和环境反射保持模型可读性，隔离游戏天气、雾和昼夜染色。支持侧面与瞄准预览。
- 后续交互调整：默认以水平侧放姿态展示，枪管沿屏幕水平方向。中央预览区按住鼠标左键左右/上下拖动可旋转整套枪械；双击或点击“水平复位”恢复默认姿态。瞄准状态开始拖动时返回整枪查看。配件选择卡、数值表和按钮不触发旋转。
- 下方：当前类别的配件选择卡片；全局底栏保持撤销、应用并保存可见。
- 右侧：已选改造项目及效果，其下始终列出整枪数值，包括未变化的项。可以切换与当前已安装配置或原厂配置对比。
- 布局使用 1600×900 设计尺寸等比适配，非 16:9 使用冷钢背景留边；类别和右栏均可滚动。

## 数值与业务边界

完整 14 行：开镜耗时、弹匣容量、普通换弹、空仓换弹、射击间隔、射速、基础命中伤害、后坐力系数、镜头震动系数、腰射散布系数、最大命中距离、子弹速度、瞄具倍率、机械瞄具状态。

数据来自 `UGunsmithSystem::Calculate`、装备实例及角色属性。当前武器采用即时命中，速度显示“即时命中”；后坐等显示相对原厂系数，不虚构角度或米制数值。当前仅支持 M4 原厂机械瞄具和 1× 全息瞄具，倍率行据此显示 1×。

当前配置对比以已安装部件为基准，成功保存后差异归零；原厂对比持续显示累计改造影响。变化方向按语义着色，缩短开镜时间为收益，延长换弹时间为代价。仍调用原有选择、撤销、事务保存和恢复流程，本次没有调整配件平衡或弹药规则。

未装备的背包枪械仍可改造和保存，中央明确提示装备后查看；不显示另一把已装备枪械的错误预览。

预览组件和场景均为临时对象，关闭时释放。选择或视角切换后以最高 30 Hz 更新一秒，静止时每秒更新一次；此为调度策略，不代表 FPS 测量结果。

旋转仅施加于独立场景中的展示副本，围绕枪身中心统一变换枪械和配件，不写入角色视角、枪械实例或存档。拖出预览区域后松开鼠标仍能结束旋转；关闭面板时若正持有鼠标捕获，会主动释放。横向可循环旋转，纵向限制范围避免连续翻转。重新打开面板恢复默认姿态。

## 文件与资产

- `Source/FPSGAME/UI/M4GunsmithWidget.*`：生命周期、选择和输入。
- `Source/FPSGAME/UI/M4GunsmithLayout.cpp`：布局和配件卡片。
- `Source/FPSGAME/UI/M4GunsmithOverview.cpp`：完整数据汇总和差异。
- `Source/FPSGAME/UI/M4GunsmithPreview.cpp`：独立工作台预览场景。
- `Source/FPSGAME/UI/SM4PreviewSurface.h`：预览区域拖动捕获、移动、松开及双击复位。
- `Source/FPSGAME/Weapons/M4DrumVisual.cpp`：取景与可预览组件列表；保留并行任务的弹鼓掉落逻辑。
- `Content/UI/GunsmithWorkbench/`：背景、预览合成材质、默认 RT、工作台环境反射纹理，已加入 AlwaysCook。
- `SourceAssets/GunsmithWorkbench20260910/PROVENANCE.md`：背景生成提示词、来源。
- `Tools/AssetPipeline/import_gunsmith_workbench.py`：可复现资产导入。
- `Tools/UI/run_gunsmith_workbench.ps1` / `Source/FPSGAME/UI/GunsmithWorkbenchAudit.cpp`：独立存档的实机验收与截图。

## 验收记录

最终 C++ 构建通过。1920×1080 和 1280×720 各通过 22 项实机检查；修正 720p 副标题自动断行后，再次运行 720p，22 项全部通过。检查存档均为独立 `WorkbenchAudit_*`。

水平预览及拖拽补充验收：`orbit-v2-1920` 和 `orbit-final-1280` 各通过 31 项检查。使用 Slate 实际事件路由验证鼠标按下捕获、双轴拖动、区域外松开、松开后停止、双击复位，以及拖动中关闭时的捕获释放；同时确认角色朝向、弹药和改造草稿不受旋转影响。构建日志 `SourceAssets/GunsmithWorkbench20260910/build-orbit.log`，汇总 `orbit-acceptance.json`。

![水平预览实机](D:/FPS3D/FPSGAME/Saved/GunsmithWorkbenchAudit/orbit-v2-1920-draft.png)

[旋转后的实机图](D:/FPS3D/FPSGAME/Saved/GunsmithWorkbenchAudit/orbit-v2-1920-rotated.png) · [720p 拖动结果](D:/FPS3D/FPSGAME/Saved/GunsmithWorkbenchAudit/orbit-final-1280-rotated.png)

![1080p 工作台实机](D:/FPS3D/FPSGAME/Saved/GunsmithWorkbenchAudit/final-v2-1920-draft.png)

[1080p 瞄准预览](D:/FPS3D/FPSGAME/Saved/GunsmithWorkbenchAudit/final-v2-1920-ads.png) · [最终 720p 布局](D:/FPS3D/FPSGAME/Saved/GunsmithWorkbenchAudit/final-v3-1280-draft.png) · [生成背景原图](D:/FPS3D/FPSGAME/SourceAssets/GunsmithWorkbench20260910/workshop-background.png)

详见 `SourceAssets/GunsmithWorkbench20260910/acceptance.json` 和 `Saved/GunsmithWorkbenchAudit/` 中对应日志、原始实机截图。自动检查涵盖完整数据行、改造差异、保存失败保留草稿、成功保存、恢复、撤销、瞄具及机械瞄具状态、未装备实例，以及反复开关后的预览场景释放。

资产导入命令行存在项目原有 GameFeatureData 规则错误，因此导入命令整体返回 1；资产验收依据脚本 PASS 标记、明确保存记录和后续正常渲染，未把退出码 1 记为通过。当前验证为开发版本实机运行，未做完整打包发布验收。
