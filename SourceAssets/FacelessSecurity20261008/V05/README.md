# 无面安保 V05：替换移动动作，重建袖筒与手臂蒙皮

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

2026-10-08。用户反馈 V04 移动时两侧仍有拉丝、模型悬空，要求改用另一段僵尸移动动作并调整手臂。V04 未获用户认可，本版继续修复同一入口。

用户后续反馈本版肩袖连接、腰侧悬空件及攻击恢复仍不正常，当前已由 [V06](../V06/README.md) 接续修订；V05 作为制作历史保留，不代表已通过用户验收。

## 制作变更

- **拉丝来源。** 对用户报告区域的制作数据读取发现，原衬衫袖面存在前臂与骨盆混合驱动。例如相邻顶点的骨盆权重分别约 0.40 和 0.81，同一片袖面被手臂与腰部向不同方向拉扯；旧 Walk_A 的读取帧中，有约 307–347 条边同时超过原长 2.5 倍及 7.5 cm，最长接近 19.7 cm。记录见 `shape_motion_before.json`。这是源数据定位，不是本版游戏验收。
- **重建衣身和两条袖筒。** 删除原 `Security_Shirt_Continuous`，改为独立 `Security_Shirt_Torso`、左右袖筒和袖口，以肩部重叠连接。衣身只由躯干链驱动，袖筒只由同侧锁骨、上臂、前臂和手腕驱动，移除骨盆、脊柱、对侧手臂对袖子的影响。袖内外层先赋权重再制作厚度，保持成对顶点一致。肩章、衣袋与扣件重新贴合对应衣面。
- **手臂与裤裆。** 完整身体和显示副本的臂部重新绑定，手掌及手指保留同侧手部权重。裤裆由左右大腿平滑过渡，减少腰侧与两腿交界被独立方向拉扯。保留 V04 已删除腰包、收窄皮带的结果。
- **改用 Zombie Walk_B。** 来源为 `/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Walk_B`，不再使用 V03 的 Walk_A。保留原生骨架绑定姿态与骨长，增加 3° 肩臂空间。新动作 239 帧、60 fps、约 3.967 秒，按实际支撑脚回移速度换算播放倍率 0.499256，与原控制器速度除以 26 的逻辑配套；角色移速维持 78 cm/s。
- **鞋底接地。** 用靴底最下层顶点计算地面，按脚步抬落建立平滑支撑区间；支撑时调整脚掌朝向，并以固定腿骨长度求解髋、膝、踝。最低鞋底落在局部 Z=0。原公共移动组件只平滑楼梯，不补偿胶囊离地距离，因此仅将本角色网格相对 Z 从 -92 cm 调为 -94.15 cm，补偿 UE 角色胶囊 1.9–2.4 cm 的地面间隙中值。
- V03 待机、攻击及攻击命中窗口继续使用原资产；材质、物理、导航胶囊、AI 和 F6 入口保持原配置。

## 文件与接入

- `Authoring/FacelessSecurity_V05.blend`：独立可编辑的身体与 75 个衣物对象。
- `Motion/FacelessSecurity_MaleMotion_V05.blend`：新 Walk_B 烘焙动作，并保留 V03 待机、攻击动作数据供编辑。
- `Delivery/`：完整身体、独立衣物、穿衣组合的 FBX 与 GLB；穿衣组合 188302 三角面，完整身体 199401 三角面，161 骨、7 材质槽。
- `Motion/A_Security_Male_V05_walk.fbx`：新移动动作。
- UE 目标为 `/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_V05`、`SK_FacelessSecurity_Clothing_V05`、`SK_FacelessSecurity_Body_V05` 和 `/Animations/V05/A_Security_Male_V05_walk`，接入原 `BP_FacelessSecurity`，F6 名称仍为“无面安保”。
- 制作脚本：`Tools/FacelessSecurity/rebuild_arms_v05.py`、`retarget_walk_v05.py`、`author_walk_v05.py`、`import_security_v05.py`。
- 制作记录：`arm_rebuild.json`、`export_receipt.json`、`native_retarget.json`、`motion_manifest.json`；实际 UE 保存状态记录在 `ue_delivery.json` 与 `Logs/import_background.log`。

三个网格、新行走动作和原蓝图均已通过后台 commandlet 实际导入、保存，`ue_delivery.json` 为 `stage: saved`，最终导入进程退出码 0。原 F6 入口已指向 V05 穿衣模型和 Walk_B 动作。

中间原生重定向 commandlet 已输出完整姿态缓存和原始动作，脚本报告成功后在关闭阶段遇到 UE 动画压缩任务断言（退出码 1）。最终交付使用另行烘焙的 FBX 和独立导入步骤，不将该中间进程记为成功退出。

本版无 C++ 修改，不启动 UE 图形编辑器、游戏／PIE，不做验收渲染或额外测试。旧版本保留；游戏中移动、接地和袖部表现由用户测试。本角色仍使用骨骼蒙皮，没有动态布料或地形逐帧脚部 IK。
