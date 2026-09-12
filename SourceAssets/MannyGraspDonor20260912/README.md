# GitHub 抓握迁移：M4 / AKM 垂直握把

2026-09-12：已将 VRE `GrabAnimation` 抓握迁移到当前 Manny 手臂，接入 M4 / AKM 各 9 条动画。本轮仍待用户视觉评价；前一版 Opposed 已被指出不及预期。

## 看结果

- [旧版与本轮抓握对比](Delivery/Grip_Comparison.png)
- [玩家视点与腕肘](Delivery/Player_Wrist_Views.png)
- [原始 GitHub 抓握与手套迁移](Delivery/Original_Donor.png)
- [M4 实机动作](Delivery/m4.mp4) / [AKM 实机动作](Delivery/akm.mp4)
- [M4 换弹接触帧](Delivery/m4_ReloadReview.jpg) / [AKM 换弹接触帧](Delivery/akm_ReloadReview.jpg)

视频按截图日志时间间隔组合，为无声视觉证据，并非原生 30 fps 录屏或音效验收。玩家近景使用真实玩家眼睛位置，以手腕和拇指为焦点、FOV 30；idle 截图保留普通持枪画面。

## 采用的来源

来源为 [VRExpPluginExample 的 GrabAnimation.uasset](https://github.com/mordentral/VRExpPluginExample/blob/bf4c7ba554ecbbe614ed3d16669ef53d3f888f09/Content/VRE/Core/GraspingHands/VRHandMeshes/Animations/GrabAnimation.uasset)，固定提交 `bf4c7ba554ecbbe614ed3d16669ef53d3f888f09`。实际打开、导出 FBX 并渲染后，确认包含四指闭合和拇指横向弯曲。它是 1 帧静态姿态，UE 序列长度 1 秒，不包含步枪前臂支撑、M4/AKM 挂点或换弹动作。

最初检查的 Epic `A_MannequinsXR_Grasp_Right` 只收拢中指、无名指和小指，食指、拇指开放，因此未采用它作为闭合母版。不能凭 Grasp 名称判断内容。

VRE 仓库提供 [MIT 许可证](https://github.com/mordentral/VRExpPluginExample/blob/bf4c7ba554ecbbe614ed3d16669ef53d3f888f09/LICENSE.txt)；Epic XR 手模、骨架等另按 [Unreal Engine EULA](https://www.unrealengine.com/eula/unreal) 的模板/示例内容条款核对，不将整包素材一概标为 MIT。公开内容仅作者脚本、来源及验证摘要；原始资产、动作矩阵、照片和加工后二进制仍留本机。没有引入整个 VR 插件。

## 方法及限制

保留 `SK_Manny_Arms_Export` 网格、骨长、rest、局部关节位置及缩放。按手掌前向/横向/法向建立左右手镜像，在 rest 坐标系间转移旋转。10 条指骨方向抽查与原始动作的误差在当前浮点测量下为 0°，没有逐指猜欧拉角。

厚手套完全闭合会相交，最终 19 个手指/掌骨旋转统一采用原始抓握的 80% 闭合幅度。四指并拢，拇指扣向食指上侧；整个手型对准握把，并沿原有肩肘参考解决整臂支撑。没有缩放手指或握把。M4 母版按握把局部坐标迁移到 AKM，保留各枪时长和主要换弹接触段，只改变持握及退握/回握过渡。

仍有手套与握把内部及相邻手指表面交叠。42 个抽查姿态中，M4 有 14 个握把相交、15 个指间相交，AKM 为 16 / 20。这是表面抽查计数，不能当作肉眼缺陷数量或零穿模验收。M4 静态近表面法线估计最大内部深度从完全闭合约 8.3 mm 降至 80% 闭合约 5.0 mm，不等同于连续碰撞测量。自然外观仍须看实际近景。

本轮仅垂直握把；45°、阻手器及配件游戏数值沿用此前配置，没有记为此次重新完成。用户指定的小阻手器后续可直接由自然握拳包裹、接受内部穿模。

UE 实机当前 `MI_Manny_01/02` 父材质为 `ArmsBlackWhiteTrial`，因此显示白手套/深色前臂；这是共享工程已有的材质状态，本轮只查询、未修改。Blender 对照图保留原花纹材质，图中分别标明。

## 引用及可编辑源

M4：`/Game/Weapons/M4VerticalGripVRENatural/Vertical`；AKM：`/Game/Weapons/AKMIntegration/SovietFab/GripVRENatural/vertical`。各含 idle、aim、fire、aim_fire、equip、reload、reload_empty、drum_reload、drum_reload_empty。

- [M4 九动作 Blend](Final/m4/vertical/M4_Vertical_VRE_Editable.blend)
- [AKM 九动作 Blend](Final/akm/vertical/AKM_Vertical_VRE_Editable.blend)
- 各动作 `.blend` / `.fbx` 位于相同目录；[38 文件散列](Final/delivery_manifest.json)。
- 原始姿态：`Donor/vre_Grasp_Original.blend`；选择参数：`Opening/0.8/aligned_fit.json`。

`Final/` 是当前接入及报告；根目录同名报告和 `m4/`、`akm/` 为完全闭合的早期实验，不是当前引用。没有强行覆盖编辑器占用的旧动画包。

## 验证和复现

[汇总](Final/validation.json)：18 条源文件保持时长、key 时间、非左臂轨道及主要换弹接触；18 条 UE 保存后回读通过。压缩最大位置差约 0.00165 cm，旋转差约 0.01105°。Native `9122750` 编译成功；新启动的 M4 / AKM 游戏分别通过 348 / 811 次功能检查，退出码 0，日志明确记录 VRENatural 动画路径。

导入与回读 Python 均完成；commandlet 退出码 1 含既有 GameFeatureData AssetManager / 本地 HTTP 服务冲突。运行中另有既有实验 Toolset Python 初始化错误；功能回归仍通过。源码、脚本、运行、外观接受分别记录，不宣称全工程无错误或通过打包。

制作顺序：`export_donor.py`（StudyProject，允许渲染导出网格）→ `inspect_donor.py -- --vre` → `retarget_pose.py` → `preview_opening.py` → `build_family.py` → `verify_source.py` → `import_family.py` → `verify_assets.py` → `assemble_editable.py` → `run.ps1`（两枪）→ `make_delivery.py`。工具为 Blender 5.1.2 / UE 5.8.2。复用 `VerticalGripFront20260911` 的整臂 solver 和原动作源，不能仅克隆本目录独立还原全部素材。FBX 对象级单位曲线不叠加到已有单位变换的源网格上。

接入改动保存为 [精确补丁](runtime-integration.patch)，相对于本轮 `IntegrationBaseline`。接入头文件包含共享未提交工作，公开提交不夹带其余内容；本机实际代码已经修改。二进制和第三方依赖按工程 AssetSetup 恢复。
