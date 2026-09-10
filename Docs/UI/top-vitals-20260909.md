# 顶部生命、魔法、等级状态栏

按本次要求将顶部名称/等级/职业摘要替换为生命、魔法、等级三列。保留 Caps 属性栏入口、Tab 背包入口及其他 HUD 模块。

依据当前 `E:/3d/3-dfps/docs/apple-glass-ui-standard.md`、`ui/status_bar.gd:428` 和 `ui/style.gd:9`：冷钢深灰玻璃染色、银色细边、公共宋体与 Consolas；标签在上、9px 轨道居中、当前值/上限在下。生命渐变 `#763B43 → #BD626D`，魔法渐变 `#36566E → #7194AC`，轨道底色 `#080B0E`。生命不高于 25% 时数值和边线使用静态警示色；没有持续闪烁、伪造回血动画或滞后的数值。

UMG 管理三列容器、文字及布局；`UColdSteelResourceMeter` 用 Slate 绘制细轨道和圆角渐变。面板不参与命中测试，不接管鼠标或键盘焦点。顶栏居中，顶部 12px；时间栏按顶栏实测高度保持至少 8px 间距，其详情浮窗随之移动。

数据来源：生命读取当前 Pawn 的 `UFPSCombatHealthComponent`；魔法及等级读取 `UColdSteelStatusModel`。复用现有 50ms HUD 刷新节奏，因此背包关闭也更新；模型变更即时触发同一刷新入口。文字只在改变时更新、条形只在比例或类型改变时失效重绘。没有新增长期定时器/委托，Slate 资源在控件释放时清理；晚创建/更换 Pawn 从当前拥有者重新读取。缺少数据或上限无效时显示破折号及空条，比例限制在 0–1。

首轮实机发现了 Slate 直接绘制时空轨道颜色未应用和顶栏高度挤占时间栏的问题，均已修正。测试样本使用实际组件和独立 `TopVitals_*` 存档；不修改正式玩家存档。满血样本采用角色真实派生上限，避免与角色配置刷新冲突。

文件：`ColdSteelTopVitals.cpp`、`ColdSteelResourceMeter.h/.cpp`、`ColdSteelTopVitalsAudit.cpp`，现有 HUD/CharacterSheet/PlayerController 的接入改动。原文件备份在 `trash/top-vitals-20260909/`。

复测入口：`Tools/UI/run_top_vitals_acceptance.ps1`。要求每个 UE 进程退出码 0、`TopVitals: COMPLETE ... failures=0`，并人工查看真实渲染截图。最终结果记录在下方。

最终编译通过：`FPSGAMEEditor Win64 Development`，模块 `UnrealEditor-FPSGAME-2026090947.dll`；日志 `Saved/TopVitals-build.log`。

| 分辨率 | 结果 | 日志 |
| --- | --- | --- |
| 1920×1080 | 13 项通过、0 失败、退出码 0 | `Saved/TopVitals/20260909225029-1920.log` |
| 1280×720 | 13 项通过、0 失败、退出码 0 | `Saved/TopVitals/20260909225029-1280.log` |
| 960×540 | 13 项通过、0 失败、退出码 0 | `Saved/TopVitals/20260909225029-960.log` |

检查覆盖：背包关闭时满血同步、魔法与等级真实绑定、控件边界及时间栏间距、不捕获输入、模型更新、受伤数值与比例、25% 警示、零魔法、魔法恢复、空血条、超上限显示钳制、独立档案恢复。已查看 1920 的满血图、960 的低血图与 1280 的空血/满魔图；渐变、深轨道、文字及留边正常。测试截图的等级 7/8、25/100、0/100 是隔离样本，不是对正式角色的修改。

真实 GPU 截图位于 `Saved/TopVitals/full-*`、`low-*`、`empty-*`。此轮仅验收顶部资源面板及与时间栏的空间关系，不将同时出现在截图中的其他并行 HUD 改动计入本轮成果。最终相关源文件 SHA256 见 `Saved/TopVitals/final-evidence.json`。
