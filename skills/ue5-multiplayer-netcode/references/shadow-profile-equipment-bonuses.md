# 套装与装备加成在监听服务器上的取值路径

适用：新增了装备属性或套装效果，单机正常，但联机下客机（非主机玩家）的数值不对，或主机看不到客机的套装效果。FPSGAME 的联机数值读的不是“当前玩家”，而是**影子档案**。

来源：2026-10-22 野行套接入时的代码走查。只记录路径与判定规则，不代表已联机验收。

## 影子档案是唯一正确入口

`UColdSteelStatusModel::Current` 是主机本地存档。远端玩家的数值来自 `AFPSGAMECharacter::NetShadowProfile`，用 `GetNetShadowProfile()` 取，主机玩家会回退到单例。

所有按玩家读取装备/套装的代码都必须走这条路径：

```cpp
UColdSteelStatusModel* M=nullptr;
if(const auto* Character=Cast<AFPSGAMECharacter>(Shooter))M=Character->GetNetShadowProfile();
if(!M&&Shooter&&Shooter->GetGameInstance())M=Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
```

已按此模式实现的入口（可直接参照）：`ColdSteelSkillRules::Snapshot`、`FPSQuickCombatComponent`、`RuneOrbBladeProjectile`、`BowWeaponComponent`、`ProductionToolComponent`、`ColdSteelPlayerState` 的大部分事务、`FPSCombatHealthComponent` 的受击结算。

**反例**：直接用 `GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()` 读远端玩家的装备，拿到的是主机自己的档，表现是“客机的套装在主机上永久不生效”或“客机打出主机的属性”。

## 套装识别在影子档上同样成立

`ArmorSet()` 与各 `*SetComplete()` 走 `CombatItemFormula::ReadOnly(Item)`，只依赖物品实例 Data + 主机本地 `source-combat-items.json`。因为客机上传的是物品实例 Data（不含覆盖层），覆盖层由**主机**在读取时补齐，所以：

- 主机目录里必须已有该套装的 `armorSet`，客机的套装才会被识别。
- 客机自己目录缺条目不影响判定，判定发生在主机。
- 物品实例里若残留旧 `bonusStats`，会盖住覆盖层（见 [套装效果三层数据](equipment-set-effect-layers.md)），这个问题在联机下同样存在，因为影子档复制的就是实例 Data。

## 移动与速度类要分清“算在哪一侧”

- `ColdSteelWeaponStats::Reload` / `Interval` 是纯函数，客机本地 UI 与主机结算都会各算一次；结果应一致，因为输入（影子档、目录）同源。
- 移速类（`CombatMoveMultiplier`）由角色移动组件消费，客户端会做预测；数值分叉会表现为“客机脚下打滑或卡顿”，排查时先比主机与客机读到的 `EquipmentBonus` 是否一致。
- 伤害永远以主机 `ApplyHit` 的结果为准，客机本地只做表现。

## 影子档的生命周期与陷阱

- `CreateShadowModel()` 会复制目录状态（定义、弹药、技能），但**不会**自动重读覆盖层——覆盖层是 `CombatItemFormula` 内部静态缓存，进程级共享，因此主机改 JSON 需重启才生效。
- 影子档的 `bNetShadowProfile=true`，写盘路径被拦；不要试图让影子档自己保存。
- 客机重新上传整档时走消毒与合并；服务器侧计数器（魂值等）以影子档水位为准，不用客机数值。

## 排查顺序

1. 先确认读的是不是影子档（有没有 `GetNetShadowProfile()`）。
2. 再确认主机目录里该装备有 `armorSet`，且实例 Data 没有残留 `bonusStats`。
3. 然后确认 `SetEffect()` 是否为该套装 id 加了分支——JSON 不会自动产生效果。
4. 最后才看客户端预测与同步时序。

## 交付口径

编译通过不等于联机可用。至少分别记录：源码路径核对、是否编译、是否真实双端联机验证。三者混写成“已完成”会让下一个人误判。
