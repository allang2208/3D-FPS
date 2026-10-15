# 双手战锤砸地反馈与技能判定 — 2026-10-14

本次按用户要求升级重击与冲刺砸地共用的视觉效果；冲刺攻击改用 `dashAttack` 技能伤害，重击增加基础 2 秒眩晕。

后续用户截图否定本版的放射线裂纹表面；地裂已转由 `CrackReliefV3` 的原创 PBR 凹陷／破碎块面材质接替，见 `steel-warhammer-fracture-relief-v3-20261014.md`。本版的烟尘、飞散碎石、共享池与玩法改动继续使用。

## 玩法

- 冲刺伤害通过 `Profile->DashAttackStats().DamageMultiplier` 读取当前技能等级数值，以当前战锤改造后的伤害面板乘算，按双手剑的技能口径对总值向下取整，保留物理、魔法和附加伤害的构成比例。不再乘重击倍率。
- 单机与服务器提交共用 `WarhammerCombat::Damage`。冲刺仍沿用战锤的圆形冲击波（默认半径 300 cm，扩散 0.36 秒），每目标仅一次，保留高度、墙体、阵营过滤。
- 真正蓄满的重击对普通／杂兵品阶或已经破韧的怪物施加显式眩晕。先结算伤害再判断，包含被这一击打出破韧的目标；死亡和伤害无效目标不添加。未破韧的精英、领主和首领不满足条件。
- 默认 `WarhammerCombat::HeavyStunSeconds = 2`，物品可用 `heavy_stun_seconds` 覆盖基础值。沿用现有 `CombatStatusFormula::AddStun`、免疫、控制计时与网络同步；较长的已有眩晕不会缩短。
- 冲刺共享砸地视觉／范围，不获得本次新增的重击眩晕。普通三连击数值、判定、动作、体力消耗和现有重击倍率不在本次修改范围。
- 无有效地面时仍走原近身接触回退，重击的合格目标可眩晕，不伪造地面波或地面特效。

## 特效

命中时保留原扩散环与砸地声音，同时启动三层局部表现：中心尘爆、横向扩散的滚动烟尘、向外弹起回落的小碎石。地面投射不规则分叉裂纹，带破口暗部和碎边亮部，3.3 秒后开始淡出，5 秒结束。

烟尘复用项目原创 Mantaflow 64 帧 8×8 密度图集 `T_MuzzleSmokeMantaflowV14`，读取 R 通道并插值相邻帧，保留透明边界与深度淡化。碎石为本次原创低面数碎块，不创建刚体。裂纹是贴花视觉，不修改地形或碰撞。

`UWarhammerSlamFXSubsystem` 每世界最多 8 个复用槽；每槽最多 10 片烟尘、14 个碎石实例、1 个裂纹贴花。受共享 `FluidPresentationSubsystem` 细节预算和 60 m 距离限制，满槽替换最旧效果。烟尘最长 1.9 秒、碎石 1.5 秒、裂纹 5 秒。装饰几何查询使用共享额度；新增装饰资产在世界开始时异步加载并持有，不在单次砸地时同步加载。以上是实现预算，没有进行性能采样。

特效由复制冲击波的本地表现触发，在独立装饰池中完成余烟和裂纹；伤害仍由服务器原冲击波管理，不因特效寿命延长、距离裁剪或预算不足而改变。

## 交付源与落盘状态

- 运行代码：`Source/FPSGAME/Production/WarhammerCombat.*`、`WarhammerSlamFXSubsystem.*`、`WarhammerShockwave.*` 与原战锤攻击提交／接触入口。
- 可编辑源：`SourceAssets/SteelWarhammer20261014/SlamFXV2/` 内 Blender、FBX、HLSL、作者脚本与导入脚本。
- 目标资产：`/Game/Weapons/SteelWarhammer20261014/SlamFXV2/` 内 `M_WarhammerDust`、`M_WarhammerDebris`、`M_WarhammerCracks`、`SM_WarhammerDebris`。
- 原有战锤目录已经纳入打包，无新增重复 Cook 根目录。
- 四项资产均已实际导入并保存：`import_receipt.json` 为 complete，后台 `import-commandlet-02.log` 退出码 0。首次导入在保存前遇到 Python 编辑器属性赋值错误，已统一改为 `set_editor_property` 后完成落盘；保留首次日志。
- 正式 Editor 构建状态见同目录 `build_receipt.json`、`build-FPSGAMEEditor.log`。最后将技能取整调用与双手剑统一为 `FloorToFloat`，避免浮点倍率在整数边界上的口径差异，随后执行增量正式构建。
- 按用户规则，不启动游戏、不预览、不截图、不做玩法／视觉／多人验收，交由用户测试。

最终补编已完成：用户授权清理残留后台 UE 后，正式 `FPSGAMEEditor` 的 204 个构建项成功结束，游戏模块及 ColdSteelNet 的 Editor DLL 均完成链接。`FloorToFloat` 的最终取整修正已进入正式 DLL；同轮也包含恢复旧骨链的普通三连击 V4。最新状态见 `build_receipt.json` 和 `delivery.json`，不再有待补编项。
