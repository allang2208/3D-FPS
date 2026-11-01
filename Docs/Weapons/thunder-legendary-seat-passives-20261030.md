# 雷神之锤：贯雷与疾雷传说改造

用户于2026-10-30指定，两款中央锤座改为传说改造，并新增安装后常驻的被动属性。

| 改造 | 等级 | 常驻属性 | 目录字段 |
| --- | --- | --- | --- |
| 贯雷锤座 | 传说改造 | 物理伤害+10% | physical_damage_mult = 1.1 |
| 疾雷锤座 | 传说改造 | 攻击速度+20% | attack_speed_mult = 1.2 |

正式配置位于 `Content/ColdSteelData/thunder-god-hammer-gunsmith.json`，ID和槽位沿用原值；两款仍限定雷神之锤并占用同一中央锤座槽。`GunsmithModificationTier.h` 同步返回 Legendary。

被动沿用现有战锤属性链路：WarhammerGunsmith解析 → GunsmithSystem汇总 → ProductionToolStats／WeaponDamagePanel消费。贯雷使用完整物理通道（基础与附加物理）的既有倍率；疾雷使用既有攻击速度倍率与上限。属性卡由数值评估器生成，旧列表文案同步为“物理伤害+10%”／“攻击速度+20%”，不重复写入特效段。

原有投掷、召回、落雷、感电、眩晕与蓄力机制继续使用当前实现。没有额外修改魔法伤害、蓄力速度或技能冷却。

独立发布入口和回执：`SourceAssets/ThunderGodHammer20261028/SeatLegendary20261030/`。同时同步会写入这两项属性的 GuanLeiReturnC8、GuanLeiInlaidC7、ThunderThrowV1 与 JiLeiSeatV1 注册脚本；本次没有运行旧模型发布器或替换模型。

默认后台制作与必要编译；未启动游戏、未执行自测或联机验收。实际构建结果见该批次 build 回执。

本轮正式目录已写入；FPSGAMEEditor 增量构建完成，6个构建动作，Result: Succeeded，原生DLL已链接。
