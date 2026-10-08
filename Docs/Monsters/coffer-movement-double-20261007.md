# 沉匣、涡电匣移动与转身提速

2026-10-07。按用户要求，沉匣 M10 和雷匣（项目名涡电匣 M25）的当前移动速度翻倍，同步调整转身与动画节奏。

| 配置 | 调整前 | 调整后 |
| --- | ---: | ---: |
| 两只移动速度 | 55 cm/s | 110 cm/s |
| 两只移动加速度 | 240 cm/s² | 480 cm/s² |
| 两只行走制动减速度 | 360 cm/s² | 720 cm/s² |
| M10 行进转向 | 36°/s | 72°/s |
| M10 原地转身 | 30°/s | 60°/s |
| M10 角加速度 | 97.5°/s² | 195°/s² |
| M25 转向 | 75°/s | 150°/s |

表中调整前数值来自已有正式制作配置。M25 原生默认值曾落后于蓝图，本次同步为新的正式配置；M10 的 CharacterMovement RotationRate 同步为 150°/s，但实际转身仍由专用组件的 72°/s、60°/s 配置控制。

M10 的动画源速度保留 46.153846 cm/s，M25 保留 16 cm/s；实际移动速度除以源速度推进动画，直行动画节奏随移速翻倍。M10 继续共用直行、弧行、原地转身相位，角速度采样上限随转向配置更新，提前补步的最短时间从 0.09 秒缩短至 0.045 秒。M25 在原有动画更新中加入实际转向速度，原地转向时复用爬行触肢循环，与前进共用连续相位；没有新增 Tick 或循环加载。

原生代码仍由服务器负责移动和转向，动画在各端按实际速度与朝向变化表现。攻击时钟、伤害、冷却、死亡和既有网格／骨架／动作引用保持原配置；没有对所有动画统一设置 RateScale。

正式保存目标：

- `/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler`
- `/Game/Monsters/VortexCofferM25/BP_VortexCofferM25`

后台入口为 `Tools/MonsterAI/Complete-CofferMovement20261007.ps1`，资产保存脚本为 `Tools/MonsterAI/save_coffer_movement_20261007.py`。两目标构建及逐资产保存回执位于 `SourceAssets/CofferMovement20261007/Records/`，修改前源文件及蓝图快照位于同目录的 `Before/`。

首次构建遇到状态栏 `StatusEffectsHUD.cpp` 的 C4458：局部变量 `Slot` 隐藏 `UWidget::Slot`。仅改名为 `ScrollSlot` 以完成本次必要构建，未改变状态栏逻辑；修改前快照同样保留。

Editor、Game 构建均已完成（退出码 0），两个正式蓝图已通过后台 commandlet 保存，完成回执为 `Records/delivery.json`。未启动 UE 图形编辑器，未运行游戏测试、截图或渲染；实际效果交由用户测试。
