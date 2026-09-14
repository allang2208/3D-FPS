# 胖子僵尸枪击命中与死亡布娃娃

后续用户已调整死亡要求，最新行为见 [完整死亡动画与即时脓液](fat-zombie-death-timing-and-pus-20260914.md)：完整播放后才转布娃娃，脓液改为生命归零时立即生成。本文保留首次布娃娃接入记录。

用户反馈近战有效、枪械无效，同时要求接入死亡布娃娃。本轮读取现有玩家日志、武器/怪物代码和物理资产，修改及构建；不启动游戏或进行玩法、画面测试。

## 枪击链路与原因

- 枪械瞄准、枪口遮挡、飞行子弹与即时射击都使用复杂 `Visibility` 射线（`bTraceComplex=true`）；符文剑使用简单 `Visibility` 球体扫掠（`false`）。
- 两类武器最终均调用 `ColdSteelSkills::ApplyHit` → `ApplySkillWeaponHit` → `ApplyPointDamage` → 胖子/护士 `TakeDamage`。生命初值仍为 600，不存在独立的枪击免疫或按武器类型拒绝扣血的分支。
- 原 `install_damage_collision.py` 创建 18 个简单骨骼胶囊并设为 Kinematic，但未设置 `CollisionTraceFlag`。UE 5.8 的 `FBodyInstance::BuildBodyFilterData` 仅在 `CTF_UseSimpleAsComplex` 下为简单形体加入复杂查询标记。默认简单/复杂分离时，没有三角形碰撞的胶囊不会被枪械复杂查询命中。
- 本次在原 Physics Asset 上设置 `CTF_UseSimpleAsComplex`，让两类查询共享已拟合的身体形体。保留独立 `Head` 骨骼命中、遮挡、距离衰减及枪械伤害公式；不将整个世界的枪械射线改成简单查询。
- 现有 `FPSGAME_2.log` 记录了胖子扣血至 0、击杀和生成脓液，但没有区分武器身份，不能据此宣称枪击已正常。
- 此次实际资产修改前读数：18 个形体全部 `trace_flag=0`（Default）、`resolved_trace=1`（SimpleAndComplex）、`physics_type=1`（Kinematic），`per_poly=0`、`constraints=0`。与复杂射线遗漏简单胶囊的原因一致。证据：`Saved/Logs/FatZombie-combat-physics-install.log` 中 `FAT_PHYSICS_BEFORE` / `FAT_PHYSICS_BODY`。

## 死亡物理

此前 `AFatZombie::StartDeathPresentation` 关闭物理与碰撞，播放死亡片段。父类护士的布娃娃入口被覆盖；旧物理资产也没有关节，不能只打开模拟开关。

- 保留 18 个原蒙皮拟合胶囊，增加一个不参与碰撞的 `FatZombieRoot` 物理根。所有形体使用 `PhysType_Default`：存活时跟随动画，死亡时统一切换模拟。
- 按骨骼父链连接 18 个关节，锁定位移并限制躯干、颈头和四肢摆角。关节位置使用实际参考骨架空间，保留导入的 100 倍骨骼缩放换算。
- 物理根与骨盆刚性连接，防止物理骨架与可见模型根错位。相邻形体及参考姿态下已经重叠的胶囊关闭相互碰撞，其余肢体保留接触；总配置质量 200 kg，并配置阻尼、CCD 和求解迭代。
- 默认先播放 0.55 秒死亡起势，再从当前可见姿态进入布娃娃。网格保持世界变换脱离移动胶囊，停止动画写入物理骨骼，与地形碰撞；忽略 Pawn，避免尸体推挤玩家。
- 致死方向向骨盆施加 90 cm/s 的有限速度冲量。可调属性：`FatZombie|Death` 下的 `bDeathRagdoll`、`RagdollDelay`、`RagdollImpulseSpeed`。
- 生命归零仍由原死亡入口停止移动/攻击、清空目标、结算一次奖励；尸体保留 15 秒。布娃娃仅改变死亡表现，不新增扣血或奖励入口。
- 脓液继续锁定死亡原位置，在原死亡片段总时长约 2.5667 秒后生成；布娃娃位移不会拖动液洼。销毁角色同时清除布娃娃交接和脓液生成计时器，F6 清理规则保持不变。

## 制作与交付

- 原生：`Source/FPSGAME/Monsters/FatZombie.h/.cpp`、`FatZombiePhysics.cpp`。
- 资产：`Content/Monsters/FatZombieMeshy/SK_FatZombie_Meshy_PhysicsAsset.uasset`，不更换模型、蒙皮、材质或四段动画。
- 原资产副本：`Saved/FatZombieRangedRagdoll/before/`。
- 当前重建入口：在已构建的 FPSGAME 编辑器宿主执行 `Tools/FatZombie/install_combat_physics.py`。`inspect_combat_physics.py` 通过同一原生入口只读输出配置；这不是游戏运行测试。
- 最初 Python 直接读取物理形体数组失败，因为当前 UE 未向 Python 暴露这些数组；改用原生 authoring 入口读取和制作，不依赖猜测属性。

## 构建和资产记录

- Editor 最终构建成功，退出码 0：`Saved/Logs/FatZombie-ranged-ragdoll-Editor-final.log`，使用模块后缀 6141201。首次完整构建也成功；随后将本次新增诊断中的旧成员访问改为当前 getter，再完成增量构建。
- 物理资产制作完成，19 个形体、18 个关节，日志含 `FAT_PHYSICS_PREPARED` 和 `FAT_COMBAT_PHYSICS_SAVED`；记录 `Saved/FatZombieRangedRagdoll/asset_prepared.json`。该主工程命令进程退出码为 1，原因是已有 `GameFeatureData` 资产扫描规则缺失；脚本自身执行与本次物理资产保存已完成，没有将该退出码报告为命令整体成功。
- 未启动游戏或执行实战/画面测试。实际枪击、爆头、死亡接地与脓液配合由用户重开编辑器后测试。
- Game 构建成功，退出码 0：`Saved/Logs/FatZombie-ranged-ragdoll-Game-build.log`，已生成 `Binaries/Win64/FPSGAME.exe`。
