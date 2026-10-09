# 无面安保 V03：僵尸动作与手脚显示修订

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

当前衣物与组合网格已更新为 [V04](../V04/README.md)，修订腰侧杂物、领口及衣物尖刺；三段 V03 僵尸动作继续使用。本目录保留原制作与排查历史。

2026-10-08。用户要求男性继续以僵尸动作为基础，并报告出生后手脚始终不可见。

## 制作内容

- 待机改为 ZombieAnimationPack `anim_Idle_A`，行走改为 `anim_Walk_A`，攻击继续以 `anim_Attack_D` 为整身供体。此前 Jason 普通男性待机和行走退出当前入口。
- 使用项目现有 UE5 Manny 源骨架，经 UE 原生 IK 重定向到独立安保骨架。待机与行走减轻约 5 度上背弯曲、整臂外展避让约 6 度；攻击整臂避让约 4.5 度。保留僵尸垂臂、屈膝拖步和转体发力。
- 攻击 2.30 秒，命中窗口 0.589565–0.785882 秒，恢复 0.38 秒。行走源足部速度约 52.1409 cm/s；资产倍率 0.498649 与共享控制器 `velocity/26` 配套，保留 78 cm/s 实际移速。
- 重建两只执勤靴。源脚部先在踝部封口形成闭合体，再进行体素重构、减面和开靴口；鞋面、鞋底、鞋带重新制作。鞋头整体跟随同侧脚骨，靴筒渐变跟随小腿；鞋内脚部使用同样权重关系。
- 从完整身体母版重建显示副本，保留整个手掌、手指及向前臂延伸 5.5 cm 的袖口搭接，并保留靴内双脚。其他制服、材质、骨架和物理资产继续沿用原版本。
- 穿衣组合 189342 三角面、161 骨骼、7 材质槽。完整身体母版仍为 199401 三角面；衣物源中 75 个独立对象。没有新增动态布料、C++ 或玩法能力。

## 定向排查结论与边界

已定位靴子制作缺陷：V01 对未封踝口的开放脚壳进行体素重构，鞋面和靴筒大量丢失。原休止姿势下，左/右靴上部最高仅约 7.19/3.91 cm；修订前足部身体又被显示裁切剔除。V03 源姿势下完整靴筒约 22.6 cm 高，另有独立鞋底。

手部原因没有冒充已经确定：旧 UE 组合资产实际包含左右手掌和手指，骨骼缩放约为 1，组件材质覆盖为空。将实际 UE 旧待机变换离线作用于导出的皮肤绑定数据，左右手各有约 3800 个主要受手/指骨驱动的顶点，手部仍位于身体两侧，未出现零缩放或消失。抽样的衣物包围读取也未显示整手藏进袖筒。用户游戏中“出生即不可见”现象尚未在游戏中复现；V03 完整显示副本和新动作需要由用户查看实际结果，不能将这些资产读取等同于游戏问题已确认解决。

针对本次报告的只读数据在 `Diagnosis/`：`ue_limbs_before.json`、`component_before.json`、`import_before.json`、`geometry_before.json`、`hand_occlusion_before.json`、`saved_ue_skin_pose.json`。

## 文件与资产

- 可编辑模型：`Authoring/FacelessSecurity_V03.blend`。
- 动作源：`Motion/FacelessSecurity_MaleMotion_V03.blend`，三段 `A_Security_Male_V03_*.fbx`。
- `Delivery/` 分别保留穿衣组合、独立衣物、完整身体的 FBX/GLB。
- 当前入口：`/Game/Monsters/FacelessSecurity/BP_FacelessSecurity`，F6“无面安保”。
- 新网格：`SK_FacelessSecurity_V03`、`SK_FacelessSecurity_Clothing_V03`、`SK_FacelessSecurity_Body_V03`。
- 新动作：`/Game/Monsters/FacelessSecurity/Animations/V03/A_Security_Male_V03_{idle,walk,attack}`。
- 保存记录：`ue_mesh_delivery.json`、`ue_delivery.json`；导入记录 `Logs/import_background.log`。原 V01/V02 资产和女接待员保留。

制作先沿用已打开编辑器的互斥桥。一次接入因 PIE 正在运行而未发送修改；用户退出并关闭编辑器后，改由无界面 commandlet 实际导入、保存。三个网格、三段动作及原蓝图已保存，进程退出码 0（0 errors）。不自动重新打开编辑器、运行游戏、截图或渲染。未做游戏测试，由用户测试。
