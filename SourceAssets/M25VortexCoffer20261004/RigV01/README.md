# M-25 涡电匣：专用骨架、权重与蠕动 V01

2026-10-04，根据用户“做好绑骨和权重设置，移动方式作蠕动状”制作。使用用户提供的 Meshy GLB，后台完成源文件和导出；未启动 UE、未做渲染、动作测试或游戏验收。

## 已落盘

- M25_VortexCoffer_RigAndCrawl_V01.blend：可编辑骨架、全部蒙皮、打包的原始材质贴图及三段动作；默认选中待机动作。
- M25_VortexCoffer_RigV01.glb：完整蒙皮模型、PBR 和三段骨骼动画。
- SK_M25_VortexCoffer_V01.fbx：绑定姿态下的完整蒙皮模型。
- Animations/A_M25_Idle.fbx：待机。
- Animations/A_M25_Crawl_InPlace.fbx：原地蠕动。
- Animations/A_M25_Crawl_RootMotion.fbx：带根骨前进位移的蠕动。
- Textures/：原图字节提取的底色、金属度/粗糙度、法线，及通道说明。
- skeleton_spec.json、skin_weights.npz：骨架定义及按源 GLB 顶点索引保存的权重。
- fitted_positions.npy、fitting_inputs.json：制作坐标和尺度输入。
- author_rig.py、package_blender_fbx.py：实际作者与格式转换脚本。
- author_receipt.json、package_receipt.json、animation_contract.json：制作、导出和动作数据。

原始未修改输入位于 ../Inputs/Meshy_AI_Arcane_Maw_1004062246_texture.glb。

## 绑定方法

147 根骨骼，其中 136 根变形骨。32 组底缘触须，每组 base / mid / tip 三段；7 组纵向体节和左右囊体控制；口部主骨及 8 个口缘控制；9 根电极骨及 9 个独立特效挂点，另有口部挂点。

基于实际源位置和局部分区生成连续权重，再取最大的四项并归一化。同位置顶点采用相同空间权重函数，避免 UV 接缝两侧的独立随机赋权。下腹支撑单独控制，低处触须末端加强 tip 权重，身体呼吸逐渐过渡到支撑区域。每个电极的陶瓷柱体区域采用单骨刚性绑定，柱座短过渡连接到对应囊体。

骨架按软体组织和支撑区域布置，未使用人形自动骨架。权重场属于本轮作者方案，没有获得动作测试或用户视觉认可；需要根据实际体验继续微调时，保留原始输入并在本版本基础上修订。

## 蠕动合同

全部为本轮原创骨骼动作，30 fps。Blender 导入后的帧号以 0 开始：

| 动作 | 时长 | 含末端的帧范围 | 根骨位移 |
| --- | --- | --- | --- |
| M25_Idle | 4.0 s | 0–120 | 无 |
| M25_Crawl_InPlace | 2.8 s | 0–84 | 无 |
| M25_Crawl_RootMotion | 2.8 s | 0–84 | 前进 0.448 m |

蠕动以由后向前传播的收缩波驱动躯干的纵向压缩和囊体起伏。底缘触须采用错相牵引，支撑占周期 70%，回收阶段抬起约 7.2 cm；运动设计参考速度为 0.16 m/s。支撑末端的局部后移与带位移版根骨的前进相抵消，接地效果仍待用户实际测试。

原地版供后续游戏移动组件驱动，带位移版供需要 root motion 的接入使用；两者只能选择一种位移来源，不能同时由移动组件和根骨重复推动。

## 几何、尺度与坐标

保留原来的 3,623,952 个 GLB 顶点、6,524,740 个三角形、UV、法线及 PBR 贴图，没有执行减面或重拓扑。当前是完整高模绑定母版。

按长轴 4.1 m 统一缩放，保留原 Meshy 体型，宽约 3.345 m、高约 1.291 m；没有为了追到原画 1.6 m 高度而把模型沿单轴拉伸。

GLB 制作坐标为 +Z 向前、+Y 向上；Blender 转换后为 -Y 向前、+Z 向上。FBX 按本工程已有导出方式使用 axis_forward=-Y / axis_up=Z。正式 UE 接入时应统一导入朝向和动作位移约定。

## 重建

在本目录执行：
1. py -3 author_rig.py
2. 使用 Blender 5.1 后台执行 package_blender_fbx.py。

author_rig.py 读取已保存的拟合位置与原始 GLB。修改尺度或参考源时应先更新 fitting_inputs.json 和 fitted_positions.npy，不能只改说明中的尺寸数字。脚本没有渲染或测试步骤。

## 当前边界

骨架、权重、三个动作、Blender / GLB / FBX 已制作并保存。后续 UEV01 已将本模型、Idle 和原地蠕动导入 UE，并接入基础追踪移动和 F6；对应生产回执、构建与边界见 ../UEV01/README.md。带根运动版保留为制作源，游戏使用原地版。攻击、受击、死亡和闪电特效尚未制作。未进行动画或游戏测试，交由用户测试。
