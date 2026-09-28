# 主神空间地毯金属条与转角修订

用户已认可地毯 V2，本轮仅处理地面条饰排列、两侧轨道连接、交叉路口及转角。按用户要求完成几何范围的检查，不启动游戏或制作验收截图。

## 原因

从当前 UE 的 `SM_GodSpaceStructure` 导出实物检查，而非重建整个旧预览场景：

- 原 43 道横条只有 9 m 长，端点到左右侧轨内缘各差约 28 cm；横条实际使用白色大理石材质，与金属边轨分属不同材质。
- 主地毯宽 9.4 m，侧轨内边在 X=±4.78 m，离地毯边缘各有约 8 cm 空隙。
- 横向支路的边条与长轨整段交叉，未做路口收边，顶面比地毯高约 2–3 cm。
- 主通道和横向支路地毯顶面相差 2.15 cm，独立盒状边条没有衔接这一高差。

输入记录：`SourceAssets/GodSpaceLayout20260927/Integration/FloorTrim/inputs.json`、`geometry-before.json`。

## 调整

- 原 4 条独立长盒与 43 道横条替换为一个连通、封闭的条饰网格，横条端点与两侧轨道共享几何，转角也属于同一实体；不再用重叠盒子遮接缝。
- 侧轨缩为 7.5 cm、落在地毯边缘内；横条宽 1.8 cm。主通道改为 7 道关键位置标记，左右支路各 3 道，避开喷泉圆台和祭坛前的显露通道。
- 常规路段金属顶面比地毯高 1.5 mm，露出棱做 1.5 mm、两段倒角。十字路口保留原地毯高差，边轨在 50 cm 长度内连续过渡；此过渡段的金属相对低侧地毯会逐渐升高，不把它记作全段均高出 1.5 mm。
- 新增专用 `M_GodSpaceFloorSatinBrass`，较柔和的香槟金属色、0.44 基础粗糙度及随像素尺度消退的轻微拉丝粗糙度变化；不修改亭子与圆形徽章的共享金属材质。
- 已认可的地毯材质、纤维视差参数与几何保持原样。

## 制作与检查记录

制作入口：`Integration/refine_floor_trim.py`；可编辑源：`FloorTrim/Structure_TrimV2.blend`；导出：`FloorTrim/SM_GodSpaceStructure_TrimV2.fbx`。原始 UE 导出和修改前 Blender 文件均保留。

针对本轮接缝的几何检查：新条饰倒角后为 1 个连通分量、0 条非流形边；修改前后地毯顶点位置一致。当前导出总计 8404 个三角形，修改前 5396；增加 1 个材质槽，无新增 Actor、纹理或 Tick。上述为几何与设计成本，不是运行帧率测量。

独立接入入口：`Integration/install_floor_trim.py`。后续 `export_accepted_layout.py` 与 `import_assets.py` 已接入此局部修订，防止重导恢复旧横条。

已通过现有编辑器批次完成网格重导、四个材质槽绑定与资产保存；保存结果见 `FloorTrim/install.json`，`complete=true`，保存后为 8404 个三角形。保留原有复杂网格碰撞、Nanite 设置与地毯 UV 密度；未保存或修改关卡布局。

原结构资产备份：`trash/godspace-floor-trim-20260928/141956/SM_GodSpaceStructure.uasset`。保存后的网格 SHA-256：`35e1f25998bcab8eb1b3bcaae2e28e01ae325ba45617450826f8f94ec8051d34`。

未重新启动游戏，未进行运行时视觉验收；由用户进入游戏确认观感。
