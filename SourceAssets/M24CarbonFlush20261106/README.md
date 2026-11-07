# 玄脊碳纤维后托直接拼接 — 2026-11-06

用户要求取消突兀衔接，改为直接贴合拼接。本轮使用用户选定的 `Meshy_AI_Carbon_Stock_1105135808_texture.glb` 既有托身与材质。

## 制作

- 撤去 R2 的独立金属连接颈；碳托裁切至原局部 Y=-85 mm，整体向机匣前移 55.5 mm，安装接缝统一为 Y=-29.5 mm。
- 只在前端 25 mm 碳壳范围内按各自机匣的真实边界适配。端面细分到共同边界后焊接，接缝属于同一网格，没有新增外露连接件。
- 源托身切口有外壳和内腔两圈。外壳与机匣共边；内腔前缘后收 1.5 mm 并单独封口。
- 抵肩面随托身前移，由 Y=-361.599 mm 改为 Y=-306.099 mm。当前改动缩短了装配总长。
- 沿用源碳纤维底色、粗糙度/金属度及 UE 版法线贴图，保留面角 UV。局部形变同步转换作者法线，共边继承机匣法线，导入后固化切线。
- Native 与 Advanced 各有独立接面及机匣材质。

## 文件与接入

- `flush.py`：本次 Blender 制作脚本。
- `M24_Carbon_DirectFlush.blend`：可编辑源。
- `Exports/SM_M24_CarbonSpine_{Native,Advanced}.fbx`：游戏导入文件。
- `construction.json`：制作参数。
- `current.json`：本轮接入前两个目标包的来源、哈希和材质槽。
- `Before/`：接入脚本保存的原包副本。
- `publish.py`：通过已有批次互斥接入并保存两个现用网格，制作三档 LOD。
- `saved.json`：只有 `complete: true` 才表示两个正式资产均已保存。

正式资产路径：`/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Native` 与 `SM_M24_CarbonSpine_Advanced`。

本轮不启动游戏，不生成验收渲染；实际观感、抵肩位置和动作配合交由用户测试。
