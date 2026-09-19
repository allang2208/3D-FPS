# M4 单手竖枪战术冲刺

后续已扩展到 AKM 与 QBZ191，见 [两把步枪的接入说明](rifle-tactical-sprint-20260915.md)。下面保留 M4 的原始制作记录。

最新的步行衔接和奔跑左手出镜修改，见 [衔接检查记录](rifle-sprint-transitions-20260915.md)：回步行退出已改为 0.30 秒，武器动作退出 0.16 秒，运行时统一使用连续姿态轨迹。

## 本轮范围

只接入当前 M4 的单手竖枪冲刺，沿用现有冲刺输入、速度、体力及 0.18 秒冲刺后开火等待。当前 M4 手臂、枪体、配件和换弹资产继续使用。

动作分三段：

| 阶段 | 时长 | 动作 |
| --- | --- | --- |
| Enter | 0.30 秒 | 左手先展开并向外、向下离开握持点；右手随后带枪竖起 |
| Loop | 0.60 秒源循环 | 右手单手持枪，左臂独立前后摆动；运行时按脚步距离相位采样 |
| Exit | 0.167 秒 | 沿进入路径反向落枪，最后让左手回握；时长短于现有开火等待 |

进入和退出共用连续进度，半途松开或重新按住冲刺时从当前位置反向。动作循环在进入末段渐入，并随落枪退出。ADS、开火及换弹仍由原有动画层与业务状态接管。

原厂、弹鼓、斜握把、垂直握把、侧倾握把、Prism 手挡各有自己的进入、循环及退出动画，共 18 个片段。握持配置优先级与原有握把动画相同。原厂和弹鼓源姿态补入了现有 UE 发布流程里的 12 mm / 32 mm 左手前移量。

## 参考与制作

本轮实际查看了项目已有的 `Saved/GunplayUpgrade/m4-sprint-final60/Preview/sprint_comparison.png` 和 `Saved/Reference/PistolBV1x6AgeTEPd20260914/reference-motion-sheet.jpg`。前者用于当前 M4 抬枪画面，后者只用于单手奔跑的松手、摆臂和回握顺序，并非步枪动作的精确复刻。

三段状态组织参考 [ARC9 MW22 的 M4 定义](https://github.com/Seulyy/ARC9-MW22/blob/main/lua/weapons/arc9_mw22_ar_m4.lua)。本轮动画由项目已有可编辑 M4 和握把姿态制作，没有引入 COD 提取动画或模型。

Blender 中以右腕为旋转中心，枪体全部机械骨骼与右手保持共同变换。左右臂分别计算肩、肘、腕及 twist 骨段；左手释放时只改变手指局部旋转。源码姿态为 +Y 向前、+X 向右、+Z 向上，单位米。动画以 120 Hz 导出，保留可编辑曲线。

## 文件

- 制作脚本：`SourceAssets/M4TacticalSprint20260915/author_sprint.py`
- 导入脚本：`SourceAssets/M4TacticalSprint20260915/import_sprint.py`
- 可编辑源：`SourceAssets/M4TacticalSprint20260915/<配置>/M4_TacticalSprint_<配置>_Editable.blend`
- FBX：同目录下 `Animations/`
- UE 资产：`/Game/Weapons/M4TacticalSprint20260915/<配置>/`
- 独立状态组件：`Source/FPSGAME/Weapons/M4TacticalSprintComponent.h/.cpp`
- 动画层：`Source/FPSGAME/Weapons/FPSGunplayAnimInstance.h/.cpp`
- 角色接入：`Source/FPSGAME/FPSGAMECharacter.cpp`
- 烹饪目录：`Config/DefaultGame.ini`

## 构建与使用状态

18 段动作已制作、导出并保存为 UE 动画资产，导入回执为 `SourceAssets/M4TacticalSprint20260915/import.json`。此轮没有运行游戏、回归测试或渲染验收，由用户测试画面和操作手感。

后台导入进程返回 1：项目已有 AssetManager 配置引用了未加载的 `/Script/GameFeatures.GameFeatureData`，产生一次 ensure 及其堆栈。导入脚本仍完成全部 18 段保存；FBX 动画导入另有绑定姿势警告。原始输出保留在 `SourceAssets/M4TacticalSprint20260915/import-commandlet.log`，没有将此进程记为无错误通过，也没有修改该全局配置。原生完整构建日志为 `Saved/BuildEditor/m4-tactical-sprint-20260915.console.log`。

新增状态放在独立组件中，没有新增 `AFPSGAMECharacter` 成员。动画实例增加了循环混合层，需要关闭项目编辑器后构建普通模块并重新打开；不能通过旧的后缀热重载模块使用本轮改动。

本轮已在编辑器关闭期间完成 `-Rebuild`：158 项构建任务，退出码 0，`Result: Succeeded`，输出普通 `UnrealEditor-FPSGAME.dll`。尚未启动编辑器或运行游戏测试。
