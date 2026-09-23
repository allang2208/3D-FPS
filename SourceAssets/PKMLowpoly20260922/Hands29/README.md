# PKM 手臂贴图通道修正

2026-09-23。用户报告 PKM 手部全黑，与其它武器的共用手部外观不一致。

## 诊断

- 当前 PKM、M4、QBZ191 和 ASH12 均引用 `/Game/Weapons/M4InfimaV3/MI_Manny_01`、`MI_Manny_02`；这些路径虽然较早，仍是现用共用实例。父材质分别为炭灰布袖与 3 cm 袖口棕皮革手套/皮肤材质。没有发现 PKM 独用旧黑色材质。
- `HandleFinish27/PKM_HandleFinish_Editable.blend` 的手臂有效 UV 名为 `DiffuseUV`。枪身多数部件为 `PKM_QBZ_SurfaceUV`，部分木制部件为 `UVMap`。
- 原合并导出按 UV 名称生成不同通道，手臂的 113406 个面角在 UV0 全为 `(0,0)`，有效坐标位于 UV1。共用手部材质采样 TexCoord0，因而皮肤/皮革/衣袖分区和颜色采样错误。详见 `source_diagnosis.json` 与 `asset_diagnosis.json`。

## 修改

- `../Belt08/mesh_export.py` 在各导出副本合并前，把各部件主贴图 UV 映射为共同的第 0 通道，附加通道依次保留。原坐标数值不重展、不重打包，原 Blend 不改写。
- `export_hands.py` 从当前 HandleFinish27 枪体导出修正版，保留提把紧固件、机匣、弹链和活动件的几何/权重/骨骼。
- `import_hands.py` 原位替换 `Accessories14/SK_PKM_Manny_Modular`；继续使用原 PKM skeleton，禁止参考姿态更新及动画/材质/贴图导入，按 imported slot identity 恢复材质和运行时分段名称。保存目标网格与其 skeleton。
- `BeforeImport/` 保存替换前的两个目标资产。材质及动画不覆盖；后续使用共用导出器时沿用修正。

## 交付与复现

`export_hands.py` 用 Blender 后台运行。`import_hands.py` 在没有 UE 编辑器时可通过 Python commandlet 后台执行；已有编辑器时只能走项目 MCP 批次互斥桥，并要求 PIE 已停止、目标资产无未保存修改。

已通过后台 Python commandlet 导入并保存正式 PKM 网格与其 skeleton，进程退出 0；记录为 `import_receipt.json`、`import_background.log`。第一次编辑器桥调用时编辑器已关闭，未开始导入，随后改为后台完成。

`corrected_uv_readback.json` 记录修正版 FBX 的手臂 113406 个面角均在 UV0 保留有效坐标，与源 UV 范围一致。本轮没有 C++ 修改，无需常规原生编译。没有进行游戏测试、截图或渲染；这次诊断与修复不代表实机视觉验收。
