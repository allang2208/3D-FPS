M-09 悬钟 — V03 绑骨交付
制作日期：2026-10-03

当前编辑源：
Authoring\M09_Rigged_v03.blend

带骨骼与蒙皮的导出：
Exports\M09_Rigged_v03.fbx
Exports\M09_Rigged_v03.glb

制作内容：
- 以 V02 拆分修整版继续，保留 25 个网格、原 UV/PBR 和封口几何。
- 113 根用于导出的骨骼，另有 8 个 Blender IK 控制骨。
- 两条悬挂长臂、两条腹前小臂；20 套三节手指链。
- 六片背叶，各有四段独立骨链；根部与主体权重衔接。
- 眼冠软连接与整体摆动骨；5 个主眼各自独立转动。
- 每个顶点最多 4 个变形骨影响，权重以 1024 份归一化。
- 腕箍所在区域使用稳定前臂权重；前臂软组织另有扭转辅助骨。
- 腹前小手仍留在主体网格里的指尖区域，也按对应的小手骨链分配权重。

使用：
1. 打开 .blend，选 M09_Rig_V03，进入 Pose Mode。
2. 默认 FK，所有骨头处于原始悬挂姿势，没有附带动作片段。
3. 骨架物体的自定义属性：
   IK_big_L / IK_big_R：长臂 IK；
   IK_small_L / IK_small_R：腹前小臂 IK。
   0 为 FK，1 为 IK。CTRL_*_grip 是抓握控制，CTRL_*_elbow 是肘部极向控制。
4. 手指与主眼骨集合默认隐藏，在 Armature 的 Bone Collections 中展开。
5. membrane_L1_01 等首段控制对应背叶，02–04 控制弯折和末端颤动。
6. eye_crown 控制眼冠摆动；crown_neck 控制连接；eye_01–05 控制主眼朝向。
7. root 用于整体位移；suspension 用于以悬挂位置为中心的整体姿态。
8. Blender 控制骨、约束和驱动器属于制作控制层。FBX / GLB 是变形骨架及蒙皮；
   以后制作动画时需烘焙到变形骨，不能指望 UE 直接执行 Blender 控制器。

交付边界：
已保存源文件并实际导出 FBX、GLB。未启动 UE，未导入为 UE 资产。
按用户规则，未追加姿态测试、验收渲染、重导入或游戏测试，变形效果由用户测试。
没有制作攻击动画、待机、眨眼形态键、物理资产、布娃娃或 AI。
当前保留 1,890,032 三角面的高模制作源；没有主动减面，也没有生成游戏 LOD。
交叉手指和背叶仍基于生成模型的既有拓扑，不能把完成蒙皮当作所有极限姿态已验收。

可重复制作：
D:\FPS3D\FPSGAME\Tools\HangingBellM09\Build-M09RigV03.ps1
骨架配方：Authoring\rig_recipe_v03.json
权重数据：Authoring\skin_weights_v03.npz
实际保存记录：Records\rig_delivery_v03.json
