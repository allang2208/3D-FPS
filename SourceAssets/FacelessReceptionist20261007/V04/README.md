# 无面接待员 V04（2026-10-08）

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

针对用户截图中的攻击屈膝穿裙、肩部衣层错位和整体衣料质感进行修订。实际保存了 23 个 UE 资产，原 F6 无面接待员蓝图已切换到 V04。未启动 UE 图形编辑器或游戏／PIE；制作前已经运行的编辑器后来关闭，本轮导入和读回由后台 commandlet 完成。

## 修订内容

- 裙摆以两腿在实际动作姿态中的空间包络制作连续衣裙修正形态，保留实体厚度，消除截图所示大腿穿出；衬片、裙侧／后缝随同修正。形态在源动作采样之间连续混合，运行时使用既有动画曲线求值，没有新增逐帧碰撞求解或 Tick。
- 肩部重建连续肩部衣片，焊接复制人体表面中的重合边界后平顺处理，以胸／锁骨／上臂连续赋权；去除被新衣片覆盖的旧肩盖，避免重叠层打架。
- 衬衫保留可见前襟及独立领口／袖口，移除衣内与外套争抢表面的重复肩背壳。穿衣显示身体剔除确定在衣内的躯干和上腿面；完整原身体仍保存在作者文件及独立身体 FBX／UE 资产中，原身体 199526 三角面未减面。
- 西装、衬衫、包边采用 20 cm 物理尺度的布纹 UV，颜色／法线／粗糙度来自同一微表面场。新建 UE Substrate 布料材质，加入受限绒面反射并降低塑料高光；胸牌、鞋及皮肤分别保留原材质分区。
- 三段现用女僵尸动作复制为 V04，只增加衣物修正曲线，不修改骨骼动作、攻击时序、AI、导航、胶囊或 F6 入口。仍然不是 Chaos 布料模拟。

## 交付文件

- Authoring/FacelessReceptionist_V04.blend：完整隐藏身体、穿衣显示身体、55 个独立衣物／细节对象、共同骨架、修正形态。默认绑定姿态。
- Delivery/FacelessReceptionist_V04.glb：完整穿衣显示模型及修正形态；不含动画时间曲线。
- Delivery/FacelessReceptionist_Clothing_V04.glb：独立衣物及共同骨架、修正形态。
- Delivery/SK_FacelessReceptionist_V04.fbx：穿衣运行网格。
- Delivery/SK_FacelessReceptionist_Clothing_V04.fbx：独立衣物运行网格。
- Delivery/SK_FacelessReceptionist_Body_V04.fbx：完整身体，未剔除衣内面。
- Textures/：现有分区贴图及更新后的三组 2K 织物 PBR。
- MotionSources/：从实际蓝图所用 UE 三段动作导出的 FBX、逐帧变换和来源记录。
- corrective_curves.json / corrective_manifest.json：修正形态的时间权重和采样来源。
- Preview/V03_attack_diagnosis.png：修复前问题复现。
- Preview/V04_attack_corrected.png：修复后攻击关键姿态。
- Preview/V04_attack_interpolation.png：非制作采样点的攻击中间姿态。
- asset_readback.json / ue_delivery.json / export_receipt.json：本轮针对性检查与实际保存记录。

穿衣导出 267462 三角面、161 骨、60 个修正形态；独立衣物与穿衣网格的形态名一致。60 个形态分属待机 17、行走 21、攻击 22 个；每个采样时刻只需要相邻两个形态插值。完整身体保留为独立母版，不重复显示在穿衣版本里。

## 实际 UE 引用

- 原蓝图：/Game/Monsters/FacelessReceptionist/BP_FacelessReceptionist。
- 新穿衣网格：/Game/Monsters/FacelessReceptionist/SK_FacelessReceptionist_V04。
- 独立衣物／身体：同目录 SK_FacelessReceptionist_Clothing_V04、SK_FacelessReceptionist_Body_V04。
- 三段动画：Animations/A_Receptionist_V04_idle、walk、attack。
- 新材质：Materials/M_FR4_Skin、Suit、Shirt、Badge、Trim、Shoes。
- 共用原独立 Skeleton 和 PhysicsAsset；未修改源女僵尸资源。

## 本轮检查与边界

用户明确要求检查，所以针对攻击屈膝、肩部、衣层及材质进行源姿态检查。关键姿态与非采样中间姿态已在 Blender 离线检查；保存后另起后台只读进程确认 60 个形态、三个片段的形态曲线标记／逐帧数值、曲线权重和、片段时长、独立衣物形态名称及原蓝图引用。待机／行走／攻击分别读回 309／99／101 个曲线采样。

这些结果不是 UE 实机动画、动态布料或游戏视觉验收。没有自动运行游戏、PIE、地图截图或修改场景；游戏效果仍由用户体验。没有新增 C++，没有触发原生构建。V03 的问题源与旧 UE 网格／动画保留，未清理其他资产。

## 制作脚本

Tools/FacelessReceptionist：inspect_v04.py 读取实际蓝图及导出动作；source_motion_v04.py 保存原生变换；author_v04.py 制作衣物与材质；export_v04.py 导出；import_v04.py 导入／保存；readback_v04.py 为本轮明确要求的针对性读回；render_pose_v04.py 为本轮明确要求的姿态检查。

导入器采用新的 V04 名称，已存在的 V04 资产默认复用以续接中断，重新制作后的进一步重导应使用新修订名或明确处理已有导入设置，不可将重跑当作已经刷新。作者文件与导出已包含最终肩部修订。Preview/V04_layer_diagnosis.png 仅为制作中的分层定位，不是最终材质预览。
