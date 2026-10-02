# 空装备栏切换与空手步态 · 2026-10-01

用户要求两套装备栏可在有装备和完全空手之间切换；同时将现有空手待机双拳收回，并参考法杖空闲左臂的走跑摆动制作右臂镜像，同步玩家步频。

## 装备状态

`UColdSteelStatusModel::CycleWeapon()` 在主手槽 6 与 9 之间切换，无论目标栏是否持有武器。仍通过 `CommitState()` 原有事务保存和应用档案。`RemoveRetiredWeapons()` 只在确实移除了当前退役武器时执行装备回退，避免保存正常空栏选择时重新跳到有武器的栏。

空手视模仍要求激活组主副手槽 6/8 或 9/11 均空，且未持有生产工具。角色与武器已有档案发布流程负责收起离场武器；空手组件按 `OnChanged` 缓存装备状态。保留已有切枪优先级和存档结构。

## 动作接入

继续使用 V7 原生 M4 手臂与闭拳姿态，隐藏枪体材质区；服饰沿用原有姿态 leader。作者源在 `SourceAssets/UnarmedLocomotion20261001/`，运行表编入 C++，无需新增或导入 UE AnimSequence。

新呼气腕点（相机厘米）为左 `(29,-15,-18)`、右 `(30,16,-19)`，相比旧版左 `(34,-15,-18)`、右 `(35,16,-19)` 各收回 5 cm。肩锚点维持左 `(-7,-21,-26)`、右 `(-7,21,-26)`，按原生骨长重新解算肩肘支撑；呼吸周期仍为 4.2 秒。

走跑相位读取 `UFPSFootstepAudioComponent::GetStridePhaseRadians()`，该相位也驱动现有相机步频与法杖动作。空手组件依赖角色、CharacterMovement 与脚步组件先完成 tick；走跑切换只混合幅度，停步/空中淡出地面动作，保留最后步频相位。蹲伏减小摆幅；滑铲、闪避关闭地面步态，攀爬维持原有隐藏逻辑。

两侧完整局部骨链先与呼吸待机混合，再一次求 FK 与 CameraToMesh。现有左手施法和药水覆盖层随后调用；服装清隙及可见性合同沿用已有实现。右臂镜像按原生骨架语义制作，手指及拇指保留闭拳。

新表 `UnarmedAuthoredLocomotion20261001.h` 保存 54 骨、2 个呼吸控制姿态及 Walk/Run 两组各 32 个步态采样，右臂在作者源中已偏移半个周期，运行时两臂读取相同相位。下臂同时保存屈伸与轴向滚转标量；运行按同一权重组合 Idle、Walk、Run 标量，再以 `Q(ElbowHinge,Flex)*LowerRestRotation*Q(ForearmAxis,Roll)` 重建局部旋转，其他骨骼使用局部位置与归一化最短路径四元数混合。

姿态缓存按网格及作者 revision 更新，骨名只在重建缓存时解析；每帧只采样缓存中的固定骨集，不复制装备档案或同步读取资源。空手动画幅度按实际速度与当前 `CharacterMovement.MaxWalkSpeed` 归一化，移入/移出按 9/s 指数跟随，入跑 5.5/s、退跑 10/s，蹲伏系数 0.6。

## 交付范围

旧空手运行文件与装备切换源码分别备份于作者目录的 `BeforeRuntimeIntegration/`、`BeforeEquipmentSwitch/`。作者姿态、实际 Blender 源保存及常规 Editor/Game 构建结果以同目录 `integration-completion.json` 为准。

按用户规则后台制作与构建；未运行游戏、测试、渲染、截图或视觉验收，未为本任务启动 UE 编辑器。动作观感由用户确认。

实际交付：可编辑 `Unarmed_V7_Locomotion_20261001.blend` 已后台保存，含三个 120 Hz take：Idle（505 帧）、Walk（121 帧）、Run（85 帧）。Game 常规构建 13 个动作成功，写入 `Binaries/Win64/FPSGAME.exe`；待原有编辑器退出后，Editor 常规构建 23 个动作成功，重新链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。对应日志在 `Saved/UnarmedLocomotion20261001/`。下次正常启动可直接使用，不依赖 Live Coding 补丁；本任务未关闭、重启或启动编辑器。
