# 冰墙升空召降与落地状态同步

2026-09-30 用户要求冰墙释放后，凝聚冰块向上快速消失，墙体从落点上方砸下，地面出现项目已有烟尘和烟雾；同时排查击退与减速是否同步。

## 当前释放过程

- 凝聚、法杖悬浮点、建筑预览与 R 切高墙／矮墙沿原输入流程。确认时冻结预览位置和形态。
- 接触时释放：种子在 0.16 秒内向上移动 160 cm 并缩小消失，不再沿玩家到落点的路径飞行。
- 随后完整墙体直接在锁定落点上方出现，从最高 360 cm 的高度，在 0.22 秒内加速砸下。通过整面墙的垂直盒扫掠，按实际顶棚／梁体／上方障碍限制下落高度；最终放置合法性沿用原判断。
- 落地当帧结算伤害、击退、寒冷与落地特效，之后开启连续阻挡盒、动态导航及共享生命。持续时间从落地起计；下降阶段无阻挡，不是伤害投射物。
- 当前生命仍为 `300 + 50 × (等级−1)`，宽度仍为 `42 × [5 + 2 × (等级−1)] cm`，高墙 260 cm、矮墙 100 cm；仅陨星与冰墙要求法杖。中立、玩家／怪物可破坏、不显示血条等合同保持。

参数来自 `Content/ColdSteelData/skills.json` 的 `riseSeconds`、`riseHeightCM`、`dropSeconds`、`dropHeightCM`，随凝聚快照。旧 `flySpeedCM`、`growthSeconds` 已从冰墙数据／读取器／类型中替换；其他技能对应参数不变。技能说明与详情操作文案同步。

## 落地烟尘和寒雾

实际保存 `/Game/Skills/IceWall/SlamV1/NS_IceWallLanding`，后台作者 `Tools/Skills/build_ice_wall_landing.py`。一次落地一个系统，包含两个同刻出生的一次性发射器：

- `GroundDust` 复用 `/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke`，灰褐烟尘从墙底两侧快速向外翻卷，0.65–0.95 秒消散。
- `GroundColdMist` 复用 `/Game/Skills/IceSpike/FrostV2/MI_ColdMist` 及其 8×8 图集，低矮灰蓝冷凝雾，0.95–1.30 秒消散。

颗粒出生区随墙宽铺开，粒径不跟技能等级放大。烟尘上限 32 片、寒雾上限 24 片，细节削减后仍铺满整面墙。接共享 `ConfigureSmoke` 的风、数量预算与五个接触面，使用 Niagara AutoRelease 池；源材质／原系统未改。组件起始异步加载持续寒雾及落地系统，不在落地 Tick 同步加载。已加入 AlwaysCook；制作回执 `Saved/IceWallSlam20260930/asset-authoring.json`。

墙体持续寒雾仍使用 `ColdMistV1/NS_IceWallColdMist`。种子升空结束时清掉原位置烟片、重置 PreviousPosition，然后在下落墙体处重新激活，避免从法杖到目标横跨一道雾线。矮墙雾保留在下半部，方便架枪。

## 击退／减速排查与修复

原路径 `BecomeSolid → ApplyIceWallSpawn` 只结算成墙伤害和击退；`ApplyIceWallChill` 在成墙后等待一秒的光环 Tick 才第一次执行。击退距离包括清出墙体的距离和附加击退，目标可能被推出 150 cm 光环范围，造成击退与减速脱节。

当前 `Land → ApplyIceWallSpawn` 对每个仍存活的命中敌人，在位移前添加一次寒冷：一层 3.5% 减速、2.5 秒。击退继续扫掠推向墙面安全侧，保持原清位距离，不穿过其他阻挡。即使目标最终离开光环，也保留此次落地寒冷。

落地事件还立即对墙边光环范围执行一次寒冷，排除已经处理过的成墙命中集合，避免同一落地重复加两层。之后按原一秒节拍叠层。死亡、友方、施法者、状态免疫和冻结的处理沿现有目标与 `AddChill` 规则。

减速消费端已按源码追踪：`UMonsterCharacterMovementComponent` 继承 `UFPSCharacterMovementComponent`，后者 `GetMaxSpeed` 读取 `UCombatStatusFormula::MovementMultiplier`，按 `1−层数×每层减速` 影响实际移动；不是只添加 HUD 状态。未改共用移动／状态公式。

## 交付范围

新 Niagara 已由后台 commandlet 编译并保存，作者退出码 0。
常规 Editor 首轮构建成功（283.99 秒），日志 `Saved/IceWallSlam20260930/build-editor.log`。之后将顶棚扫掠起点提高到离地 10 cm，避开放置允许的 6 cm 地面支撑误差。
最终 Editor 重编曾完成冰墙源码及 `UnrealEditor-FPSGAME.dll` 的链接，但全目标退出码 6：运行中的 FPSGAME-mp 编辑器占用了根工程共享 `Plugins/AutoFootstep/Binaries/Win64/UnrealEditor-AutoFootstep.dll`，LNK1104。历史日志 `Saved/IceWallSlam20260930/build-editor-final-four.log`；没有关闭该编辑器或跨任务协调。调整并行度前的双路构建由本任务停止，未动他人进程。
用户保存关闭编辑器并要求继续后，完整 Editor 构建已成功（474.51 秒，退出码 0），最终日志 `Saved/IceWallSlam20260930/build-editor-complete.log`。源码、已保存 Niagara、Editor DLL 和 Game 程序均已落盘；构建后未打开或重启编辑器。
Game 构建成功（776.03 秒），日志 `Saved/IceWallSlam20260930/build-game.log`，包含最终顶棚扫掠调整。
本轮仅按用户请求排查状态应用时序；未启动编辑器界面、游戏、PIE、截图、渲染或额外自测，观感与实机由用户测试。
