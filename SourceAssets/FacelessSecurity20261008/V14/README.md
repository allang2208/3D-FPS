# 安保员 M-03 V14：帽带与帽檐连接

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

用户要求排查帽子与帽檐衔接处的漏空。当前身体继续使用 V13，动作继续使用 V06／V10／V12，本版仅修订独立帽子。

## 原因

V11 帽带与帽檐各自是独立厚壳。帽檐根部向两侧下垂，最低比帽带底边低 6.803 mm，形成可见缝隙；不是帽子挂点或爆头掉落代码导致。源拓扑与 65 个帽檐根部采样见 `Diagnosis/hat_before.json`。

## 修订

- 将皮革帽带和帽檐重建成同一连续实体壳；上、下连接边各共享 101 个顶点，两个侧端与底面全部封闭。
- 保留原帽檐外缘轮廓，根部连续接入帽带，帽檐厚度 3.5 mm，帽带厚度约 3 mm。
- 保留帽冠、滚边、帽带装饰、铆钉、徽章与文字共 2956 个顶点的位置，沿用原 4 个材质家族。
- 保留原头骨局部坐标和挂点；保留帽冠凸碰撞体，按修订帽檐重做第二个凸碰撞体。爆头击落继续使用同一帽子网格，质量 0.32 kg、冲量和 35 秒回收不变。
- 连接厚壳的针对性拓扑检查：非流形边 0、零面积面 0。总帽子 13560 三角面。未渲染或运行游戏，不将拓扑结果当作视觉验收。

## 文件与状态

- 作者源：`Authoring/SecurityServiceCap_Anatomical_V14.blend`；引擎局部坐标源：`Authoring/SecurityServiceCap_EngineLocal_V14.blend`。
- 导出：`Delivery/SM_SecurityServiceCap_V14.fbx`，包含两个 UCX 凸碰撞体。
- 制作：`Tools/FacelessSecurity/repair_hat_join_v14.py`；导入：`Tools/FacelessSecurity/import_hat_join_v14.py`。
- 已通过现有编辑器互斥桥导入并保存 `Accessories/SM_SecurityServiceCap_V14` 与原 `BP_FacelessSecurity`，共 2 项资产；保存收据为 `ue_delivery.json`。
- `Diagnosis/saved_hat.json` 确认原帽子组件引用 V14、头骨挂点坐标不变，导入后具有 2 个凸碰撞体和原 4 个材质家族。V13 身体网格继续使用。原 F6“安保员 M-03”入口沿用。

本轮无 C++ 修改，不需要原生编译或重启编辑器。未自动启动 PIE。
