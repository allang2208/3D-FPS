# 铁砧实物参考修订 V3

用户指出 V2 砧角和砧面错位、表面过度光滑。本次先参考真实 London pattern 铁砧，再重建几何及材质。

用户在厘米缩放修复后认可模型，随后要求材质更旧、更暗。当前表面为 **AgedIron4**：保留几何及尺寸，只更新原钢材质。使用现有金属扫描纹理把原本整片的亮砧面分成不规则氧化层与少量磨损区；铁体亮度系数 0.42，旧钢面 0.34，粗糙度提高至约 0.60–0.93，降低氧化区反射并保留灰褐锈迹和凹坑。`apply_aged_material.py` 只保存材质，不重新导入网格；先前亮材质留作 `M_AnvilReferenceSteel_BrightV3Archive`。`aged_material_blender.py` 同步可编辑源的表面，原 FBX 和模型尺寸不变。未运行游戏、截图或渲染，外观由用户测试。

- 砧角到台阶、工作面及砧尾由共享截面生成；与承力砧身做布尔并集。取消独立圆锥端盖、薄钢板和台阶方块的重叠装配。
- 工作面宽 16.2 cm，X=10.38–52.7 cm，Z=91 cm；底脚 Z=62 cm，与原木砧座一致。保留整体设施坐标、占格、接收架和互动挂点。
- 砧身保留较平的承力侧面、低底脚和小倒角，底部穿拱形成四脚；固定压片变薄。
- 材质复用项目已导入的 Normandy `T_MetalRust_00A` 衍生高炉铁材五张贴图，通过本砧专用材质调成深色氧化铁。砧面为原创 2K 锤痕、划痕和轻微氧化 PBR；顶面、砧角和底脚边缘按 `AnvilWear` 顶点色磨亮，砧角根部无独立材质切缝。UV 对应 50 cm 纹理幅宽。
- 复用纹理保留项目原有资产授权，不修改高炉材质或其源资产；参考照片不投影到模型、不打包进游戏。

`rebuild_anvil.py` 读取初版总装，只替换铁砧；`Authored/CastingStation_AnvilReference_Source.blend` 为本版可编辑源。整台 42,504 三角形，独立铁砧 15,428 三角形，UE 保留 Nanite 和原有碰撞方式。

`install.py` 将总装及独立铁砧写入原 `/Game/Props/CastingStation20260926/` 路径，新材质/贴图放在子目录 `AnvilReferenceV3`。父目录 `install_station.py` 优先安装本版。旧版源文件保留。实际保存记录见 `Receipts/`。

用户随后要求核对缩放，发现首次 V3 导入的总装实际只有 1.8 × 1.2 × 1 cm，独立铁砧为 0.76 × 0.319 × 0.29 cm，而实例和 LOD BuildScale 均为 1。FBX 原先把米制换算保留在单位元数据中，重导入后的独立铁砧还保留 `convert_scene_unit=False`。现已将导出改为 `FBX_SCALE_NONE`，将厘米换算写入 FBX 变换，并明确保留导入比例 1。重新导入保存时读回：总装 180 × 120 × 100 cm，铁砧（含压片）76 × 31.9 × 29 cm。导入入口会对照源几何厘米尺寸，防止此单位错误再次落盘。记录：`Saved/anvil-reference-v3-centimetre-import-2.txt`。为重导入结束了当时正在运行的 PIE，编辑器保持打开；未重新启动游戏。

最初导入因 UE `ImportedMaterialSlotName` 为只读而中断；随后保留导入器的 section/slot 对应关系完成保存，旧铁砧槽也统一绑定新钢材质。`resume_interrupted_import.py` 是这次中断的续写记录，日后使用常规 `install.py`。

本次完成建模、贴图制作、导入、必要材质编译和保存；没有启动游戏、运行测试或生成验收渲染。外观由用户自行测试。

参考来源及许可见 [References/README.md](References/README.md)。
