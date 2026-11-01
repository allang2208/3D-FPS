# 静电场握柄 V3 游戏重拓扑

用户授权：对当前 V2 静电场握柄减面、重拓扑。保留设计语义、安装端、握持尺寸和玩法。

## 源模型与游戏模型

- V2 高模完整保留在 `../StaticFieldGripV2/`，原始导出为 1,960,020 三角形。
- V3 游戏导出为 **175,732 三角形**，比 V2 源导出减少 **91.03%**。
- 这两个数字均为 Blender 导出几何，不能当成每帧可见 Nanite 三角形或帧率收益。
- 分件四边面制作源：`StaticField_Design.blend`；含运行时合并网格：`StaticField_Editable.blend`。
- FBX、GLB 位于 `Export/`。运行时为一个静态网格、6 个材质分区；可编辑源分件数不等于游戏组件数。

## 重拓扑与细节转移

- 皮革沿原有螺旋接缝重新采样，使用 128 × 256 主体网格；保留包覆起伏与端部厚度。
- 440 处双股针脚共 880 个线体仅保留在 V2 烘焙源，游戏版转入切线空间法线、基础色和 ORM。
- Cycles selected-to-active 实际投射 V2 皮革/针脚；源皮革的微表面法线也参与法线烘焙。
- 烘焙只处理侧面 UV 岛，排除被接头遮盖的端盖，防止平面端盖 UV 覆盖主体图集。
- 银色导条、编结、环印仍为实体；按曲率与饰纹周期降低扫掠采样密度。闭环复用首尾拓扑，取消重叠封帽。
- 两端原装接触面直接复制 V2 网格与面角法线，保留接口 UV；仍使用原位置偏移 +40.5 cm，不改握持与动作。
- 皮革保持 4096 × 8192 烘焙图，金属继续复用原有 4096² 材质；不增加视差材质采样。

## UE 接入

- 新资产隔离路径：`/Game/Weapons/ThunderGodHammer20261028/StaticFieldGripV3Game`。
- 保持 Nanite，游戏源网格本身已精简；回退网格设为 15% 三角形目标，用于传统/光追表示。
- 实际导入三角形数与保存结果由 `import_receipt.json` 记录；`publication_receipt.json` 记录活动配置切换。
- 仅切换 `thunder-god-hammer-modules.json` 的 `slots.grip.static_field_grip` 外观引用；战斗数值、感电逻辑、图标和其他配件不变。
- V2 源与已保存资产保留。共享配置写入前保存备份，并检测同一写入窗口的修改。

## 制作入口与边界

顺序：`prepare.py` → Blender `author.py` → Blender `bake_leather.py` → Blender `finalize.py` → `prepare_import.py` → `install.ps1`。

后台制作、烘焙、导出和资产导入属于本次工作；没有启动 UE 编辑器、运行游戏、性能采样或追加验收渲染。面数下降不能替代实际帧率测量，最终视觉效果由用户游戏内检查。
