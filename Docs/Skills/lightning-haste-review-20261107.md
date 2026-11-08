# 雷电迅捷：纯元素图标与定向排查（2026-11-07）

## 图标

按用户补充的规则，魔法图标不含人物模型、人体轮廓或手脚。实际参考当前 `lightning_cold_steel.png`、`thunder_lance_cold_steel.png` 和 `storm_domain_cold_steel.png`：银色圆角方框、石墨暗底、蓝白电光。主体为三股向前加速的电流及环绕尾迹。

- 游戏读取：`Content/ColdSteelData/Skills/lightning_haste_cold_steel.png`。
- 选用源：`SourceAssets/LightningHasteReview20261107/Icon/lightning_haste_cold_steel.png`，1254×1254 RGBA，框外透明。
- 制作方式及完整提示词：同目录 `prompt.txt`。使用内置 imagegen 编辑已有魔法图标。
- `skills.json:lightningHaste.icon` 保持既有路径；UI 直接读 PNG，无需另造 Texture uasset。
- `Tools/UI/prepare_cold_steel_skill_icons.py` 增加最终源覆盖；旧 `Tools/Skills/draw_lightning_haste_icon.py` 改为只恢复这张选用图，不再绘制旧六边形。
- 同一游戏进程可能保留已有图标纹理，重新进入游戏后读取新 PNG。

## 本次修正

1. **新连斩漏用迅捷动作速度。** `RuneSwordChainSlash.cpp` 原先直接按真实秒推进动作。现在在已有源时间重映射外应用 `LightningHaste::ActionSpeed`，余帧按倍率换回真实秒；手臂采样、命中窗口、挥刀音和刀光继续使用同一个 `Elapsed`。命中停顿保持真实时间，不随加速缩短。
2. **电弧可能绑定到收起的手臂。** 单手/副手武器会通过骨骼零缩放收起另一条手臂，而不是设置 HiddenBone 标记。原筛选只判断骨名及 HiddenBone，会误选这条手臂。`LightningHastePresentation.cpp` 现在同时排除组件空间零缩放骨骼，并在逐帧显示时重判。切换来源和清理特效时移除旧骨架 Tick 前置依赖，避免一直保留旧武器依赖。
3. **联机释放重复通知。** 迅捷的 `CommitLightningHasteCast` 已经发送 `NotifyMagicReleased`，通用网络接受分支原来又调用一次。迅捷分支现在仅回执，保留提交时的一次通知。这是重复状态刷新/通知，并非两层数值加成。

## 排查范围与现有接入

| 范围 | 本次所见 |
| --- | --- |
| 数值与详情 | `skills.json`、`LightningHasteStats` 和详情读取同源。1级移速+10%、动作+5%、20秒；20级分别+29%、+14.5%、29.5秒。未改平衡数值。 |
| 施法、费用、动作占用 | 起手扣蓝并预留冷却，生效时重置完整冷却；未释放取消退款；已生效不可重复叠加；双手占用和其他动作按共用手势规则处理。 |
| 加速入口 | 移动、枪械射击/换弹、法杖普攻、施法、弓搭箭/拉弦、剑锤攻击、副手快速近战、消耗品、闪避/翻越等已有专用入口。新增连斩遗漏已补；双手武器检视使用其明确约定的独立展示节奏。 |
| 修炼与生命周期 | 击杀入口接入 `NotifyKillByOwner`，去重及友军/召唤物/训练过滤；结束统一结算，死亡和离场清理。 |
| 存档 | 已有 v24 迁移、进度/冷却字段与校验、退款清冷却；活动增益不跨存档恢复。 |
| UI 与资产 | 技能卡、详情、快捷栏、状态文字、后台预载均有入口；现有迅捷 Niagara 资产在盘。 |
| 网络 | 权威费用和开始状态、CastId 对应回执、预测确认/拒绝、状态复制与离场结算均有入口；修正重复释放通知。 |

以上是当前源码与定向离线排查范围，不等于所有动作、模型和网络组合已进行实机验收。

## 离线排查入口

`SkillNetworkAudit -LightningHasteOnly` 调用 `LightningHasteAudit20261107.cpp`，使用独立 `SkillNetworkAudit_<GUID>` 档案，不开始地图，不创建实际网络传输，也不渲染/试听。

覆盖等级成长、缺蓝、重复施法、击杀档位与去重、死亡/到期、迟到/重复回执、预测确认、新连斩加速/停顿/源时间映射，以及使用实际手臂骨架复现的零缩放附着选择。输出为 `Saved/LightningHasteReview20261107/native-result.json`。

游戏内图标观感、电弧表现、动作手感及真实多人网络仍交由用户测试。

## 本次结果

- `FPSGAMEEditor Win64 Development` 已后台编译成功；最终日志 `Saved/BuildEditor/build-20261107-172551.log`。
- `FPSGAME Win64 Development` 已后台编译成功、退出码 0，更新 `Binaries/Win64/FPSGAME.exe`；日志 `Saved/LightningHasteReview20261107/build-game.log`，构建耗时 125.62 秒。
- 专项离线检查 **31 项通过、0 项失败，进程退出码 0**；日志 `Saved/LightningHasteReview20261107/audit-final.log`，明细 `native-result.json`。
- 初次离线结果中的 3 项失败源于检查环境没有本地玩家标记，进入了远端分支；补齐隔离控制器标记后重新执行，实际零缩放骨架复现及三项附着选择均通过。初次记录保存在 `native-result-initial-fixture.json` 和 `audit-initial-fixture.log`。
- 新 PNG 已在运行目录落盘，与选用源一致，`skills.json` 仍指向该文件。未启动图形编辑器、地图游戏或真实网络测试。
