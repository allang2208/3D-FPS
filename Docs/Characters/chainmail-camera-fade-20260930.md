# 锁子甲统一近镜头保护（2026-09-30）

用户确认问题对象是锁子甲衣袖，并授权继续实现公共层优化。目标是处理多种动作中肩部、上臂衣袖贴到相机的闪入问题，减少逐动作增加避让补丁。

## 原因与方案调整

此前共用避让以肩部骨点决定权重，骨点在镜头后方时，带厚度的上臂衣袖表面仍可能进入镜头；其调用还依赖枪械动画实例，不能覆盖所有手部动作。QBZ191 普通换弹的已保存姿态提供了一个具体例子，见 [末段构图交接修复](../Weapons/qbz191-normal-reload-chainmail-20260930.md)。现有局部动画修复继续保留。

新增服装公共材质保护：对靠近相机的肩部、上臂衣袖逐渐裁去，采用实际着色表面到相机的距离，不依赖枪型、动作名或肩点是否越过相机。它处理的是镜头遮挡，不能代替不正确的肘部骨骼、蒙皮权重或远离镜头的几何相交修复。

## 已实现

- `modular_outfits.json` 为 `ue_chainmail_shirt` 增加三个 `first_person_materials`，依次覆盖外层锁环、钢制包边、内衬。材质与网格同批异步加载，仅第一人称应用。
- `FPSOutfitSecondaryMotion.cpp` 在现有 MID 初始化时，将该衣袖自身参考骨架的肩／肘／腕位置写入材质。不是套用 M4 的固定坐标，也不改动运行时骨骼、手位或袖口位置。
- `chainmail_camera_region.ush` 在顶点阶段计算双臂区域：肩和上臂参与，前臂近肘端到中段平滑减弱，腕部与袖口排除。单臂缺失的一侧不参与。
- 区域权重为 1 时，距相机 10 cm 内隐藏，10–22 cm 平滑恢复，22 cm 外完全显示；区域过渡带按权重减弱。使用 Masked 与引擎 `DitherTemporalAA`，不是整件衣袖突然开关。外层、内衬与包边共用规则，防止只裁外层而露出内衬。
- 保留原材质 PBR、环纹视差和最大 .12 cm 的共享袖口摆动。保护不依赖 `fps.Outfit.ChainmailSway` 强度；材质距离排除 WPO，避免微小摆动反复影响过渡。
- 没有新增组件 Tick、衣物模拟、逐帧骨骼扫描或网格重制。增加了一项顶点区域插值及像素距离／抖动遮罩运算；GPU 成本和过渡观感未测，不承诺帧率收益。

配置覆盖现有 22 个第一人称 rig：15 个枪械／单手枪派生，RuneSword、FrostSword、FrostArms、Axe、Pickaxe、Traversal、Bow。法杖使用 M4 手臂链路。这里的数量是接入范围，不是动作测试数量。

全部 `rig_meshes` 保持原引用；Body、掉落物和图标继续使用原材质。`appearance_family` 仍为 `ChainmailInsetBinding20260929`；此次只是第一人称材质覆盖，不应将整个网格家族改名或回退。

## 实际落盘

- 三份新材质已保存到 `/Game/Characters/ModularOutfit20260924/ChainmailCameraFade20260930/Materials/`：`M_Chainmail_CameraFade`、`M_CuffSteel_CameraFade`、`M_Lining_CameraFade`。
- 作者入口：`Tools/ModularOutfit/import_chainmail_camera_fade.py`；接入入口：`publish_chainmail_camera_fade.py`。两步已实际执行，不只是准备脚本。
- `FPSGAMEEditor Win64 Development` 构建成功，更新 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。日志：`Saved/BuildEditor/chainmail-camera-fade-20260930.log`。
- 后台资产制作日志：`Saved/chainmail-camera-fade-import-20260930.log`，三个保存完成标记，commandlet 正常结束。执行未启动交互编辑器。
- `SourceAssets/ChainmailCameraFade20260930/` 保存 `before.json`、`configuration-before.json`、`native-build.json`、`saved.json`、`published.json`。配置接入保留当前全部网格引用。

未运行游戏、PIE、动画回归、截图或渲染验收。首次接入的距离参数及抖动过渡效果由用户实机测试；不能据此宣称所有动作无穿模。后续若问题仅在镜头近处，优先调整公共区域和距离；如果裸臂也扭曲或远处仍相交，再定位具体姿态或权重。
