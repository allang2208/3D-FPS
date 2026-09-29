# 201 Repair36：盖内壁尖刺、涂层差异与弹箱白材质

2026-09-29 已完成现用资产修复和本次用户要求的定向检查。通过后台 commandlet 导入、保存；未启动编辑器或游戏，未做游戏画面验收。

## 原因与修复

1. **机匣盖左侧长条**：Detail35 对生成外壳做 Solidify 时启用了 `use_even_offset`，部分极尖/凹角的等厚补偿失控。源盖内壁有 12 个越界顶点，最长三角边约 2.16 m，最远 X 达约 1.96 m。保留加厚前的原盖外形及新制内部细节，关闭无界角度补偿，按单位法线作有限厚度偏移，并限制锐角处厚度；从原始外皮重做内壁，没有直接把飞出的顶点压到一个盒子边界上。
2. **涂层不统一**：Detail35 精修涂层的线性底色为 `(0.021, 0.026, 0.031)`，明显亮于现用机匣。按当前机匣平整区的实际 UV 图集采样，统一到线性底色约 `(0.01096, 0.01444, 0.01764)`、粗糙度 `0.604`、金属度 `0.329`。内壁保持消光，少量滚轮/轴销保持较克制的裸金属反射。新材质为本枪专用副本/实例，旧材质保留。
3. **弹药箱发白**：ClothFeed33 绑定的 `M_LMG201_R30_Cloth` 来自静态弹箱，`used_with_skeletal_mesh=False` 且自动用途关闭。复制完整织物材质图到 `Repair36/Materials/M_LMG201_R36_Cloth`，明确开启骨骼用途并重新编译。保留原织物底色、法线、ORM 和织纹贴图，新旧弹箱与源供弹分件均重新绑定；湿润材质目录同步更新。
4. **附带发现并修复**：Detail35 机匣法线沿用了 R29 原图的切线方向，却丢失原导入设置中的绿通道翻转。已制作本枪专用法线副本，恢复正确导入方向，避免凹凸光照方向反转。

## 保存与检查证据

- 当前主体：`/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`。
- 前后瞄具的统一材质、`ClothFeed33/Parts/SK_LMG201_Cloth33_Props` 的布料绑定、`Accessories22/DA_LMG201_AttachmentWetMaterials` 均已保存。
- 原网格按 `LMG201_Cover` 骨骼归属只替换盖体；其他部位几何、手臂、供弹分件、动画和音频未重做。
- 从最终 UE 保存的完整 FBX 再读回，盖体越界顶点 **0**；最大三角边约 **0.103 m**，局部边界回到原盖体范围。
- 两个弹箱表面均有 **77,482** 个三角面，UV 有效；两套供弹状态均绑定新的骨骼布料材质。
- 当前主体 **27** 个有效材质槽均支持骨骼网格，未发现空材质、WorldGrid 或 DefaultMaterial。
- 这些是几何与资产绑定检查，不代表游戏内最终视觉效果已获认可。

## 文件与恢复

- `LMG201_R36_Lid.blend`、`Exports/SK_LMG201_R36_Cover.fbx`：修复后的可编辑盖体和分件。
- `Exports/SK_LMG201_R36_Installed.fbx`：从现用 UE 资产导出的完整装配。
- `source_geometry.json`：问题源网格的越界证据。
- `lid.json`、`saved_geometry_check.json`：修复源模型与 UE 保存后模型的检查结果。
- `capture.json`、`materials.json`、`saved_material_check.json`：修改前、制作回执和最终有效材质检查。
- `delivery.json`、`bindings.json`：实际保存回执与材质绑定。
- 旧版资产保留于 `/Game/Weapons/LMG201/Repair36/Previous/`；原始文件备份在 `Before/`。Detail35 及更早版本没有删除。

本轮应以 Repair36 为恢复/重导入口，不重跑已被本轮修正的旧 Detail35 整批生成或旧静态布料绑定脚本。

2026-09-29 归档更新：上述历史备份中的无外部引用 UE 包与失败 D35 输出已按用户要求移到本机 `trash/lmg201-rejected-20260929`，原路径与散列见工程 `Docs/Weapons/lmg201-publication-20260929/archive-manifest.json`。当前 Repair36 全装配、盖体源及所依赖的 Detail35 加厚前脚本、Work、贴图和母材质仍保留。历史 `source_geometry.py` 的失败网格读取需先按清单恢复旧 D35 输入；不要为重做诊断而恢复其运行绑定。
