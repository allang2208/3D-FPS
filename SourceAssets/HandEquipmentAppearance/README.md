# 手部装备表现作者源

正式入口为本目录。2026-09-12 用户接受：原色棕皮革手套向前臂延长 3 cm，开口约 4 mm 薄卷边效果，裸露前臂皮肤与炭灰布袖。保留 Manny 网格、UV、骨骼、动画与枪械接触。

完整操作和恢复边界见 [手部装备替换标准](../../Docs/Weapons/hand-equipment-appearance.md)，后续任务入口见 [手臂技能](../../skills/ue5-fps-arms-animation/SKILL.md)。本目录是材质作者管线；衣物/手套的物品数据、装备切换和存档系统仍需在相应功能任务中接入。

## 文件职责

| 文件 | 用途 |
| --- | --- |
| `inspect_regions.py`、`bake_glove_mask.py` | 根据原网格连通壳和手骨权重生成手套遮罩 |
| `inspect_leather.py`、`bake_leather_regions.py` | 物理纹理尺度、掌面/指腹分区、真实壳边缝线 |
| `export_surface.py`、`bake_forearm_regions.py` | 肘腕轴、原始 UV/平滑法线、皮肤与布袖区域 |
| `bake_rolled_edge.py` | 3 cm 袖口局部距离场及 DirectX 卷边法线 |
| `prepare_leather_source.py`、`source_maps.json` | 用户下载的 Fab 包、散列、法线方向与本地来源 |
| `import_leather_textures.py`、`build_sleeve.py`、`build_material.py` | 导入共用纹理，构建已接受的袖子和手套父材质 |
| `skin_sleeve.hlsl`、`rolled_cuff.hlsl` | 可编辑布料/皮肤与卷边表面代码 |
| `restore_assets.py`、`apply_standard.py` | 显式重建并恢复整个项目共用基线 |
| `verify_saved.py`、`audit_dependencies.py` | 重新加载数值、材质宿主与旧资产引用审计 |
| `validate_authoring.py` | 临时重烘焙，与已接受六张作者贴图逐字节对比；源 Blend 不变 |
| `run_preview.ps1 -Label <新名称>` | 2560×1440 DX12 实机验收与断言结果 |

`Source/` 是已许可的 Quixel 原包解压内容，`Preview/` 是用户接受的原始游戏截图。这两者、几何导出数据、贴图和 UE 二进制均不公开提交。Git 中的脚本需要本机原始手模及许可贴图才能完整复现；缺失时按恢复说明准备依赖。

`Evidence/accepted-20260912-*` 是整理前已接受版本的历史记录，不代表当前重新运行。后续整理验证单独记录在 `authoring_validation.json`、`verification_report.json` 和 `Docs/Weapons/hand-equipment-publication-20260912/`。
