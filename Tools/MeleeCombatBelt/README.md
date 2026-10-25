# 破阵近战腰带：精细模型 R1

母版为 `SourceAssets/MeleeCombatBelt20261025/ConceptR1/design-sheet.png`。本阶段只制作模型、原生绑定和材质，不发布物品定义、数值或 UE 资产。

## 制作源

- `author.py`：分段护腰、斜切快拆扣与穿带孔、双点刀鞘挂扣、磨刀石袋和固定带、铆钉与针脚。
- `native_geometry.py`：冻结的本工程腰线采样、原生权重及几何辅助方法；从本批 `Inputs/` 读取，不运行旧腰带制作器。
- `make_textures.py`、`surface_fields.py`：复用本工程织物，并制作暗红棕皮革、收边和金属 PBR。新颜色先按线性反照率定义再保存为 sRGB。
- `ModelR1/inputs.json`：本次选取的实际 ST6 裤装和原生身体输入，保留资产路径及来源散列。

## 输出

`SourceAssets/MeleeCombatBelt20261025/ModelR1/Exports/`：

- `MeleeCombatBelt_Jason_Editable.blend`、`MeleeCombatBelt_Kaitlin_Editable.blend`：完整分件和修改器、打包材质贴图、原生骨架；参考裤装收藏默认隐藏。
- `SK_MeleeCombatBelt_<身体>.fbx`、同名 `.glb`：对应身体的完整细节绑定网格。
- `<身体>_NativeWeightedMesh.json`：UE 厘米坐标、原生骨骼、逐顶点权重、UV 与法线资料。
- `SM_MeleeCombatBelt_Display.fbx`、同名 `.glb`：独立完整细节展示件，正面 −Y、上方 +Z；无骨架，不影响穿戴空间。

保留源模型的完整细节，不进行自动减面。本轮没有另外制作远景 LOD。几何计数由生成过程写入 `Authored/<身体>_production.json`，不能把作者网格面数当作运行帧率证据。

`Textures/` 包含 BaseColor、OpenGL Normal、ORM（R=AO，G=粗糙度，B=金属度）、16 位 Height 及物理高度场 NPZ。皮革为 4096，其余贴图为 2048；UE 后续导入法线时按清单处理绿色通道。贴图微细结构与真实开孔、厚度、接缝分别保留。

## 后台制作命令

```powershell
python Tools/MeleeCombatBelt/make_textures.py
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup -t 6 --python-exit-code 1 --python 'D:/FPS3D/FPSGAME/Tools/MeleeCombatBelt/author.py' -- Jason Kaitlin
```

该命令会重新写入本批 R1 输出；后续修改先新建版本目录并调整脚本目标，保留已交付母版。

男女版本分别使用原生腰线与权重，刚性扣具和挂架尺寸相同，仅改变挂载位置。当前输入为已保存 ST6 裤装参考姿态；动画、其他衣物、背包组合与联机效果尚未测试。本轮不自动渲染预览或启动 UE。

## 游戏接入状态（2026-10-25）

本页上方记录 ModelR1 的制作阶段。后续游戏接入已由 `Tools/CombatBeltsIntegration` 完成：男女穿戴、三级 LOD、PBR、正面物品图标、掉落网格、物品目录和 +15 强化属性已保存发布。Editor/Game 已后台构建。运行、服装动作组合及联机未测试；接入回执位于 `SourceAssets/CombatBeltsIntegration20261025/melee`。
