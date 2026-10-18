# 大份烤羊排双手自然抓握修正（2026-10-16）

后续状态：用户继续指出双手进食拇指扭曲，本版不视为视觉验收通过。最新修订见 [拇指扭转修复](large-lamb-thumb-untwist-20261016.md)。



目标是 `roasted_large_lamb`，不是单手 `roasted_lamb_ribs`。本次保留其他并行改动，没有运行游戏或 PIE，没有关闭已有编辑器，没有改存档或提交 Git。



## 原因与修改



运行链为 `FPSPotionUseComponent` → `PotionUseMotion` → 左右 `PotionArmPose`；双手使用 DefaultGame.ini 指定的 Traversal V7 裸臂。旧掌向沿用了握瓶基底，左右四指共用镜像参数，部分相邻指节侧展相差约20度。离线还原中，接近阶段前臂轴与掌纵轴夹角约70度，咬食阶段约111度；此前的拇指检查没有覆盖完整手掌、掌骨混合蒙皮和四指。



增加可选 `palm_rotation`、`right_palm_rotation` 与 `right_digits`，只由大份羊排提供。手指各节使用连续屈曲平面，左右独立贴合。物品变换使用同一个掌向基底的逆变换，保持原模型、轨迹及咬食点；右手仍跟随左手实际求解后的物品变换。双手抓握保持到食物隐藏后再松开。



运行数据位于 `Content/ColdSteelData/potion_use_motion.json`，固定制作配方为 `SourceAssets/FoodGrip20261003/large_lamb_natural_grasp.json`，原制作入口和 `LargeLamb20261014/grip_profile.json` 已同步。发布后已核对所有其他消耗品分支不变、制作配方重放与保存数据一致。



## 离线证据



使用原生 Traversal 骨架、当前 V7 完整混合蒙皮及原羊排三角表面，覆盖拿起、展示、接近、咬食、收回等9个阶段，每只手每阶段5976个相关皮肤顶点；另采样306个连续姿态。报告见 `SourceAssets/LambNaturalGrip20261016/Authoring/surface_and_motion_review.json`。



2.75秒的左右腕部轴线夹角约6.5/11.2度，4.65秒约38.5/44.2度。连续采样没有位置突跳，约60Hz步长的最大腕点位移1.12厘米，旋转变化1.01度；指骨长度误差仅数值精度量级。该轴线角是几何检查指标，不是临床关节角度。



完整表面最大嵌入从左4.31/右3.53毫米降至左1.67/右0.53毫米，仍存在局部接触嵌入，不能称为零穿模。拇指与无名指的接触面形成反向支撑；不强迫每根指尖都贴住不规则骨排。中指、小指部分指腹仍留有自然握持间隙，最终造型需要用户体验确认。



`Previews/final_present_front.png`、`final_present_side.png` 和 `final_bite_front.png`、`final_bite_side.png` 均从保存后的运行 JSON 生成；同目录保留离线 Blend 场景和修复前对照。它们是离线诊断渲染，不是游戏截图，不证明实时动画图、装备混合或第三人称表现已经验收。



## 编译与生效



原生修改先落盘，再执行 `20261016-153510` 的 Game 目标构建，150.01秒，`Result: Succeeded`。最终 JSON 参数在这次构建之后保存；之后没有修改本次 C++，JSON 在组件初始化时读取，不需因纯参数再次编译。时间、散列和构建回执以同目录 `delivery.json` 为准。



2026-10-16 继续核验时，确认其他批次已完成包含本修复的 `FPSGAMEEditor Win64 Development` 常规构建，故未重复编译。最终复用 `Saved/BuildEditor/build-20261016-180543.log`：10:05:43–10:05:59 UTC，15.51秒，`Result: Succeeded`，完成普通 `UnrealEditor-FPSGAME.dll` 链接。UBT 的结构化结果 `Succeeded` 对应退出码0；本任务没有重新启动该历史进程或独立捕获它的 shell 退出码。DLL 修改时间为 `2026-10-16T10:05:58.379253+00:00`，SHA-256 为 `51e4b0ec4431f0d983d52ba26bf8eb07f1d9e0f30aca58edc68fec67a221baa0`。三份 Editor 目标文件内嵌的源码校验值及 `PotionUseMotion.h` 校验值与交付 SHA-256 完全一致，且均列入成功 DLL 的链接输入。5个源码/制作脚本、3份动作数据保持原交付散列。证据保存在 `SourceAssets/LambNaturalGrip20261016/EditorVerification-20261016-102758Z`。本任务未关闭其他进程、未启动编辑器/游戏/PIE；当前会话实际加载、游戏视觉与联机表现未验收。
