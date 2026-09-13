# 装备改造台：冷钢玻璃正式接入

2026-09-12。用户在方案、黑灰背景和九类部件图标评审后明确要求“整体接入游戏”。本次在 `D:/FPS3D/FPSGAME` 的 UE 5.8.2 实现改造台整体升级。

## 当前实现

- 中央继续加载原有 `/Game/UI/GunsmithWorkbench/T_WorkshopBackground`，叠加实际枪械的实时渲染，保留旋转、双击复位、水平复位和瞄准预览。外围改成中性黑灰渐变。
- 左侧目录、中央配件区和右侧汇总共用三处真实 `SBackgroundBlur`：强度 5、半径 13、10 圆角、半透明炭灰染色和细顶光。低画质使用深灰回退；文字与图标在模糊上方绘制。
- 九类统一材质图标以 48 单位显示，配合完整中文类别名、当前部件名和选中标线。长部件名省略后可悬停查看全文。可用分类从当前枪械目录读取，不硬编码可用数量。
- 配件卡为 264×142，保留普通滚轮和显式横向滚动条；区分“已安装”“已选 · 待应用”“当前安装”。说明卡和表格使用同一草稿与装备实例。
- 右侧完整保留 20 项、四列、原行序及当前／原厂比较；数字右对齐，降低后坐等收益仍为绿，代价为红。表头固定、表体独立滚动。
- 底部状态、“撤销更改”“应用并保存”固定可见。撤销恢复精确瞄具型号及现有附件状态，不再将非全息瞄具错误地退回机械瞄具。

## 布局与字体

移除了固定 1600×900 整体缩放。`SDPIScaler` 只抵消项目的分辨率 DPI 曲线，按 `BodyHost` 的实际可用空间重排。每帧只检查几何档位，档位不变时不重建控件。

| 实际内容区条件 | 布局 |
| --- | --- |
| 宽 ≥1450、高 ≥520 | 左栏 208、中央弹性、右栏 438 |
| 宽 1100–1449、高 ≥520 | 左栏 184、中央弹性、右栏 394 |
| 宽 740–1099 或高度 <520 | 类别＋预览在上，汇总在下；中部主滚动 |
| 宽 <740 | 类别、预览和汇总依次纵向排列 |

窄窗的汇总面板按可见内容高度约束，使标题、比较按钮和表头可同时看到，详细行单独滚动。顶栏与底部操作不随主内容滚走。短操作按钮保持单行，避免动态缩放后断字。

中文、按钮和标题使用 Noto Sans SC Regular／Medium；数值使用 JetBrains Mono Regular／Medium，并显式以 Noto 回退中文单位。改造台只用 20／16／14／12 四档，按 Slate 原生点数的 96/72 换算，避免把 14px 误显示为接近 19px。后续全局规则更新已将字体和配色收敛到 `ColdSteelUIStyle`，`GunsmithUIStyle` 作为像素字号兼容入口；不再执行“其他面板继续使用宋体／Consolas”的旧范围限制，见 [正式规则 v2](ui-cold-steel-design-system.md)。

四份字体位于 `Content/UI/GunsmithWorkbench/Fonts`，不依赖本机已安装字体或 Saved 临时字体。Noto 为 2.004，JetBrains Mono 为 2.305；OFL 1.1 文本、原始 URL、提交和 SHA-256 与字体一并保留于 `provenance.json`。生成器固定提交：

- Noto：`f8d157532fbfaeda587e826d4cd5b21a49186f7c`，来源 [noto-cjk](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE)。
- JetBrains Mono：`19371302b95d218af43299bce79ddbddd0bc364d`，来源 [官方 OFL](https://github.com/JetBrains/JetBrainsMono/blob/master/OFL.txt)。

字体已加入 `RuntimeDependencies` 的 UFS 暂存列表。图标和材质被已有 `/Game/UI/GunsmithWorkbench` 的 AlwaysCook 目录覆盖；本次没有进行整包 cook 或发行包测试。

## 图标与资源恢复

九张经评审的 1254×1254 RGB PNG 原样保留，见 [候选与生成记录](../../SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/README.md)。正式纹理为 `/Game/UI/GunsmithWorkbench/ColdGlass/T_Category_<slot>`；枪管对应既有目录键 `foregrip`，前握把对应 `underbarrel`。

`M_CategoryIcon` 是 UI 透明混合材质，以中性灰图标的近黑像素去除背景，表达式为 `saturate((Texture.R - 0.012) * 100)`。每个分类创建独立 MID，纹理和 MID 均由 UPROPERTY 保活。这是 UE 中的材质透明合成，不是导出了新的 RGBA 源图，也不包含三维配件或 PBR 材质包。

- [字体准备器](../../Tools/UI/prepare_cold_glass_fonts.py)：从固定官方提交恢复未修改字体和许可。
- [图标导入器](../../Tools/UI/import_cold_glass_icons.py)：通过 UE Python 导入九张源图并建立 UI 材质。
- 本机导入结果：`Saved/ColdGlassIntegration20260912/import-result.json`。首次素材 commandlet 因工程启动时其他资源／插件报错返回非零，不能作为整个工程 commandlet 通过；导入完成后已在实际游戏中检查九纹理、九 MID 和渲染画面。

## UI 生命周期与数据合同

保持 `UM4GunsmithWidget` 承载 Slate 的混合结构。`UGunsmithSystem` 管理草稿、合法选择、计算与应用；`UColdSteelStatusModel` 管理装备实例和存档。Construct 注册两个 OnChanged，Destruct 解除注册并释放预览。显示刷新由这些事件及明确 UI 操作触发，不在 Tick 轮询业务数据。

打开时沿用控制器的 UIOnly、键盘焦点和移动／视角锁定；关闭时恢复角色配置、GameOnly、鼠标与输入。类别和候选卡沿用 Slate 标准 Tooltip 的弹层定位；没有新增脱离视口约束的自定义弹窗。保留鼠标捕获、按住拖动越界旋转和释放逻辑。

运行按 `J` 打开当前装备枪械的改造台；Esc、Tab、J 或“返回”关闭。测试使用独立 `ColdSteelProfile=WorkbenchAudit_<RunId>_<Width>`，不使用玩家日常存档。

## 验证记录

最终 V5 已在新的 DX12 `-game -RenderOffscreen` 进程完成 **91 项、0 失败**，结束时间为 2026-09-12 18:41:54（北京时间）。检查覆盖真实拖动和鼠标捕获、对比、应用、写入失败、存档恢复、撤销精确瞄具、大量候选的滚动点击、长附件取景、尺寸重排、最后分类与最后数值行、高缩放操作按钮单行，以及退出恢复游戏输入。V4 的 86 项通过记录保留为中间版本证据。

| 最终检查 | 结果与本机日志 |
| --- | --- |
| FPSGAMEEditor Development | Succeeded；`Saved/ColdGlassIntegration20260912/build-v5.log`，模块后缀 91265 |
| FPSGAME Development | Succeeded；`Saved/ColdGlassIntegration20260912/build-game-v5.log` |
| 工作台实机／交互／存档／布局 | `WORKBENCH: COMPLETE checks=91 failures=0`；`Saved/GunsmithWorkbenchAudit/coldglass-v5-1920.log` |

实际游戏画面：

![1920×1080 冷钢玻璃改造台](D:/FPS3D/FPSGAME/Saved/ColdGlassIntegration20260912/final/coldglass-v5-1920-draft.png)

[1280×720](D:/FPS3D/FPSGAME/Saved/ColdGlassIntegration20260912/final/coldglass-v5-1280.png) · [960 上部](D:/FPS3D/FPSGAME/Saved/ColdGlassIntegration20260912/final/coldglass-v5-960-top.png) · [960 汇总及最后一行](D:/FPS3D/FPSGAME/Saved/ColdGlassIntegration20260912/final/coldglass-v5-960-summary.png) · [125% 应用缩放](D:/FPS3D/FPSGAME/Saved/ColdGlassIntegration20260912/final/coldglass-v5-ui-scale-125.png) · [150% 应用缩放](D:/FPS3D/FPSGAME/Saved/ColdGlassIntegration20260912/final/coldglass-v5-ui-scale-150.png)。逐张检查后，短操作按钮均保持单行。

验证命令（PowerShell，项目根）：

```powershell
$env:UE_SKIP_UBT_SDK_SETUP='1'
& Tools/UI/run_gunsmith_workbench.ps1 -Width 1920 -Height 1080 -RunId coldglass-v5 -LayoutStress -RenderOffscreen -ColdGlassResize
```

`UE_SKIP_UBT_SDK_SETUP` 仅用于本次子进程避免启动时等待并行 UBT SDK 探测；没有关闭游戏、UI、存档或渲染检查。Offscreen 使用真实 DX12 渲染和 Slate 输入；普通隐藏窗口的早期运行曾有五项合成鼠标路由失败，不能把该轮当作通过记录。

| 画面条件 | 检查内容 |
| --- | --- |
| 1920×1080 | 九类与 20 行连续展示，原背景与真实预览 |
| 1280×720 | 紧凑三栏，左右独立滚动，固定底部 |
| 960×540 | 上下重排，完整汇总标题／比较入口及最后一行可达 |
| 回到 1920×1080 | 不重开面板即可恢复三栏与原数据 |
| 应用缩放 125%／150% | 边界、数据和短按钮排版；这是 Slate 应用缩放压力检查，并非修改 Windows 系统 DPI |

未执行完整发行包验收或模糊 GPU 毫秒／FPS 对照；本记录不声称这些项目通过。共享工程同期新增枪托文件的两处编译兼容问题已作最小修正：局部 `Mesh` 重命名为 `StockMesh`，查询材质可见性时使用 UE API 所要求的非 const 组件指针；未改枪托的摆放和玩法。

## 本次主要文件

`M4GunsmithLayout.cpp`、`M4GunsmithOverview.cpp`、`M4GunsmithWidget.h/.cpp`、`GunsmithUIStyle.h/.cpp`、预览 Tick 中的响应布局调用，以及 `GunsmithWorkbenchAudit.cpp`、`GunsmithLayoutAudit.cpp` 和运行脚本。上述部分文件原本已有并行修改，本次保留了动态枪名、独立预览、长附件取景等工作；没有清理或覆盖其改动。

实施前相关文件快照、构建日志和实际游戏截图保存在 `Saved/ColdGlassIntegration20260912`。旧候选提案已按用户要求移入 trash，见 [归档记录](panel-workflow-archive-20260913.md)；后续面板／栏目使用 [工作流](../../UI-WORKFLOW.md) 与 [正式规则](ui-cold-steel-design-system.md)。
