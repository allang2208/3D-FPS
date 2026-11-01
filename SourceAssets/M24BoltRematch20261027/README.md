# M24 拉栓右臂重新匹配（2026-10-27）

本轮针对用户指出的拉栓手势扭曲、右手与前臂进入枪体问题制作。采用 DJMaesen 原始 `arms@sniper.fbx` 的拉栓动作作为参考，保留当前定制 M24 的外观与机械行程。

## 制作与接入

- 通过源枪栓与当前枪栓的坐标关系重新配准动作；未使用已经重新定轴的枪械根骨作为配准基准。
- 重新匹配掌心、掌指关节和原始网格的指尖方向；保留当前 V9 手模的骨长、蒙皮与静止姿态。
- 分别调整抬柄、后拉、前推、压柄和退手阶段；右肘与前臂沿枪托外侧运动，握栓时为定制瞄准镜及枪栓杆留出空间。
- 仅替换 `fire`、`cycle`、`reload_empty`、`reload_empty_mag10` 的右锁骨及其子骨骼轨道。普通换弹、左臂、10 发弹匣动作、枪械机械轨道及事件时钟延续接入前配置。
- 后台 commandlet 已完成导入、烘焙和保存，见 `install_receipt.json`。实际运行继续使用 `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip` 与 `DA_M24_Mag10`，两个原资产已备份至 `Backups/`。
- 新版配置副本保存于 `/Game/Weapons/M24/BoltRematch20261027/`。临时导入的 Authoring 动画用于烘焙，不作为新增运行时动画依赖。本轮没有修改 C++。

## 可编辑素材

- `M24_BoltRematch_Editable.blend`：最终可编辑动作。
- `Exports/`：四个角色动作 FBX。
- `refined_poses.json`：最后一轮制作姿态。
- `M24_BoltRematch_Source.gif`：第一人称及侧面源动画预览，源采样 30 Hz，预览显示 15 fps。

## 范围与限制

预览来自 Blender，不是 UE 游戏画面；没有运行游戏、PIE 或通用回归测试。最终游戏中的视场、动画混合与运行时修形需要用户自行体验。

源网格的有限帧、有限顶点接触诊断用于本轮制作，不代表完整无穿模验收。拉栓核心段的明显前臂穿托及握栓穿插已作针对性调整；原有待机握把姿态及回到该姿态的首尾帧仍存在右手与枪托重叠，本轮没有改写其他动作的共同待机姿态。`surface_after.json` 保留这些结果，没有将其作为零穿模通过记录。

## 来源与署名

This work is based on "sniper animated" (https://sketchfab.com/3d-models/sniper-animated-b48999a250b2433da59f705c371a49b2) by DJMaesen (https://sketchfab.com/bumstrum), licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/).

本地原始许可文件：`../M24CustomScope20261026/Donor/GLTF/license.txt`。本轮修改包括 V9 手模重定向、手指与掌面配准、右肘路径及定制枪体接触调整。

当前定制模型页面：https://sketchfab.com/3d-models/m24-sniper-rifle-custom-scope-84b72eaf37a54ecb945017e3955455a0

GitHub 搜索发现 https://github.com/Terrydaktal/UnityZombies 的 README 提到 M24 动画，但本轮未确认其可直接复用的完整骨骼资产及独立素材授权，因此没有引入该仓库资源。
