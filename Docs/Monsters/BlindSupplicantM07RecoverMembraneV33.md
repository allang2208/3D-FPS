# M-07 V33：收势转移动的支撑与背膜回退

2026-10-03。用户报告攻击 recover 切回移动时短暂陷地；V31 背膜破碎和扭曲比修改前严重，要求先退回，再重新考虑方案。

## 下陷定位与修改

现有状态机在攻击结束后保持末姿，随后通过 `UFatZombieAnimInstance::TransitionTo` 从快照混合到移动片段，并恢复此前移动相位。M07 使用局部骨骼旋转混合；V32 的待机膝面与 V25 的移动膝面方向不同，混合途中腿链变直，骨盆高度的线性混合无法维持脚底支撑。

按用户要求离线读取实际制作源、模拟局部四元数混合并计算原脚部蒙皮，发现两端脚底均约 0 cm，但过渡中间进入地面：慢走最深约 21.64 cm，追击约 22.37 cm。证据为 `SourceAssets/BlindSupplicantM07Meshy20261001/RecoverMembraneV33/recover_ground_diagnosis_v33.json`。这属于源数据复现，不是游戏运行捕获。

`BlindSupplicantAnimInstance.cpp` 中新增 M07 专用过渡节点。来源、目标各求一次脚底高度，完成原有混合后，只上移根骨以补齐混合造成的支撑缺口。来源与目标的实际支撑高度参与插值，首尾修正自然归零；不把骨盆本身归零，不叠加上一帧偏移，不改腿部旋转或攻击片段。

采样从本例脚底最低点提取，共 18 点、4 根脚部骨骼；参考局部坐标在骨骼缓存阶段计算，仅过渡到待机／慢走／追击时计算支撑。正常播放、攻击／施法、死亡和共享击倒过程走原流程。没有新增 Tick、地面射线、运行时 IK 或逐帧分配采样数组，动画源与目标仍各求值一次。

## 背膜回退边界

使用 `MembraneStabilityV31/Before/SK_M07_BodyMotionV18.uasset` 完整恢复 V31 之前的显示网格包，包括原隐藏物理网格、布料映射、活动距离和 Chaos 配置。V31 当前包在 `RecoverMembraneV33/Before` 留存可恢复副本。原蓝图不整包倒退，仅把 V31 改动的额外背膜避让角度由 6° 恢复到此前 18°，保留 V32 攻击和现存移动、施法、死亡引用。

V31 的新代理和脚本属于用户否定版本，不作为成功模板。源记录显示 V31 布料捕获顶点从旧版 24,930 减少到 19,926，增加了布料与纯蒙皮交界；这提示须调查驱动一致性，不能仅以活动幅度更小、代理面数更少推断外观更稳定。

## V33 时的重新设计方向

后续实现见 [V34 完整背膜统一驱动](BlindSupplicantM07CoherentMembraneV34.md)。V34 以原连续蒙皮统一承担显示变形，原骨链的受限阻尼弯曲承担末端二次运动，替代下列重建布料代理的初步设想；没有继续叠加 V31 的碎片捕获。

1. 以回退后的完整组织轮廓、根部和显示面连接为基准，重做每片连续的低密度模拟面；不通过删除狭长面把一片组织进一步分碎。
2. 明确整片、接缝和根部的驱动归属。焊接位置的重复显示顶点需使用一致捕获与一致混合权重；不能在同一连续面中零散切换到另一套驱动。
3. 由现有骨骼维持整体弯曲和随身体运动，末端布料只承担小幅二次摆动。参数从连续性成立的候选开始调整，不继续增大固定点或阻尼掩盖映射问题。
4. 保留原角色轮廓、纹理、肩背连接与既有求解预算。新代理单独制作，正式角色本轮停留在完整回退状态。

## 制作状态

- Game 必要构建完成：`Saved/BuildEditor/m07-FPSGAME-20261003-200006.log`。
- 用户保存并关闭编辑器后，完整旧网格已恢复，Editor 必要构建完成：`Saved/BuildEditor/m07-FPSGAMEEditor-20261003-200235.log`。
- 原蓝图回退设置已由后台 commandlet 保存：`RecoverMembraneV33/ue_recover_membrane_delivery_v33.json`，`saved: true`。网格回退凭据为同目录 `membrane_package_restore_v33.json`；生产日志 `Saved/Logs/M07Import-20261003-200431.log`。
- 源码：`Source/FPSGAME/Monsters/BlindSupplicantAnimInstance.cpp`、`M07FootSupportSamples.h`。
- 工具：`Tools/BlindSupplicantM07/diagnose_recover_ground_v33.py`、`restore_membrane_v33.ps1`、`save_recover_membrane_v33.py`。
- 未运行游戏、截图或渲染；视觉效果由用户体验，未宣称通过验收。
