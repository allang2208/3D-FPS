# SVCH 换弹左臂根部避让

用户继续报告换弹时裸臂根部进入镜头，要求保留认可的 V9 手模，避免扭曲和错误拉伸。本轮只修改 SVCH 普通／空仓换弹的左臂支撑层。

## 定位依据

活动配置仍为 `/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip`，输入 SHA-256 为 `d26541acd94b6ab409914d2216cc5a3c722df9fcb4cb788313fa98990745b57e`，包含已完成的弹匣接口和左手拉栓修复。共享 SVD 源动作没有变化。

当前认可裸臂是历史 V7 路径中的 V9：`/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7`，本轮最终制作输入 SHA-256 为 `db865373cd3574a8a3382d5b76b1a1ea6452bae25e8305d3c5df063d2d479d1b`。制作期间检测到 V9 更新，因此重新读取当前资产并在同一后台互斥批次中制作、保存；首次读取资料保留在 `PreviousInput/`，未覆盖 V9。

作者几何计算使用当前 V9 蒙皮、当前姿态层、已有换弹相机记录以及代码中的 75° 垂直视野。旧避让主要使臂根越过 16:9 的左侧画框；采用保持垂直视野的宽窗口时，退匣、插匣、左手拉栓和部分回位帧仍会露出近端轮廓。这是离线定位依据，不是本轮实机截图或验收。

## 修订

- 保留手掌完整世界变换、手指局部曲线、右臂、枪根、弹匣和枪机轨道，以及原动作时长、机械时钟和回位交接。
- 肩根与锁骨一起向相机后方作小幅刚性平移，再用原骨段长度重解肩肘支撑。肘位置选择现有轨迹附近的可达点，维持已有屈肘平面关系。
- 仅将新增的前臂轴向补偿按原生 V9 的 100%／50% 分配给近腕／中段扭转辅助骨。掌心不随肩部避让翻转。
- 整段共同求解连续位移曲线，避免逐帧独立求值造成跳肩。源首尾帧保留；已经清出画框的近伸直回位姿态优先保留，不为额外留白把肘部拉直。
- 作者目标覆盖 21:9 画框并保留一定边缘余量。普通换弹肩根后移峰值约 4.32 cm，空仓约 5.26 cm；骨长由固定长度解算约束，骨骼缩放沿用输入值。
- 左手仍完成换弹后的左侧拉栓，掌心与机械部件的相对接触不变。手掌局部补偿轨道随父骨变化重新表达，不能将局部数值变化误认为重新创作手部动作。

没有写入 V9 网格、权重、参考绑定、材质或矫正形状；没有重导共享动画、枪体、弹匣和瞄具。本次无需 C++ 构建。

## 文件和交付状态

作者目录：`SourceAssets/SVCHReplacement20261018/RootClearance20261019`。

- `Inputs/`：本轮读取的实际资产、源姿态和配置。
- `clearance_context.py`、`shoulder_support.py`：相机和当前裸臂轮廓、固定骨长的肩肘配准。
- `author_root_clearance.py`、`profile_root_clearance.json`：普通／空仓换弹的新支撑轨道。
- `authoring_recipe.json` 与两个 `*_support_curve.json`：作者曲线与约束记录。
- `export_editable.py`、`SVCH_RootClearance_ReloadGrip_Editable.blend`：可编辑制作源；显示材质不替代 UE 材质。
- `install_profile.py`：写入前保护当前版本与未保存工作，仅保存活动 SVCH 专用姿态配置。
- 备份位于工程外 `D:/FPS3D/FPSGAME_Backups/SVCHRootClearance20261019`。

已通过后台 commandlet 保存活动 SVCH 配置，资产 SHA-256 为 `09c209b529f487c1e5ec330da16c1eb71b1603b67e404389ff75e2ab34f47e7e`。`install_receipt.json` 记录本次保存结果；只写入普通／空仓换弹的左臂支撑层，没有写入 V9 或共享源动画。

本轮没有启动游戏、拍摄新截图、渲染预览或追加回归测试。实际视觉效果由用户测试。
