# 单手近战普通攻击判定缩窄与弯刀／战斧对照

2026-11-03，用户要求基础攻击判定范围再减 20%，并核对弯刀与战斧的范围、距离。此次将“判定范围”落实为普通连击的球扫半径与低位补判夹角，攻击距离独立保留。

| 参数（原装） | 尼泊尔弯刀 | 碳钢战斧 |
|---|---:|---:|
| 普通攻击基础距离 | 220 cm | 220 cm |
| 普通攻击球扫半径，调整前 | 26 cm | 26 cm |
| 普通攻击球扫半径，调整后 | 20.8 cm | 20.8 cm |
| 球扫直径，调整后 | 41.6 cm | 41.6 cm |
| 低位小目标补判总夹角，调整前 → 后 | 60° → 48° | 60° → 48° |
| 低位补判距离上限 | 120 cm | 120 cm |

`KukriRhythm::BasicAttackQueryWidthScale = 0.8` 只在 `UKukriWeaponComponent::TraceBlade` 的普通连击状态 `bAttacking` 生效。普通球扫半径和低位补判夹角各乘一次；`QueryQuickAreaContacts` 新增带低位夹角参数的重载，原有入口保留，其余调用者使用原默认值。

当前 `items.json` 中单手近战分类只有 `ue_kukri` 与 `ue_tactical_hatchet`。两者均走 Kukri 动作执行器；后续沿用该执行器的单手近战同时继承此规则。

检查覆盖普通三段、双持交替挥砍、双持同时突刺／双斧下劈和每把武器的距离快照。主手近战配副手枪也使用该普通攻击入口。主手枪／法杖配副手近战的快速近战属于武技，保持原技能判定。重击、主副手上挑、冲刺与风车也不使用本次缩窄倍率。场景接触的真实刃段 2.5 cm 球扫保持原值，只用于墙面／玻璃等接触反馈，不扩大敌人命中。

距离统一由 `ColdSteelMelee::Evaluate` 计算：

```text
普通攻击距离 = melee_reach_cm × 安装改造的 range_mult 乘积
```

两者原装均为 220 cm。弯刀猎手刀身 `hunter_blade` 与战斧长柄握把 `hatchet_grip_long` 的范围倍率均为 1.25，因此单独安装时均为 275 cm。双持每把武器分别读取自己的改造距离，不将两把武器的距离累加，也不互相复制加成。破阵握柄和隼喙凿锋斧刃不提供距离倍率。

数值与查询规则一致不表示不同动作每帧覆盖完全相同：查询起点随手中武器的骨骼握点运动；第三段弯刀为刺击，战斧为下劈。查询以 `BladeMid` 为共同局部采样点，向稳定瞄准方向扫掠 `max(40 cm, 武器距离 − 起点前向深度)`；球扫边缘与目标碰撞体也参与接触，220 cm 并非“目标中心超过此距离必定不中”的严格球形截止。改造模型的真实刃根／刃尖只用于场景接触，不替代敌人攻击距离。

服务端普通攻击检查了动作提交、接触时窗、目标去重与遮挡，但当前通用命中距离容差仍沿用 `Shooter->TraceDistance × 1.25`，没有为这两种武器各自重建球扫。两者在这一点上也使用相同规则；本次不将范围缩窄表述为服务端严格几何复核已完成。

证据入口：`Content/ColdSteelData/items.json`、两者枪匠目录、`Weapons/MeleeWeaponStats.cpp`、`Weapons/Kukri/KukriWeaponComponent.cpp`、`Weapons/MeleeSmallTargetQuery.cpp`、`Multiplayer/ColdSteelKukriAuthority.cpp` 与 `Multiplayer/ColdSteelPlayerState.cpp`。

本轮完成配置与代码路径核对；必要后台构建状态见 `SourceAssets/OneHandBasicQuery20261103/build_receipt.json`。未启动编辑器、游戏或多人实机测试，手感由用户测试。

后台 `FPSGAMEEditor Win64 Development` 最终构建成功，Editor 基础 DLL 已落盘。首轮状态同步组件生成头错误在重新生成头文件后消失；后续共享查询的旧签名链接错误通过保留原入口、增加重载解决。未修改状态同步组件的功能代码。构建成功不代表实机距离或多人效果已验收。
