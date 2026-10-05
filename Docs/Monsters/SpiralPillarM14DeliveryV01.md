# 螺柱者 M-14 — V01 交付

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04，工程 D:/FPS3D/FPSGAME。已完成后台制作、原生构建与资产导入保存，未运行游戏测试。

## 使用入口

用户启动游戏后，在 F6 怪物生成列表选择 **螺柱者 M-14**。稳定 ID 为 `SpiralPillarM14`，类路径为 `/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14.BP_SpiralPillarM14_C`。

## 制作文件

- [带骨架与动作的 Blender 文件](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV01/Authoring/M14_Rigged_Animated_v01.blend)
- [骨骼网格 FBX](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV01/Exports/M14_Skeletal_v01.fbx)，同目录保存 7 段独立动作 FBX。
- [制作配方与部位记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV01/Records/production_recipe.json)
- [UE 已保存资源清单](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV01/Records/ue_delivery.json)
- [原始来源清单](../../SourceAssets/SpiralPillarM14Meshy20261004/source_manifest.json)
- [C++ 怪物类](../../Source/FPSGAME/Monsters/SpiralPillarM14.cpp) / [配置声明](../../Source/FPSGAME/Monsters/SpiralPillarM14.h)
- [后台制作脚本](../../Tools/SpiralPillarM14/build_m14_v01.py) / [后台导入脚本](../../Tools/SpiralPillarM14/import_m14_v01.py)

UE 资源保存在 `Content/Monsters/SpiralPillarM14/`，包括 SK_M14、Skeleton、PhysicsAsset、3 张纹理、4 个材质、7 段动画和 BP_SpiralPillarM14。

## 模型与驱动

源模型统一为 3 米高、根原点落地。9 个制作对象分别为主体与根裙、口器、牙列、左右膜、左右囊体、束具、锁链。它们是基于位置区域与贴图信息得到的表面分区，连接位置采用一致权重，UE 中使用一个骨骼网格。没有把显示分区当作可拆卸器官，也没有增加断肢玩法。

专用骨架包含 48 根作者骨骼：基底与柱体主链、8 组根须支撑、径向口器、囊体、膜和链组；FBX 导入会另包含一个骨架对象根。每点最多 4 个骨骼影响，保留源三角面、UV 和角点法线。膜与链采用骨骼摆动，没有 Chaos Cloth 或逐链节物理。原始高模 1,936,942 三角面完整保留，没有自动减面或生成 LOD。

材质分为 Body、Mouth、Membrane、Metal，复用原始 2K PBR：颜色使用 sRGB，粗糙度取 G、金属度取 B，法线导入时转换绿通道方向。源图无 AO 绑定，未冒充 AO；薄膜沿用有孔几何与双面材质，未新增透明大面或透光贴图。

## 动作与战斗

| 动作 | 时长 | 实现 |
| --- | --- | --- |
| 待机 | 4 秒 | 柱体呼吸、囊体与悬挂组织轻动 |
| 蠕行 | 2.4 秒 | 根裙交替支撑与拖拽，配 28 cm/s 位移 |
| 左转 / 右转 | 各 2.4 秒 | 分区支撑循环，随实际转向选择 |
| 咬击 | 1.9 秒 | 收紧、口器前探、回收，接触时刻 0.86 秒 |
| 受击 | 0.7 秒 | 短暂收缩与组织摆动 |
| 死亡 | 3 秒 | 柱体失张力倒塌，随后进入共享尸体物理与清理流程 |

这是基于专用骨架创作的首版动作，不是已验收的动作成品。运行时复用项目 AIController / Behavior Tree、战斗韧性、减伤、经验与击杀事件；咬击使用实际口器位置、前向范围和障碍遮挡处理。尸体使用按蒙皮源点构建的凸体碰撞与约束、共享尸体预算；存活击倒暂映射为硬直，没有专用起身动作。

首版数值为 HP 1800、攻击 48、物防 40、魔防 20、等级 10、经验 650；寻敌 1500 cm、追击边界 2600 cm，咬击触发距离 185 cm、冷却 3.2 秒。这些是可在蓝图上调整的初始玩法配置，未做平衡测试。

导航复用项目现有大型怪物导航规格（半径 225 cm / 高 450 cm），保留已有地图导航数据；角色胶囊半径 110 cm / 半高 150 cm，F6 生成占地半径 125 cm。

## 交付状态

FPSGAMEEditor 与 FPSGAME 的 Win64 Development 构建均完成。UE 导入脚本实际执行并保存资源，逐项保存记录见 ue_delivery.json。未启动图形编辑器或游戏，未执行自测、渲染或验收。

当前保留约 194 万三角面的 LOD0；同屏性能、近景分区边界、蒙皮形变、口器接触、物理与导航表现均留给用户测试。上述资源已落盘，但不宣称运行表现或视觉质量已经验证通过。
