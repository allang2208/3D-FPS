# 上挑：游戏内动作技能

2026-10-04 V20：主动上挑前踏 150 cm 的推进结束点由 1.160 秒提前至 1.050 秒，与刀刃进入正前方的时刻对齐；扫掠按角色实际、受碰撞约束后的位移计算，见 [V20 位移与接触](../Weapons/sword-uppercut-lunge-contact-v20-20261004.md)。当前恢复入口、废案归档与公开源码范围见 [整理发布](../Weapons/sword-uppercut-publication-20261004.md)。

2026-10-04 V19：基础判定范围提高 25%，距离按 `原突刺距离 × 1.25 × [1 + 0.01 × (等级 - 1)]` 成长；宽度不随等级继续扩大。技能页显示当前／下级距离和倍率，见 [V19 范围与成长](../Weapons/sword-uppercut-range-v19-20261004.md)。

2026-10-03 接入正常技能列表和快捷栏。2026-10-04 接入 V17 空间扰动、突刺范围、重击 70% 伤害及独立成长；当前 V18 增加释放消耗 25 体力、基础冷却 8 秒，见 [V18 消耗与冷却](../Weapons/sword-uppercut-cost-cooldown-v18-20261004.md)。

## 用法

1. 打开游戏的技能页，在「全部」或「主动」分类找到「上挑」。
2. 将卡片拖到 Q／E／X／1–4 任意快捷槽，绑定沿用原有保存事务；不会自动替换已有槽位。
3. 装备剑，结束当前动作后按绑定键。武器与双臂先向右下移出镜头蓄力，释放时前踏一步，伴随普通攻击挥剑声快速向前上方劈出，镜头由右下蓄势甩向左上；左手沿用待机正握、右手靠护手，以剑尖向上、剑柄在下且略向前倾的姿态收势，再缓慢回到待机，可以再次发动。前踏受现有地面和胶囊碰撞约束。

在 1.000–1.125 秒结算突刺范围内的单目标命中。按上挑自身等级计算同级重击公式后乘 70%，等级 1–20，每级力量 +1；单次修炼取释放 +1／命中 +5／击杀 +12 的最高档，升级需要当前等级×300。V18 在实际释放点扣除 25 体力并开始 8 秒基础冷却，蓄势取消不扣费。技能页、快捷栏倒计时、升级通知及版本 21 存档迁移已接入，保持当前动作节奏。

动作状态加入剑的 IsBusy；普通挥砍、重击、格挡、奔跑持剑姿态及新的施法遵循已有占用关系。移动照常进行。换装、死亡、菜单及已有高优先级动作通过 CancelAction 释放上挑占用，沿用原回位衔接。

## 实现与资产

2026-10-04 的运行参数调整见 [镜头与前踏 V16](../Weapons/sword-uppercut-feel-v16-20261004.md)：主镜头拉扯幅度扩大至 V15 的 1.5 倍，前踏由 75 cm 翻倍为 150 cm；动画资产继续沿用下述 V15。

- 数据 ID：`swordUppercut`，元数据入口 `Content/ColdSteelData/skills.json`。
- `Source/FPSGAME/Weapons/RuneSwordUppercut.cpp`：异步预加载、当前握距选片、状态提示和触发。
- `RuneSwordComponent` 的独立分支按动画长度推进；V17 通过 `TickUppercut` 复用突刺扫掠与武器伤害链，最高档修炼在接触窗口结束结算。
- 标准与长握柄分别播放 `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard`、`/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip`，路径保留 V1 名称，本轮制作为 2.05 秒 V15。保留现有武器／V7 手臂／服装挂接；长握柄片不再次套用已有动作的差量。当前设计、制作源与保存结果见 [对角镜头与握柄回位 V15](../Weapons/sword-uppercut-grip-recovery-v15-20261003.md)。
- 1.000 秒出手时播放普通挥砍的攻击层及当前装备剑的挥剑层；V17 同时启动由下向上的空间扰动，命中音沿用武器命中链。
- 技能页、详情、拖拽、快捷槽图标及不可用提示沿用原生冷钢 UI。当前图标为圆角银色方框、无脸人物上挑与上扬剑光，源在 `SourceAssets/SkillIconRoundedSquare20261004/UppercutSilhouetteV5`，PNG 和 UE 纹理已正式替换；恢复清单为 `Tools/UI/prepare_cold_steel_skill_icons.py`，保存回执为同作者根目录的 `DeploymentV1/deployment_result.json`。
- 原独立场景及当前 V15 可编辑 Blender／FBX／关键帧源保留；V1–V14 退役版本移入 `trash/sword-uppercut-retired-20261004`。新的日常入口为技能栏，无需打开原试播地图。

布局和数据合同见 `Docs/UI/sword-uppercut-skill-plan-20261003.md`。不使用付费动画。本轮按用户明确要求检查了上挑握柄与回位，包括作者姿态和 UE 指定姿态读回；未启动游戏，离线姿态图不代表实机效果验收。

## 初次技能接入构建（历史）

`FPSGAME Win64 Development` 和 `FPSGAMEEditor Win64 Development` 均已常规构建成功，退出码 0，正式 Game 产物和 `UnrealEditor-FPSGAME.dll` 已落盘。历史回执现位于 `trash/sword-uppercut-retired-20261004/SourceAssets/SwordUppercut20261003/skill_build_receipt.json`，对应日志文件名带 `20261003-104200`。没有使用 Live Coding，也没有启动或重启编辑器；实机效果由用户测试。

必要构建修复：`Characters/FPSPlayerBodyComponent.h` 中 `AppearanceLoad` 的 `FStreamableHandle` 前置声明由 `class` 统一为引擎使用的 `struct`，解决 C4099 编译错误；没有修改外观逻辑。
