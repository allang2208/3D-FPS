# 上挑：游戏内动作技能

2026-10-03。用户反馈独立试播场景无法进入，改为通过正常技能列表和快捷栏在游戏中使用。本轮先接动作，不设置数值与修炼项目。

## 用法

1. 打开游戏的技能页，在「全部」或「主动」分类找到「上挑」。
2. 将卡片拖到 Q／E／X／1–4 任意快捷槽，绑定沿用原有保存事务；不会自动替换已有槽位。
3. 装备剑，结束当前动作后按绑定键。武器与双臂先向右下移出镜头蓄力，释放时前踏一步，伴随普通攻击挥剑声快速向前上方劈出，镜头由右下蓄势甩向左上；左手沿用待机正握、右手靠护手，以剑尖向上、剑柄在下且略向前倾的姿态收势，再缓慢回到待机，可以再次发动。前踏受现有地面和胶囊碰撞约束。

暂不结算伤害、命中、击退、消耗、装备附伤或修炼；不设额外冷却，不受攻速缩放。技能不创建等级／经验记录，详情中没有等级、数值对照和修炼栏目。现有档案可直接绑定，不改技能进度版本。

动作状态加入剑的 IsBusy；普通挥砍、重击、格挡、奔跑持剑姿态及新的施法遵循已有占用关系。移动照常进行。换装、死亡、菜单及已有高优先级动作通过 CancelAction 释放上挑占用，沿用原回位衔接。

## 实现与资产

2026-10-04 的运行参数调整见 [镜头与前踏 V16](../Weapons/sword-uppercut-feel-v16-20261004.md)：主镜头拉扯幅度扩大至 V15 的 1.5 倍，前踏由 75 cm 翻倍为 150 cm；动画资产继续沿用下述 V15。

- 数据 ID：`swordUppercut`，元数据入口 `Content/ColdSteelData/skills.json`。
- `Source/FPSGAME/Weapons/RuneSwordUppercut.cpp`：异步预加载、当前握距选片、状态提示和触发。
- `RuneSwordComponent` 的独立分支按动画长度推进，不调用 StartSwing、SweepBlade、技能结算或修炼。
- 标准与长握柄分别播放 `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard`、`/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip`，路径保留 V1 名称，本轮制作为 2.05 秒 V15。保留现有武器／V7 手臂／服装挂接；长握柄片不再次套用已有动作的差量。当前设计、制作源与保存结果见 [对角镜头与握柄回位 V15](../Weapons/sword-uppercut-grip-recovery-v15-20261003.md)。
- V15 延续 V14 音效在 1.000 秒出手时播放普通挥砍的攻击层及当前装备剑的挥剑层，与动画、前踏和镜头反馈共用时钟，不触发命中或其他普通攻击结算。
- 技能页、详情、拖拽、快捷槽图标及不可用提示沿用原生冷钢 UI。上挑专用图标为原创银色六边形、剑和向上弧线，源在 `SourceAssets/SwordUppercut20261003/Icon`；恢复清单已接入 `Tools/UI/prepare_cold_steel_skill_icons.py`。
- 原独立场景及可编辑 Blender／FBX／关键帧源保留。新的日常入口为技能栏，无需打开原试播地图。

布局和数据合同见 `Docs/UI/sword-uppercut-skill-plan-20261003.md`。不使用付费动画。本轮按用户明确要求检查了上挑握柄与回位，包括作者姿态和 UE 指定姿态读回；未启动游戏，离线姿态图不代表实机效果验收。

## 初次技能接入构建（历史）

`FPSGAME Win64 Development` 和 `FPSGAMEEditor Win64 Development` 均已常规构建成功，退出码 0，正式 Game 产物和 `UnrealEditor-FPSGAME.dll` 已落盘。回执为 `SourceAssets/SwordUppercut20261003/skill_build_receipt.json`，对应日志文件名带 `20261003-104200`。没有使用 Live Coding，也没有启动或重启编辑器；实机效果由用户测试。

必要构建修复：`Characters/FPSPlayerBodyComponent.h` 中 `AppearanceLoad` 的 `FStreamableHandle` 前置声明由 `class` 统一为引擎使用的 `struct`，解决 C4099 编译错误；没有修改外观逻辑。
