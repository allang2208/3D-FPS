# 虎啸镇岳配重锤：虎啸

唐刀 `ue_tang_dao` 安装 `pommel/tiger_mountain` 后，快速近战命中存活敌人，在该次命中结算后施加 `tigerRoar`（虎啸）。普通挥砍、重击、裂斩波不触发。

- 持续 6 秒，重复命中刷新至 6 秒，数值不叠加。
- 目标冲击、利器、钝器的有效韧性抵抗均为 0。
- 目标受到的韧性伤害乘以 1.25，不改变生命伤害。
- 到期恢复目标原有抵抗；不覆写怪物基础数值。沿用状态免疫、净化及重生清理。
- 护甲吸收直接伤害仍算命中；致死命中不向尸体施加状态。

配置在 `Content/ColdSteelData/melee-gunsmith.json`，由枪匠结算进入攻击快照；服务端从实际装备生成同一快照。`UColdSteelStatusModel::ApplySkillWeaponHit` 负责命中施加，`UCombatStatusFormula` 保存状态，`UMonsterCombatComponent` 消费临时韧性修正。

配件效果说明、物品提示、改造比较及状态目录同步更新；制作源 `SourceAssets/TangDaoMeshy20261002/TigerPommel20261002/catalog_extension.py` 保留该效果，避免后续重建外观目录时丢失。

按用户要求不启动编辑器、不运行游戏、不执行测试或验收，实际表现由用户测试。

后台 `FPSGAMEEditor Win64 Development` 构建成功，已链接 `UnrealEditor-FPSGAME.dll`。构建日志：`Saved/BuildEditor/tiger-roar-rebuild-20261003-174829.log`。

构建期间对既有角色身体代码做了三处类型修正以解除编译阻塞：`FPSPlayerBodyMotion.cpp` 的 `FName` 条件表达式与材质指针遍历，以及 `FPSPlayerBodyConsumable.cpp` 的组件指针遍历；保留原有行为。
