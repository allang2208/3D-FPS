# 弓箭 V10：举弓、ADS 与下蹲姿态复用

2026-09-26。源码、八段动画导入保存与 FPSGAMEEditor 后台构建已完成；未启动可视编辑器、游戏、预览或测试。动作观感与操作效果由用户测试。

## 参考与制作范围

参考用户提供的 [BV1jGdDBkEkc](https://www.bilibili.com/video/BV1jGdDBkEkc/) 33–48 秒，《【APEX英雄】波赛克S28赛季进化皮展示-大人物》。通过浏览器正常播放页面定位到所需时间，逐半秒查看该范围画面。

观察到的动作关系：站立腰射有侧倾；ADS 回正靠近中央；下蹲腰射明显横持；下蹲 ADS 恢复竖直瞄准；放箭后右手短暂向后、向外随动。二维视频仅用于姿态、阶段和节奏参考，下面的三维角度、距离是针对当前木弓和 V7 裸臂重新设定的制作参数，不是从视频准确反求的动作数据。未提取或导入 Apex 的模型、骨架、动画或声音。

制作源：`SourceAssets/DarkBow20260925/ReferenceUpgradeV10/author_actions.py`。复用 ContactV9 的手臂表面、原生骨架、闭合左手与三指弦接触数据，以及原有 Sparrow 轨迹。Blender 源文件、8 个 FBX、制作记录和导入回执均保存在同目录。浏览器参考画面为本地工作资料，不作为游戏资源打包。

## 动作与层级

- **举弓后拉弦**：保留独立 DrawEntry 0.2 秒。Draw 首帧已经举弓，弓握把由待机 `(46,-20,-20)` 到准备 `(64,-18,-11)` cm；实际拉弦到满拉只继续移到 `(70,-16,-8)`。拉弓时长仍为 1.4 秒，受原有属性节奏驱动。
- **放箭随动**：右手短暂后撤、向右打开，约 0.14 秒后进入回收，整段仍为 0.64 秒。手指释放使用满拉接触姿势起点。运行时以实际释放姿势与 Release 首帧的局部差值接续动作，在回收曲线中逐步去掉差值，兼顾半拉与满拉释放。
- **ADS**：单独保存瞄准权重，不重启搭箭／拉弦／保持／释放片段。瞄准将动画弓握把变换到指定箭台位置与弓身朝向；相机缩放、移动镜头抑制和鼠标灵敏度跟随同一权重。右键瞄准期间限制冲刺并使用瞄准移动速度。
- **下蹲**：绕当前握把增加侧倾和小幅收拢，复用同一组动画。与 ADS 连续混合，满瞄准时覆盖腰射侧倾；角色已有蹲姿相机高度继续负责降低视点。
- **接触与时钟**：手臂、弓体、弦与箭共享 BowPivot。先采样动画，再更新姿态层，再更新几何；姿态计算使用未经叠加的组件空间握把，避免前一帧位姿反馈。当前木弓的弦平面和拉距锚点写入新动画。

## 可复用参数

位于 `Content/ColdSteelData/bows.json`，均为物品数据键。换弓可沿用代码与阶段，只配置匹配的骨架动画前缀、部件锚点及下列姿态参数。

| 键 | 当前值 | 用途 |
| --- | --- | --- |
| bow_draw_entry_seconds | 0.2 | 到达举弓首帧 |
| bow_ads_in_seconds / bow_ads_out_seconds | 0.18 / 0.16 | 瞄准进出时间 |
| bow_ads_fov_scale | 0.82 | 基础垂直视角倍率 |
| bow_ads_rest_cm | 70,0,0 | 相机空间箭台目标 |
| bow_ads_rotation_deg | 0,0,0 | 瞄准弓体 Pitch/Yaw/Roll |
| bow_crouch_in_seconds / bow_crouch_out_seconds | 0.18 / 0.22 | 蹲姿侧倾进出时间 |
| bow_crouch_cant_deg | -55 | 在腰射动画上追加的相机前轴侧倾 |
| bow_crouch_offset_cm | -1.5,-2,-0.5 | 围绕握把收拢的位移 |

瞄准和下蹲权重可在任意拉弓阶段改变。四个 Still North 音效仍使用已有阶段接线，0.2 秒到位之前不计拉距；箭支依然只在成功发射时扣除。

## 已落盘与接入

八段 `A_Bow_Idle/Ready/Equip/Nock/Draw/Hold/Release/Run` 已保存到 `/Game/Weapons/DarkBow20260925/ReferenceUpgradeV10/`。继续引用 ContactV9 的 V7 裸臂网格和已有骨架。JSON 动画前缀切到 V10，表现版本由 15 升到 16，复用既有存档表现迁移；新目录加入显式打包资源路径。

涉及运行时：`BowWeaponComponent`、`BowArmsMeshComponent` 和角色的移动／镜头／灵敏度接入。放箭姿态差值回收起点为 Release 片段的 `0.14/0.64`，若今后改变该片段的回收比例，应同时调整 `BowArmsMeshComponent` 对应比例。

导入记录：`SourceAssets/DarkBow20260925/ReferenceUpgradeV10/import-receipt.json`，8 个已保存资产。导入通过现有后台 commandlet 和批次互斥执行。

构建记录：`Saved/BowAudioStillNorth20260926/build-reference-v10.log`，FPSGAMEEditor Win64 Development，结果 `Succeeded`。构建产物是项目 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。后台构建成功仅说明构建完成，不代表运行、接触或视觉验收通过。

修改前文件快照保存在 `Saved/BowReferenceUpgradeV10/Before/`；共享源码的其他修改应继续保留，不应直接用快照整文件覆盖。
