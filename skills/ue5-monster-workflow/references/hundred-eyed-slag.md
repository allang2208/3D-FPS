# 百目炉渣：不对称巨臂、恢复段与烟雾状态

2026-10-02。非常规四肢怪物采用专用骨架，攻击的视觉重点是最大右臂。用户已认可 RampageV8 的横扫和下劈攻击主体，随后要求修下劈收势；V9 收势及后续烟雾修订没有当前用户验收记录。不要把局部动作认可扩展成整只怪物合格。

## 巨臂动作源与蒙皮

早期自行构造大臂轨迹多次未获认可。此类非标准比例的主要攻击器官，先取得能体现蓄势、肩肘配合、躯干移重、落击和收勢的完整动作参照。本例供体为用户下载导入的 Epic Paragon Rampage；免费取得和项目使用许可不等于可公开供体网格、蒙皮、导出动画或逐帧姿态数据。

- 重定向使用肩、肘、腕整条链及供体身体配合，保持目标骨长和可达性；仅放大手掌位移或增加腕旋转会继续折叠关节。
- 沿巨臂补充 twist 与肘腕体积支撑骨，使用稳定的肘平面及分段权重过渡。辅助骨需要与整条臂的姿态一起返回，不能在收势时突然切回供体参考轴。
- 本例 V9 保留已认可的前 32 帧，仅重写后续收势，使用实际 `Ability_GroundSmash_End` 的回撤轨迹；固定长度臂链、扭转和支撑骨连续回到待机。保留攻击总长与原伤害窗口，只修指定片段。
- 躯干与其他支撑肢要承担准备与恢复阶段的重心变化。新增骨不是通用补救；先确认问题来自动作轨迹、关节轴还是蒙皮权重，避免通过根节点平移冒充关节运动。

当前可重建链含 AuthoringV1、PolishV2、RuntimeV3、HeroHandV4、ClawV6、ApeRecoveryV7、RampageReferenceIntake、RampageV8、RampageRecoverV9、ArticulationV12 与 ThreeAttacksV13。V7 的旧攻击曾被否决，但其可编辑模型仍是 V8 作者输入，不整目录归档。已取消的 ChargeV10、否决的首版参考和退役快照按发布清单进 trash。

## 战斗时间与碰撞

- 近战触发范围、导航停止距离、前摇阶段接近目标和实际挥爪走廊一起调。扩大 `MeleeRange` 却让停止距离始终等于 `MeleeRange-35`，可能让怪物停在实际命中走廊外；按目标攻击器官的触达制定停止距离。
- 持续激光使用一个权威攻击时钟，明确定义首跳、间隔、末端是否计入，按跳次去重；每跳重新考虑实际遮挡。打断、死亡和结束时停止伤害。当前案例约 0.65 秒内每 0.13 秒一次，首跳在开始时，共 5 次；不是按帧重复扣血。
- 当前仅横扫、下劈、眼部激光三种攻击；下劈命中附加 2 秒眩晕。激光按用户要求保持待机、眼部 1.5 秒蓄能，不计算提前量。已取消的冲锋和跃砸不作为现用技能模板。

## 根单位与布娃娃

本例实际顶层骨骼是 `RIG_HundredEyedSlag_V1`，带 100 倍单位缩放，下游还有 `root`、`death_pivot`、`pelvis`；不得把 Blender 的通用 Armature 名当成实际导入骨名。V16 曾错误地给不存在的 Armature 添加刚体，用户反馈尸体仍然下陷。容器刚体和交接约束都应从网格参考骨架取得真实根骨。独立 Physics Asset、无碰撞物理根、即时姿态同步与一致速度交接一起处理缩放父链，不能仅看到 `IsSimulatingPhysics=true` 就认定尸体接地。

UE 5.8 `UPhysicsConstraintTemplate::Serialize` 保存的是 `DefaultProfile`；C++ 修改 `DefaultInstance` 的限制后，要调用 `SetDefaultProfile` 或适用的 `UpdateProfileInstance`。本例重新加载的 V16 关节全部为 Free，原拟定的限制没有实际落盘；内置 PhysicsAssetToolset 的限制 setter 也只修改实例。当前 V17 制作与构建状态见工程 `Docs/Monsters/hundred-eyed-slag-ragdoll-ground-v17-20261002.md` 和对应安装回执。静态资产错误与运行接地结果分别报告，本轮未运行死亡测试。

## 身体浓烟与玩家状态

制作、可见性与 Niagara 空间详见 [身体浓烟与可见性](../../ue5-fluid-vfx-workflow/references/body-smoke-and-visibility.md)。玩法规则由玩家实际眼点是否位于浓烟核心决定；看向雾体不代表进入雾体。可用中心到眼点的局部遮挡检查过滤隔墙暴露，但不要用视线穿过雾球来触发雾外目盲。

本例用户最新要求是在烟内刷新效果、离开立即清除，覆盖最初“离开后保留 2 秒”的方案。多云团共用玩家独立后处理组件，状态、后处理权重与死亡／销毁释放保持一致。这里只维护这只怪物的最新合同，不规定其他烟雾弹都必须立即解除。

当前入口为 `Source/FPSGAME/Monsters/HundredEyedSlagMonster.*`、`HundredEyedSlagSpecialAttacks.cpp`、`SlagBlackMist.*`、`SlagMistViewComponent.*`；F6 目录 ID 为 `HundredEyedSlag`。本机资产恢复和本次公开范围见 `Docs/Monsters/hundred-eyed-slag-publication-20261002.md`。
