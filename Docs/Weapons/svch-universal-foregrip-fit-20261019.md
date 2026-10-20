# SVCH 通用握把与左手匹配

用户报告几乎全部通用握把都没有匹配左手。本轮范围是 SVCH 的五种通用下挂握把，保留认可的 V9、现有原装动作，以及已保存的弹匣接口、左手拉栓和换弹臂根避让。

## 原因与接入

此前 SVCH 只为 `base` 加载专用姿态配置。四种握把族会查找不存在的 `AnimationProfiles20261001/ue_svch/DA_*`，随后落入 M4 的旧动作路径；可见握把也落入 M4 默认安装位置。换弹又强制使用原装配置，无法自然回握附件。

现在 `SVCHForegripAssets.h` 为 SVCH 提供统一安装变换和专用配置路径，`M4HandstopVisual.cpp` 明确处理五个目录 ID，`SVDGripProfiles.cpp` 加载各族。换弹动作使用当前握把族，缺少时仍回落原装配置。

| 目录 ID | 配置族 | 复用的握把外形 |
| --- | --- | --- |
| `angled_foregrip` | `angled` | 共振握把 |
| `vertical_foregrip` | `vertical` | 垂直握把 |
| `tactical_vertical_foregrip` | `vertical` | 战术垂直握把，独立外形与属性 |
| `canted_foregrip` | `canted` | 45° 侧倾握把 |
| `prism_handstop` | `prism` | 棱镜阻手器 |

每族覆盖共享 SVD 的 12 个源动作：idle、aim、fire、aim_fire、equip、reload、reload_empty、inspect、quick_melee、sprint_enter、sprint_loop、sprint_exit。使用现有差量消费路径，不增加运行时逐帧 IK 或资源加载。

## 制作依据

- 输入原装配置 SHA-256：`09c209b529f487c1e5ec330da16c1eb71b1603b67e404389ff75e2ab34f47e7e`，包含上一轮臂根避让。
- V9 输入：历史 BarePalmV7/SVD 路径中的当前认可资产，SHA-256 `db865373cd3574a8a3382d5b76b1a1ea6452bae25e8305d3c5df063d2d479d1b`。不写入网格、参考绑定、权重或矫正形状。
- 读取实际新枪体底面，物理枪体坐标的局部底面约为 3.633 cm；把原握把 1.47 cm 的顶面放到约 3.65 cm，形成约 0.17 mm 的接合量。沿用枪体实际上方向的 5° 轴向修正，不再使用共享骨架的旧 M4 准星作为下挂定位依据。
- 复用 SVD 对应四族的成组手指旋转与手掌相对握把关系，再用 SVCH 的原生骨段长度解算肩肘。手指局部位移和骨骼缩放沿用输入；前臂扭转采用 V9 的 100%／50% 分配。
- 共振握把通过调整肘部和肩部来向控制腕部弯折，握点与掌向保持在握把上。松开／回握时，支撑位移和手指姿态一起逐渐过渡。
- 普通换弹只在源帧 0–24 松开握把、255–304 回握；空仓在 0–24 松开、360–416 回握。其余取匣、插匣和拉栓接触段保留原装配置。右手、枪根和机构轨道保留。
- 检视按实际离开原握点的距离退让；冲刺松手循环保留原动作，只适配进入与退出的握把接触段。

## 交付

制作源：`SourceAssets/SVCHReplacement20261018/ForegripFit20261019/`，包含当前输入、挂点配方、四族 JSON、作者脚本和可编辑 Blender 动作。

四份 `SVCH_Foregrip_*_ReloadGrip_Editable.blend` 已导出保存，每份包含 12 条枪体动作与 12 条原生 V9 动作（文件名沿用源导出器的 ReloadGrip 后缀）。`FPSGAMEEditor Win64 Development` 后台构建成功，完成时间为 2026-10-19 17:36:23 +08:00。

运行资产：`/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_{angled,vertical,canted,prism}`。四份配置已于 2026-10-19 17:54:01 +08:00 经后台 commandlet 保存，每份 12 条动作；见 `install_receipt.json`。原装配置、V9 和共享源序列未写入。原生构建见 `build_receipt.json`。

本轮进行用户要求的接入排查和制作计算，没有启动游戏、PIE、截图或渲染。资产保存、编译完成与实际握持观感分开记录，游戏效果由用户测试。
