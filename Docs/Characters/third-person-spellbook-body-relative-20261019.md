# 第三人称副手魔法书：身体相对持握

用户反馈左手与手臂跟随镜头移动导致扭曲，要求改成相对位置，并参考其他主手装备的整臂姿态。

## 修改

| 状态 | 处理 |
| --- | --- |
| 持书、走跑、蹲姿 | 复用现有 `Staff.BookCarry` 原生整臂姿态；同主手法杖通过 `AnchorStaffArm` 保持身体方向和肩部位置，不再混回已受瞄准或通用 IK 影响的腕臂 |
| 主手切换 | 由实际副手魔法书装备和显示状态启用持书层，移除仅限主手法杖的条件 |
| 魔法书推击 | 继续使用 `Staff.BookPush` 原生肩肘动作与原有时钟，起手和收势接同一身体相对持书姿态 |
| 专注开书、阅读、收书及受击回收 | 第一人称只提供相对其原生持书起点的腕部位移与旋转；第三人称在自身原生持书臂上重建动作，镜头朝向和眼部位移不再进入目标 |
| 前臂与手腕 | 专注动作复用主手法杖的原生肘平面、可达距离、前臂旋转及腕部限角处理；同步重建左臂蒙皮辅助骨 |
| 悬浮书 | 以映射后的左手为坐标基准传递书本姿态，挂接最终第三人称 `hand_l`；保留封面、书页、开合及接书时序 |
| 收起与其他动作 | 沿用装备显示、翻越、死亡、消耗品和其他左手动作的优先级 |

`USpellbookArmsMeshComponent::GetCarryHandInCamera` 从已有缓存持书关键帧计算基准，不改第一人称姿态。`CaptureMotion` 在采样端消除镜头变换，`BlendBookCarry` 在第三人称动画线程按本体姿态应用相对动作。专注同时施法继续保留 `StaffCast` 通道；普通专注使用 `SpellbookFocus`，现有表现快照与序列号继续承载更新，无新增网络字段或存档字段。

复用现有动画包、手型和挂点，无需重导入资产。修改前工作区文件副本：`Saved/TaskBackups/ThirdPersonBookRelative20261019-164343/`；保留同文件的并行修改。

## 交付状态

源码已落盘，已执行一次常规 `FPSGAMEEditor Win64 Development` 构建，日志为 `Saved/ThirdPersonBookRelative20261019/build-editor.log`。身体动画、书本表现和 Spellbook 组件参与编译。采样文件中的局部 `Cast` 变量遮蔽全局模板调用，已改为 `::Cast`。

完整构建失败，尚未链接更新 Editor DLL。当前体素建造代码还存在以下阻塞，本任务未修改这些文件：

- `VoxelBuildGeometry.cpp:68`：lambda 返回值推导混合 `int` 与 `INDEX_NONE` 的枚举类型。
- `VoxelBuildGeometry.cpp:71`：`VoxelSurface::AppendCutCells` 接口缺失。
- `VoxelBuildComponent.cpp:914`：局部 `End` 遮蔽先前声明。

修正本次 `Cast` 调用后准备增量构建时，工程再次被 `BareSkinV9Rollout_20261017/run_installs.py` 的资产导入 commandlet 占用，启动保护未提交新构建。因而本轮没有成功的完整构建回执，当前 Editor 不应视为已经应用修复。后续需要在占用释放及体素编译错误解决后完成常规构建。

本任务未启动编辑器、游戏、PIE、截图、渲染或自动测试；姿态与接触观感交由用户实机测试。
