# M08 口部避让与攻击动作 V09（2026-10-05）

用户反馈空气炮发射时嘴部陷入地面，要求继续加快飞扑，并改善整体动画僵硬。本轮保留原模型、权重和背环出口的实际蒙皮定位。

## 制作内容

- 空气炮源动作的骨盆主下沉量由 11.5 cm 改为 5.5 cm，并减轻后坐下沉、修正颈部方向；蓄力的后半段由完全保持改为小幅持续加压。
- 从原模型下唇／牙齿的下部实体表面提取最多 12 个支撑样本，保留原来的骨骼影响。离线制作时通过胸部和颈部共同抬升，使这些样本保留 3.5 cm 的支撑平面间隙；此步骤属于动作制作，不是运行测试。
- 原生动画节点在空气炮支撑阶段使用三处口部地表采样（复用 30 Hz 接地调度），在四肢 IK 前按口部样本计算 3 cm 的表面间隙修正。按实际支撑面方向工作，并将修正分配给胸部和颈部，避免只把头骨向上拉。额外抬升上限 35 cm；复杂地形效果仍需用户体验。
- 飞扑速度系数由 2 改为 3，即比 V07 再快 50%；飞行时长为 `clamp(distance_cm / 760 + 0.16, 0.44, 0.95) / 3`，约 0.147–0.317 s。沿用既有源时间映射、预测与命中窗口，蓄力／恢复没有整体快放。
- 飞扑重制胸部伸展、腰盆滞后、前后肢错时收放和落地缓冲；路径俯仰分散到骨盆／脊柱／胸部，颈部作小幅稳定补偿。背环两侧共用连续变形场。
- 在 V08 头部与躯干联动基础上，将移动抬脚改为较早提起、较缓放下，拉开后足延迟与回收时长，步幅高度随速度变化。原世界空间接触目标继续保留。

空气炮发射源时间仍为 0.92 s，保持 48 基础物理伤害、3 s 眩晕和 20 s 冷却；慢行／追击／爬墙速度继续为 150／315／270 cm/s。

## 文件与安装

- 作者入口：`Tools/LurkerM08/author_motion_v09.py`，复用 V05／V06 原作者函数。
- 可编辑源：`M08_Attacks_MotionV09.blend`；中间空气炮制作源：`M08_AirCannon_MotionV09.blend`。
- 已导出：`Animations/A_M08_AttackAirCannon_MotionV09.fbx` 和 `Animations/A_M08_AttackPounce_MotionV09.fbx`，120 fps。
- 口部绑定制作数据：`mouth_binding.json`，UE 导入时按实际骨架参考姿态换算，避免猜测 FBX 坐标轴。
- 原生变更：`LurkerM08ContactNode.h/.cpp`、`LurkerM08Monster.h`。修改前这三份源码保存在本目录 `PreviousSource`。
- 构建入口：`Tools/LurkerM08/Build-MotionV09.ps1`。
- 资产安装入口：`Tools/LurkerM08/Import-MotionV09.ps1` / `install_motion_v09.py`；完整安装链已追加 V09。
- 目标资产：`/Game/Monsters/LurkerM08/MotionV09/Animations`；原 `DA_M08_AnimationSet` 与 `BP_LurkerM08` 继续作为唯一运行入口。

## 当前交付状态

2026-10-05 继续接入时，已有 UE 编辑器已关闭。常规 `FPSGAMEEditor` 构建成功，退出码 0，新 DLL 已落盘；本次同时包含 V08 的移动全身细调。后台动画导入和蓝图保存也已完成，commandlet 退出码 0，`installation.json` 状态为 `motion_v09_saved_and_bound`。

实际保存了两段 V09 动画、原 `DA_M08_AnimationSet` 和 `BP_LurkerM08`。蓝图绑定 12 个真实口部蒙皮支撑样本，飞扑速度系数保存为 3；其余动作继续沿用原引用。构建日志为 `build_01.log` / `build_console_01.log`，安装日志为 `import_01.log`，无需再手动运行导入脚本。

未主动启动编辑器、游戏、测试、截图或验收渲染；本轮动作仍需用户测试，不能以离线制作或构建状态代替实机效果。

## 2026-10-05 归档说明

本目录中旧 Before、PreviousSource、before_references.json、Blender 上次保存和已替代定位文件（如存在）已移到 `trash/lurker-m08-retired-20261005/`。按工程 `Docs/Publication/LurkerM08_20261005/archive-manifest.json` 查询原路径及恢复目标；历史段落的旧位置不表示备份仍在本目录。仍供当前制作链读取的正式源继续保留。
