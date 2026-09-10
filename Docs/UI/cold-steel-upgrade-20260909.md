# UE5 冷钢 UI 对照升级 · 2026-09-09

本次以 `E:/3d/3-dfps/ui/status_page.gd`、`ui/player_status.gd`、`ui/apple-glass-tokens.json` 和 `docs/apple-glass-ui-standard.md` 为来源。Godot 参考保持只读；使用独立存档重新渲染三种分辨率。目标为当前 UE5 已有 UI 的升级，重点是角色属性页。当前实现不等于原项目全部玩法迁移完成。

## 对照结果与实现

| 区域 | 升级前 UE5 | 当前实现 |
|---|---|---|
| 公共字体 | 本机宋体常规字重，数字字体中文回退不明确 | 宋体 face 0、0.5 轮廓加粗本机字体；Consolas 数字、宋体中文回退；浮点字号，不靠文字描边 |
| 字号与布局 | 启动时零视口 DPI 被写入控件，实际尺寸放大 | 公共 PixelScale 在 RHI 视口准备前使用请求分辨率；标题、属性行与浮窗按物理像素生成 |
| 抽屉 | 45% 全高、四个页签，按钮内容只居中占一小块 | 保留比例与分区；全宽页签、冷钢背景、18px 外壳圆角、独立滚动区 |
| 角色头 | 写死身份信息 | GameInstance 角色状态模型，身份、等级与属性点绑定 |
| 状态条 | HP 部分实时；其余“未接入” | HP 与当前角色生命组件一致；魔法/体力/经验缺乏玩法所有者时显示“—”，说明原因 |
| 六维 | 硬编码 10；标签与数值居中挤压 | 两列六维、名称左对齐、数值右对齐；正数属性点时显示加点按钮；模型拒绝无点数/未知属性 |
| 战斗属性 | 30 伤害硬编码与空占位混杂 | 原 Godot 六维派生公式；与当前武器实值单独分区，浮窗明确六维尚未参与 UE 战斗结算 |
| 武器实值 | 名称、部分参数为样例 | 根据当前角色显示武器名、伤害、射击间隔、普通/空仓换弹、ADS、弹药；不修改武器参数 |
| 详细信息 | 几条固定参数 | 原页全部 9 项；半径、实际水平速度、攻击距离、当前相机水平 FOV 读取实际角色 |
| 轮回信息 | 固定 0/1 等容易误认为真实进度 | 原页全部 6 项；暂无权威进度来源时显示“—” |
| 属性浮窗 | 六维硬编码，位置固定，不处理焦点 | 40 项共用焦点/悬停入口；完整说明、当前值；自适应高度、视口夹取、失焦/换页/关闭收起 |
| 装备浮窗 | 示例强化 +10、附魔中毒、扩容等与真实武器混显 | 清除未经数据支持的样例加工效果；保留主卡和真实参数；键盘焦点、固定可达关闭、末行可见性验收 |
| 快捷栏 | 48 单位随 DPI 缩小；覆盖浮窗 | 48px 槽位与8px间距；Q/E/X 与1–4保留；抽屉/浮窗在其上层 |
| 天气控制 | 字号15/13、整块缩放，内容多时受限 | 公共冷钢字体和按钮色；预设滚动、关闭固定；零视口初始化保护 |
| 输入 | 面板打开后游戏仍可能收到按键 | C 直接打开状态；B/Tab 打开背包；面板打开使用 UIOnly、平衡移动/视角锁；Esc/B/Tab/C 关闭；重复开关与销毁解绑 |

## 实现文件与数据边界

- `ColdSteelCharacterSheet.cpp`：原页结构、实时读取适配、说明浮窗、主 HUD 角色摘要。
- `ColdSteelDetailRow.h/.cpp`：可聚焦属性行、状态条、加点入口。
- `ColdSteelStatusModel.h/.cpp`：GameInstance 生命周期内的六维公式与加点状态，事件触发刷新。**尚未接入 SaveGame、经验增长或战斗伤害结算。**
- `ColdSteelHUDWidget.h/.cpp`：公共构建入口、抽屉、装备页、快捷栏及输入生命周期。实时武器/状态仅在面板打开时每 0.1 秒读取；加点使用事件即时更新。已有弹药 HUD 与天气进度调度保留。
- `ColdSteelUIStyle.h/.cpp`：公共字体、颜色、像素尺寸换算。
- `WeatherControlWidget.cpp`：已有天气面板的视觉和滚动布局升级。
- `FPSGAMEPlayerController.cpp`：C 入口与仅命令行启用的验收启动。
- `ColdSteelUpgradeAudit.cpp`：真实控件、模型变化、运行数据、焦点和输入的定向验收。

仍未迁移的原项目能力：真实空间背包/仓库数据、拖放/堆叠/穿戴交易、实例存档、完整技能/图鉴/枪匠/NPC 面板及其游戏流程。装备网格沿用原有 AK-105/药水/金币布局样例与图标，不代表当前 M4 装备和真实物品存量。技能和图鉴页签仍为禁用状态。不能把这次 UI 升级描述成上述玩法已经完成。

## 验收与复现

UE5 Development Editor 构建通过。编辑器存在其他会话使用的模块，采用带独立后缀的 Editor 构建，保留其进程。最新编译生成的 `Binaries/Win64/UnrealEditor.modules` 供新进程加载。当前已打开的旧编辑器是否自动热重载不作为验收证据。

运行 `Tools/UI/run_upgrade_acceptance.ps1` 启动独立游戏进程，在 960×540、1280×720、1920×1080 下测试并自动退出。只允许 `ColdSteelUpgrade: COMPLETE failures=0` 作为该组通过。证据保存在 `Saved/UIUpgrade/2026-09-09/`：

- `final-960-retry.log`、`final-1280.log`、`final-1920.log`：最终通过的运行日志；每个分辨率均为 19 项 PASS、`COMPLETE failures=0`，进程退出码 0。
- `status-*`、`status-focus-*`、`status-details-*`：属性页顶部、焦点说明、底部信息。
- `equipment-*`、`equipment-detail-*`、`hud-*`、`weather-*`：现有面板与 HUD。
- `godot-status-*`：本次实际 Godot 引擎渲染的参考。

测试会短暂改变自身审计进程内的属性点、生命和移动速度并立即恢复，不读写正式玩家存档。覆盖原版公式、无点数与非法键不扣点、20次加点后派生数值刷新、生命/上限联动、厘米到米换算、未提供资源不造数、45%抽屉、完整属性行、键盘详情、浮窗边界、装备末行、关闭与8轮开关输入锁平衡。

首次最终 960 运行在第 5 帧、UI 验收开始前发生 D3D12 GPU device removed，退出码 3；原始日志保留为 `final-960.log`。使用相同构建和渲染配置单独重跑后通过，日志为 `final-960-retry.log`。此次不据此断言 GPU 故障根因或项目渲染稳定性。

引擎 Experimental Toolsets 的 Python 启动脚本存在 `ToolsetDefinition` / `PythonTestRunner` 缺失报错；它们与本次 UI 验收结果分别记录。没有声称整个项目零错误、全流程或打包验收通过。PIE 任意拖动改变窗口尺寸、手柄全部导航、亮暗背景实测对比度和发行字体授权不在此次已通过证据中。

## 字体与备份

`Tools/UI/prepare_local_simsun.py` 读取本机 `C:/Windows/Fonts/simsun.ttc` 的 face 0，以 FreeType 生成 1/32 em 的加粗轮廓；依据 [Godot TextServer 源码](https://github.com/godotengine/godot/blob/master/modules/text_server_adv/text_server_adv.cpp) 与 [FreeType 轮廓接口](https://freetype.org/freetype2/docs/reference/ft2-outline_processing.html)。字距和 advance 保留，字体栅格器差异仍存在，不宣称逐像素完全相同。

生成文件位于 `Saved/UIFonts/`，仅用于用户本机预览，不放进 Content 或发行包。生成 JSON 记录原字体 SHA256、face、强度和输出哈希。缺少该本机文件时公共字体入口回退本机宋体。

六个被修改的原文件完整备份位于 `trash/ui-upgrade-20260909/Source/FPSGAME/`。UE 项目没有 Git，未制造虚假提交；Godot 的并行工作未修改。
