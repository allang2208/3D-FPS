# 玩家观察、近战与穿戴修复整理发布

范围为本对话的面板装备待机、F6 固定观察镜头、第三人称剑术修订、法杖世界尾饰补接，以及七分裤腰口和背包背带修复。法杖水晶、杖冠、符文、握柄配方此前已在 `7f185098` 发布，见 [法杖与符文发布记录](../StaffAndRunes20261010/README.md)，本轮不重复恢复旧候选。

## 当前实现与状态

| 部分 | 当前实现 | 交付边界 |
| --- | --- | --- |
| 面板装备待机 | 剑、弓、采集工具分开展示条件和输入条件；菜单取消攻击但保留持握，暂停菜单遵守世界暂停 | 原有后台构建记录为 `build-20261009-225250.log`，未游戏回归 |
| F6 | 基本调参新增“第三人称固定视角”；捕获碰撞处理后的渲染位置／方向／FOV；开启自动进入第三人称，关闭或切回第一人称释放 | `build-20261010-205541.log` 构建成功；未运行镜头验收 |
| 普通／冲刺竖劈 | `KwangSwordLeftContact20261010`，左手靠护手、右手靠柄尾，左手整手向柄尾收回 2.4 cm，保留刀身补偿 | 两段已保存并接入；后续实机未验收 |
| 上挑／通用旋风 | `KwangSwordRecovery20261010`，保留完整肩肘腕和辅助骨；不恢复 V3 肘极优化 | 旧恢复记录仅证明源／压缩数据，不代表所有动作合格 |
| 唐刀旋风 | `TangDaoWhirlwind20261010` 三段，独立刃面转角；最终子步后同步角色朝向 | 最后用户要求的 `turnDegrees=-720` 已在主线配置，保持不变；未游戏验收 |
| 法杖尾饰 | 世界武器复用既有 `TailDynamics` / `USwordTasselMeshComponent` | 不新建物理方案；保留原生视模尾饰实现 |
| 七分裤腰口 | 普通与高筒靴版各补 1,096 个原生皮肤面，保留三档 LOD，生成配方同步 | 两种资产均已保存，未视觉验收 |
| 背包 | 肩垫／窄回带重排，去掉手臂／腿部误权重与多余悬带，保留包体 UV/PBR | 当前骨骼包已保存，25,218 顶点／39,328 三角形／1 档 LOD；未视觉验收 |

共享代码按具体修改段发布。步枪姿态、死亡镜头、滑铲／蹲姿、热成像、属性面板等并行修改留在原工作树，未夹带；本轮没有覆写或回退它们。`WeaponAnimationAuthoring` 的压缩收尾、剑术原生图和 `SwordGripRoll/SwordGripSlide` 消费定义已随前序提交进入主线，本轮补齐必要的采样／挂接和实际配置引用。

## 本机资产恢复

公开内容为原创 C++、配方、说明、诊断工具与技能经验，不包含模型、FBX/Blend、图标/PBR、骨架、密集顶点／权重／动画采样、UE 包、DLL、日志或 trash。Jason、Epic/Kwang 供体、原生武器手部、背包及衣物沿既有本机授权使用；未核准其原始资产再分发，不因已购或免费而公开。裤鞋来源和基础恢复顺序沿 [裤鞋整理记录](../../Characters/lower-equipment-publication-20261006.md)；仅 clone 源码不能恢复完整游戏。

1. 竖劈当前可从本机 `ThirdPersonSwordLeftContact20261010/candidate-actions.json` 经 `save_sword_left_contact20261010.py` 保存。完整制作链为 `ThirdPersonSwordKwang20261006/adapted-actions.json` → `ThirdPersonMeleeRegression20261010/restore_accepted_arms.py` → `ThirdPersonDashArm20261010/repair_forearm.py` → `ThirdPersonSwordHandClearance20261010/author_support_thumb.py` → `ThirdPersonSwordGripPair20261010/author_grip_pair.py` → `ThirdPersonSwordArmSwap20261010/author_arm_swap.py` → `ThirdPersonSwordLeftContact20261010/author_left_contact.py`。
2. 上述链还需要本机 Kwang `retargeted-poses.json`、`ThirdPersonSwordActions20261006/authoring-input.json`、Jason 网格及 `ThirdPersonDashArm20261010/graph-after.json`。`ThirdPersonSwordGrip20261007/refine_kwang_grip.py` 的函数初始化段被后续脚本引用，故保留；其完整 V3 优化器已经被否定，不应运行它覆盖当前动作。
3. 通用恢复段由 `save_melee_recovery20261010.py` 保存；唐刀在此基础上用 `author_edge_roll.py` 生成稀疏曲线，再用 `save_tang_dao_whirlwind20261010.py` 保存。`edge-roll.json` 中 +720 是最初刃面适配的描述，运行转向以当前 `skills.json` 的 -720 为准。原本的 `publish_*` 是有旧路径／散列前置条件的阶段切换器，不应无条件重新执行整串发布器覆盖当前引用。
4. 七分裤保留 `SourceAssets/SmokeGreyCapri20261004/native_waist.json` 和两个最终穿戴源。`prepare_runtime.py` 自动附加腰部补片；`save_waist_repair.ps1/.py` 从当前身体的被遮挡区域生成并保存两种变体。最终回执为 `PlayerWaistSeam20261012/saved.json` 与 `save-bridge-02.txt`，失败的早期 API 尝试不代表最终状态。
5. 背包保留 `BackpackStraps20261012/backpack_input.json`、`native_islands.npz`、`backpack_repaired.json`，以及 `JasonEquipmentRepair20261003/backpack.json`、`backpack_fitted.json`、Jason 和三件上衣的包络数据。`native_islands.npz` 是本次保留的离线岛标签输入，不在公开包内。`author_backpack_straps20261012.py` 使用既有 `refit_jason_backpack_straps.py` 的 `make_envelope`，不能归档该工具或它的输入。`save_backpack_straps20261012.ps1/.py` 保存到现有 `SK_Jason_Backpack`；旧保存入口优先选择新修复源。

`read_*`、`capture_*`、比较和渲染工具作为用户明确要求排查时的入口保留，不自动运行。保存操作需停止 PIE；已有编辑器沿当前桥互斥，关闭编辑器时可后台 commandlet，不为整理发布启动应用。

## 废案归档与技能沉淀

30 个旧覆盖备份、空／失败桥接记录和重复失败日志，共 129,830,048 字节，移入 `trash/player-presentation-retired-20261012/`。逐文件原路径、目标、大小、SHA-256、归档原因和保留替代物见 [归档清单](archive-manifest.json)；所有文件移动后读回散列一致。成功保存回执、用户否定版本的必要制作输入及现用 UE 包保留。没有因为版本日期早就搬走完整动画目录。

个人维护源和本次工程交付同步了以下经验，既有本机技能入口重组不夹带入本提交：

- [双手接触与旋风方向](../../../skills/ue5-fps-arms-animation/references/third-person-sword-contact.md)：完整手部覆盖、左右臂参考轴、刀身反补偿、旋风四种方向及异步压缩。
- [共用身体／腰部／背带](../../../skills/ue5-fps-arms-animation/references/shared-owner-body-and-lower-equipment.md)：遮挡缺面与贴图问题分开，变体覆盖、保持原生属性、背带功能分区及骨权重归属。
- [F6 固定第三人称](../../../skills/ue5-cpp-gameplay/references/fixed-third-person-observation.md)：只冻结渲染观察视角，保留输入和玩法射线。

本轮只进行用户要求的仓库／推送检查及归档读回，没有重新编译或运行 UE、游戏、截图、渲染或视觉验收。上述历史构建和资产保存均有各自边界，公共提交切片没有独立重新构建，实际游戏表现交由用户测试。
