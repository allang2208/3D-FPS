# 炼药台金色细线：近裁剪面蒙皮细条修复（2026-10-18）

> **2026-10-19 撤回：本修复已被证伪为空操作。** 部署手模 `BareSkinV9M4_20261017/Work/install_payload.json` 的蒙皮权重只覆盖 24 根手臂/手骨，**没有任何脊柱/颈/头/腿骨权重**；折叠所有非 `ArmBones` 骨骼影响 0 个顶点，画面必然不变——与用户实测"线仍在"一致。此外 `Work/mesh.npz` 扫描显示网格最长边仅 1.71 cm、零退化面，跨屏细条在几何上也不可能。本修复可保留作无害防御，但**不是这条线的原因**。见 [第三轮复排](alchemy-gold-line-third-audit-20261019.md)。

## 症状

工作视角下（倒配料、倒药水、蘸取全程），画面里出现一条浅金色、约 1–2px 的细线：从画面上缘进入、向下略向右斜穿坩埚与幽灵瓶区域直到下缘；放大截图可见为两条近平行的边，上端在画外收窄交汇；被锅沿与半透明幽灵瓶正确遮挡（真实深度测试几何）。RedRoot 瓶盖提取管修复上线后线仍在（09:57 编辑器已加载修复版 DLL），说明瓶盖不是唯一线源。

## 定位结论（静态分析）

**元凶：工作视角手臂网格 `SK_M4_BareArmsV7` 的完整全身骨架 + 未驱动体骨绑定在镜头近裁剪面附近。**

证据链：

1. `AAlchemyWorldView::Tick`（`Source/FPSGAME/Building/AlchemyWorldView.cpp`）：
   `Pose[I]=Reference[I]*Torso`，`Torso = Eye+(0,-13,-35)` —— 所有**未驱动骨骼**（手臂链之外的一切）以绑定姿态刚性贴在镜头后 13cm、下 35cm 的躯干点上。
2. 直接扫描 `SK_M4_BareArmsV7.uasset`：骨架含 `pelvis`/`spine_01`–`spine_03`/`neck_01`/`head`/`thigh_*`/`ball_*` 等完整 UE 体骨，并非仅手臂骨骼。
3. 该骨架绑定姿态下脊柱/颈/头沿 +Z 向上，置于躯干点后落在镜头上方略后——正好在近裁剪面附近、投影出画面上缘之外。
4. 蒙皮三角面若一端权重在体骨（停在镜头旁/后）、一端权重在被 IK 拉到台面工具的手臂骨上（`Solve` 把 clavicle/upperarm/lowerarm/hand 直接写到位），就被近裁剪面裁成贯穿屏幕的细长三角条带——**两条近平行边正是条带两侧的剪影边，顶端交汇点＝贴近镜头的顶点**。
5. 全部吻合观察：浅金色＝暖光下肤色；被锅沿遮挡＝真实深度几何；倒料/蘸取全程出现＝手臂始终摆姿；约 700px 全屏跨度只有贴镜头几何能解释（台面瓶盖提取管 10.8cm 在 60cm 外最多投影约百级像素）。
6. 同源佐证：Backlog 记录这批 FBX 来源手模"整条手臂布满细长碎面"的已知缺陷；本 mesh 混权过渡区的三角面即同类细长三角。

排除复核（本轮全部重读源码确认）：流束 8 段样条网格、`Stream` 隐藏件、蒸汽车牌面向相机、`Carry/Smooth` 有界、`ToolGrip/BottleGrip` 偏移有界、`DoseFill/LadleFill` 缩放有界、瓶盖隐藏逻辑、手册叶/书签、温度文本、幽灵瓶后处理（不受遮挡，排除）——均有界/正确。`CommitStationPose` 的父局部换算、`Solve` 的 IK 数值（D 钳制、sqrt 非负、GetSafeNormal）均有防护。

## 修复

`AlchemyWorldView.cpp` `Tick`：在 `Solve` 之后、`CommitStationPose` 之前，把所有不在 `ArmBones` 内的骨骼折叠到两侧已解锁骨的中点、缩放 0.01：

```cpp
if(ArmBones.Num()&&Hands[0].Clavicle>=0&&Hands[1].Clavicle>=0)
{
    const FVector Anchor=(Pose[Hands[0].Clavicle].GetLocation()+Pose[Hands[1].Clavicle].GetLocation())*.5f;
    const FTransform Fold(FQuat::Identity,Anchor,FVector(.01f));
    for(int32 I=0;I<Pose.Num();++I)if(!ArmBones.Contains(I))Pose[I]=Fold;
}
```

效果：体骨/肩口残余蒙皮收缩成藏在两臂根之间的小球，镜头近裁剪面附近不再存在任何蒙皮几何；手臂、手指、IK 全部不变。折叠点在两锁骨中点，天然落在 `PosedLocalBounds`（ArmBones +10cm）内，不会引入剔除问题。只改炼药视角，锻造台/枪械装配的同构代码未动（其镜头-躯干关系不同，且未报告此线）。

## 遗留风险与回退判断

- 若细线其实是手臂链**内部**的退化面（全部权重在手臂骨上），本修复不影响它——需运行期 `showflag.SkeletalMeshes 0` 复核（线消失＝手臂蒙皮范畴，仍在＝非手臂线源）。
- 备用诊断清单（已从源码移除，仅当线仍在时需先恢复）：`fps.Alchemy.Diag 1` 屏幕标签、`fps.Alchemy.ListThin 1` 组件点名日志 `ALCHEMYTHIN`、`fps.Alchemy.HideAll`/`fps.Alchemy.LaserHold` 对照、`showflag.PostProcessing/CustomDepth/StaticMeshes/Translucency/Particles/SkeletalMeshes` 分层、UI 遮挡判定。

## 验证状态

**未做运行验证**（用户暂停运行诊断；按规则不主动测试）。静态证据充分但非 100% 确证；修复低风险（不碰可见手臂、不碰资产），请用户进炼药台工作视角复核倒料与蘸取。
