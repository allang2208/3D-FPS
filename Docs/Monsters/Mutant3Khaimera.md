# 突变体-3：Khaimera 动作第一版（2026-09-23）

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

当前运行引用已转到 [V2 爪形与飞扑接地修订](Mutant3ClawGroundFix.md)。本文保留 V1 的来源、制作和当时构建记录。

本次制作目标为低姿态快速追击、快速爪击、下蹲蓄力接飞扑。保留现有 Meshy 怪物外观、骨架、蒙皮、物理资产与死亡/受击表现，用已取得的 Khaimera 动作制作新的运行时动画。

## 素材获取情况

| 素材 | 本机实际情况 | 本次使用 |
|---|---|---|
| [Paragon Khaimera](https://www.fab.com/listings/e7c665c1-8c13-42f0-9152-0753008853d7) | `D:/FPS3D/VaultCache/ParagonKhaimera/data/Content/ParagonKhaimera` 有完整 UE 内容；正式工程原 `Content/ParagonKhaimera` 只有占位文件 | 使用：在独立后台工程完成重定向，再将派生动画保存到正式工程 |
| [Paragon Rampage](https://www.fab.com/listings/0807cf74-08fd-4a33-8c8d-f33c9439fb1f) | 本机对应 FabLibrary 目录只有 manifest，未找到其动画内容缓存 | 未导入、未使用 |
| [Zombie Animation Pack Standard](https://www.fab.com/listings/82b55c77-c706-4634-839e-29ba827dac8d) | 对应本机下载为 `ue5mannycontrolrig.ma`、metadata 和缩略图 | 未导入、未使用 |

Khaimera 来自 Epic Games 的 Paragon 免费素材。本次沿用该素材的 UE 授权用途，不将其视作开源或 CC0；原始包、派生 FBX、Blend 和动画二进制均留在本机，没有发布。

## 已制作并保存的资产

正式目录：`/Game/Monsters/Mutant3Meshy/KhaimeraV1/Animations`。

| 动画 | 源片段/制作方式 | 时长 |
|---|---|---:|
| `A_Mutant3_FeralIdle` | Idle_NonAdditive | 6.967 s 循环 |
| `A_Mutant3_FeralRun` | Jog_Fwd | 2.000 s 循环 |
| `A_Mutant3_FeralSprint` | TravelMode_Fwd | 1.267 s 循环 |
| `A_Mutant3_ClawA` | Melee_A_Fast | 0.500 s |
| `A_Mutant3_ClawB` | Melee_B_Fast | 0.500 s |
| `A_Mutant3_ClawC` | Melee_C_Fast | 0.500 s |
| `A_Mutant3_PounceWindup` | 静止姿势 → RMB 深蹲姿势 → RMB 起跳姿势 | 0.600 s |
| `A_Mutant3_PounceFlight` | RMB_60fps 0.08–0.60 s，去除重复的垂直位移 | 0.650 s |
| `A_Mutant3_PounceLand` | RMB_60fps 0.60–2.25 s 的落地与起身压缩 | 0.800 s |

18 段源动画通过 UE 原生 IK Rig/IK Retargeter 转到现有 34 骨 Meshy 骨架；最终 9 段在 Blender 以 60 fps 烘焙，保留目标骨长、骨骼静止姿态和原蒙皮，保留骨盆起伏与下蹲压缩。循环末尾作短衔接；地面动作按目标模型修正穿地，空中动作由实际角色飞行提供高度。

原奔跑/攻击包保留在原路径，新版运行时构造默认引用使用新目录。新动画引用正式工程已有的 Meshy Skeleton，无须将整个 Paragon 模型、材质和贴图拷入正式工程。

## 运行时行为

- 追击速度默认 560 cm/s；普通跑和高速跑按脚掌支撑阶段轨迹估计的参考速度 312 / 565.8 cm/s 调整播放速度。高速切换带 420/460 cm/s 滞回，避免阈值附近反复切换。
- 近身默认两段连击；三段爪击轮换使用。每段 0.5 s，命中窗口 0.13–0.25 s，与动作手部向前极值约 0.183 s 对齐。每段最多一次伤害，单次为原 AttackDamage 的 0.8 倍（默认 32），连击后停顿 0.4 s。
- 目标位于 320–750 cm 时可发起扑击；0.6 s 蓄力后重新计算起跳轨迹。起跳后固定方向，默认飞行 0.65 s，冷却 5 s。
- 飞扑要求目的地有可站立地面、胶囊路径无阻挡；通过 CharacterMovement/LaunchCharacter 完成真实移动，命中沿实际路径扫掠并沿用 EnemyMeleeDamage。飞扑最多一次伤害，为原 AttackDamage 的 1.25 倍（默认 50）。
- 实际 Landed 回调进入落地动画；撞墙和落空依赖角色碰撞及重力。玩家移开可躲过，动画本身不拖动玩家。
- Behavior Tree 继续负责决定进攻和追击；突变体自己的动作时钟负责执行阶段。动作期间保持共享 Attack 忙碌态，避免父类攻击逻辑重复扣血。
- 格挡、破韧和死亡取消剩余攻击、挂起的 Launch 及后续命中，恢复原移动设置，沿用既有受击/布娃娃逻辑。
- 现有 F6“怪物生成 → 突变体-3”入口复用同一原生类，无新增怪物 ID。

## 文件与重建

作者目录：`SourceAssets/Mutant3Khaimera20260923`。

- `UEAuthoring/Mutant3Khaimera.uproject`：无游戏模块的后台制作工程。
- `retarget_khaimera.py`：原生 IK 重定向及动画导出。NullRHI 下不导出预览网格。
- `author_feral.py`：保留原 Meshy 蒙皮的动作制作和 FBX 烘焙。
- `Mutant3_Khaimera_Feral.blend`：完整可编辑角色和新动作。
- `final/*.fbx`：九段动画的导入源。
- `import_feral.py`：动画导入和保存；不重新导入模型/材质。
- `animation_contract.json`、`import_delivery.json`、`installed.json`：制作参数、已保存资产与正式工程安装记录。
- `baseline/`：开始修改前的 Mutant3.cpp/.h 与 MonsterCombatComponent.cpp 文件副本，用于比对原始局部内容，不能整体覆盖并行工作。

运行时源码为 `Mutant3.h`、`Mutant3.cpp`、新增 `Mutant3Feral.cpp`。`MonsterCombatComponent.cpp` 仅新增突变体类包含和 CanAttack/TryAttack 分派。

## 交付状态与构建阻挡

九个动画 `.uasset` 已保存并复制到正式 Content；源码引用和战斗执行逻辑已落盘。

2026-09-23 的 `FPSGAMEEditor Win64 Development` 后台构建在 `WeaponBipodDeploymentComponent.cpp` 失败：访问 AFPSGAMECharacter 的 protected/private 成员（C2248），以及第 244 行动态格式串不符合即时常量要求（C7595）。该脚架代码在本次制作期间仍有修改，保留现场，未改动或跨任务协调。本次新增 `Mutant3Feral.cpp` 和相关模块的编译步骤已执行，没有报出突变体代码编译错误，但完整模块尚未成功链接，**本轮不能视为可运行构建已经交付**。日志：`SourceAssets/Mutant3Khaimera20260923/build-editor.log`。

未打开交互式 UE 编辑器、未运行游戏、未截图/渲染、未执行自动测试。脚架构建问题解决并完成工程编译后，由用户通过现有 F6 入口体验此第一版，动作观感、地形接触与战斗平衡尚未经过游戏内验收。
