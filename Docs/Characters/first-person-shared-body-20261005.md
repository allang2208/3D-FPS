# 第一人称复用第三人称身体

用户在低头截图中仍看到悬空裤腰和身体内部，要求保留现有手部，其他部位套用现有第三人称模型。此次替换 NativePoseV3 的“独立腿部姿态＋骨盆后移”显示路线。

## 接入方式

- 现有第一人称手臂、手套、衣袖、武器资产与动作引用保持原路由。
- 本机 `FirstPersonSharedBody` 直接引用 `GetBodyMesh()` 当前第三人称网格，并以第三人称身体为 `LeaderPoseComponent`；世界身体是唯一姿态来源。这个本机组件不创建 AnimInstance，不运行骨盆修正或第二套腿部 IK，也不拥有独立 Tick。
- 本机可见皮肤、上衣躯干、裤子和鞋靴分别装配，但都直接引用世界身体的最终骨骼缓冲区。裤子及靴子仍按 `Jason` 配方选择，包括七分裤和高筒靴的搭配。
- 身体／腿部按世界空间与原比例显示。本机副本不进入场景捕获或光追，不重复向场景投影；原完整第三人称身体继续负责影子、反射和远端显示。
- 死亡、翻越和第三人称模式沿已有本机显示开关。`fps.body.FirstPersonLegs` 保留为兼容开关，现在控制整个本机身体显示。

## 胸腹、袖臂与遮挡

本机皮肤只隐藏基础身体的 `[0,1,2,5,6]` 材质区段，即原袖臂、手、颈部接缝及代理；不再隐藏躯干区段 3。穿衣和裤靴对皮肤的遮挡仍使用第三人称同一装备配方，保留腰臀连续关系。

三件现有上衣（野外长袖、炭灰短袖和锁子甲）直接从当前第三人称网格派生本机显示版本。2026-10-06 已将正式本机引用更新为 `/Game/Characters/ModularOutfit20260924/OwnerShoulderSeam20261006`，在肩口跨界三角面内插入连续切线，保留未跨界面与原生绑定。本机组件隐藏追加的袖臂材质区段，完整胸腹和下摆继续显示。原第三人称上衣与既有各武器第一人称衣袖没有回写。旧整面裁切资产已于 2026-10-06 移入 trash；原回执仅保留为源网格契约元数据。

袖臂归属沿 `upperarm_l/r` 及其后代骨骼权重之和的 0.4 等值线切分，不再用三角形平均值隐藏整块面。该阈值为生产设置，不是已通过实机验收的结论；制作、保存与接入记录见 [肩口尖刺离线处理](sleeve-spikes-20261006.md)。

配方新增 `owner_body_meshes[Jason]` 和 `owner_body_hidden_materials[Jason]`；世界 profile 新增仅本机使用的 `owner_body_hidden_materials`。后续新增上衣需沿此入口生成本机袖臂区段；缺少配方时不自动显示一整套第三人称袖臂。

## 稳定相机与判定

相机继续由现有鼠标、站立／下蹲高度和动作镜头驱动，不绑定头骨旋转。用户反馈第一版仍能看到锁子甲内部；世界姿态会在低头时让胸部前倾，原先固定前移 14＋9 cm 的距离不足。当前身前 V2 保留眼高，基础前移 56 cm，下蹲前移 62 cm；俯视从 20°到 80°平滑增加最多 12 cm 前移，取消低头下沉。用户反馈上一版 36 / 42 cm 仍看到上身内部，因此本轮将基础距离和动态避让距离同步增加 20 cm。

身前距离还读取世界身体当前已求值的 `pelvis / spine_01 / spine_03 / spine_05 / neck_01` 五个骨点，转换到相机父空间，将未受环境碰撞限制的目标眼位放在这些骨点前方至少 40 cm（上一版为 20 cm）。这个余量用于覆盖胸腹衣物的深度，避免上身前倾后重新把视点包进领口。沿既有相机插值平滑位置，不新增骨骼求值、顶点扫描或 Tick；不改变胸腹、裤腿和脚的比例、蒙皮或连续结构。胸前→腹部→大腿→脚的可见构图仍待用户在游戏内确认。

新增偏移在现有 `UpdateCamera` 中计算，不新增 Tick；对前移路径作一次半径 6 cm 的相机通道球扫，受阻时缩短偏移。结果缓存在身体组件，`GetMeleeAimTransform` 复用同一偏移，枪械仍沿当前相机和枪口路径瞄准。原手部相对相机的姿态、FOV 和动作曲线保持原样。

参数位于 `Content/ColdSteelData/player_body.json` 的 `first_person_body`。旧 `first_person_lower_body_mesh` 兼容指针改为当前世界网格；NativePoseV3 和 `UFPSFirstPersonLegsAnimInstance` 不再由本机显示入口加载。旧独立腿模已于 2026-10-06 归档，活动配置不再保留其 profile／别名。

## 文件与制作状态

- C++：`FPSPlayerFirstPersonBody.cpp`、`FPSPlayerBodyComponent.h/.cpp`、`FPSModularOutfitComponent.cpp`、`FPSGAMECharacter.cpp`。
- 生产：`Tools/FirstPersonLegs/save_continuous_owner_shoulders.py`、`save_continuous_owner_shoulders.ps1`。
- 发布：`Tools/FirstPersonLegs/publish_shared_body.py`。
- 常规构建：`Tools/FirstPersonLegs/build_shared_body.ps1`，等待已有构建／commandlet，不关闭编辑器、不打开游戏。
- 回执：`SourceAssets/OwnerBodyShared20261005/saved_shirts.json`、`published.json`；修改前快照在该目录 `Before/`。

三件本机上衣及三档 LOD 已后台构建保存，配置已发布。`FPSGAMEEditor Win64 Development -NoLink` 已完成 28 个编译动作，返回 `Result: Succeeded`；日志为 `build-objects.log` 和 `build-objects-console.txt`。这一步仅编译对象文件，没有更新运行中的 DLL。

用户保存关闭 UE 后，常规 `FPSGAMEEditor Win64 Development` 构建已完成，返回 `Result: Succeeded`、`Target is up to date`；日志为 `build-editor.log` 和 `build-editor-console.txt`。项目 DLL `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已于 2026-10-05 22:11:24 更新，晚于本次源码与对象文件编译。源码、已保存资产和 DLL 均已落盘。

没有重新打开编辑器、启动游戏、运行回归或制作验收截图，实际低头、下蹲及装备搭配效果由用户测试。

## 身前修订交付

本轮修改 `FPSPlayerFirstPersonBody.cpp`、组件参数、`player_body.json` 及后续发布脚本；不重新生成或裁切模型。修改前副本位于 `SourceAssets/OwnerBodyFront20261005/Before`。通过 `Tools/FirstPersonLegs/build_front_body.ps1` 完成常规 Editor 构建，29 个构建动作含 `UnrealEditor-FPSGAME.dll` 链接，返回 `Result: Succeeded`，耗时 89.96 秒；日志位于 `SourceAssets/OwnerBodyFront20261005`。未打开编辑器或运行游戏测试。

## 身前 V2：再向前 20 cm

用户要求继续前移后，同步增加站立、下蹲和胸腹动态余量，保留低头曲线、眼高、手部及模型。配置与默认值、后续发布脚本均已更新。修改前副本及本轮构建日志位于 `SourceAssets/OwnerBodyFrontV2_20261005`；通过 `Tools/FirstPersonLegs/build_front_body_v2.ps1` 完成常规 Editor 构建，36 个动作包含 `UnrealEditor-FPSGAME.dll` 链接，返回 `Result: Succeeded`，耗时 125.20 秒。未打开编辑器或运行游戏测试。

2026-10-06 整理：本文历史备份／旧版本路径按 [归档清单](lower-equipment-archive-20261006.json) 映射到 trash。当前制作入口与恢复顺序见 [整理发布](lower-equipment-publication-20261006.md)。
