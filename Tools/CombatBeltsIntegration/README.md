# 破阵与星律腰带接入

制作源：`SourceAssets/MeleeCombatBelt20261025/ModelR1`、`SourceAssets/ArcaneConduitBelt20261025/ModelR2`（Inputs／Textures 仍取 ModelR1）。本入口读取已完成的可编辑模型，不重写母版。

- `prepare_delivery.py`：Blender 后台生成男女原生绑定网格、完整 LOD0、55%/22% 远景 LOD，以及用于物品栏的正面扣具图标。图标是游戏资产生产，不运行验收渲染。
- `geometry_delivery.py`：修复导入日志实际报告的退化倒角/缝线 UV 与重复三角形。保留有效 UV、位置、法线及骨骼权重；只移除零面积面与完全重复面，再从修复后的网格派生远景 LOD 和正式图标。
- `save_assets.py`：在独立 `IntegrationR1` 目录保存 PBR、原生 SkeletalMesh、静态掉落网格、展示网格与 UI 纹理。法线按 OpenGL 绿色通道翻转，ORM 按 AO/粗糙度/金属度连接；紫晶使用实时薄透射近似，符文独立低亮发光。
- `run_asset.ps1`：复用项目命名互斥；已有编辑器时走现有桥，否则用 NullRHI commandlet。不会启动交互编辑器或游戏。
- `publish.py`：在资产实际保存后，按两个物品 ID 合并 `items.json`、`modular_outfits.json`，复制正式 PNG。保留其他条目与并行修改；保持腰带槽 10 和既有异步换装、拾取、存档及联机事务。

所有输出与执行回执位于 `SourceAssets/CombatBeltsIntegration20261025`。制作输入是男女原生身体和已保存 ST6 裤腰；它不是任意服装组合或动作无穿模的验收结论。新体型、厚外套及异形裤腰需按实际外层几何派生。

破阵的后台执行顺序：Blender `prepare_delivery.py` → `run_asset.ps1` → Python `publish.py` → `Tools/WorkwearSet/build.ps1 -ReceiptRoot SourceAssets/CombatBeltsIntegration20261025/Build`。中断续接先使用本轮保存记录，不重复生成已完成母版。

本次只生产两张最终物品图标，不启动游戏、联机、回归或验收。

## Archived predecessor outputs

The pre-keeper-fix ModelR1 exports and old `CombatBeltsIntegration20261025/arcane` geometry/icon outputs are archived under `trash/backpacks-belts-retired-20261025/`. ModelR1 inputs, references and textures remain active dependencies. Current arcane geometry uses ModelR2; publish with the KeeperFixR2 wrappers. Historical receipts retain their original paths. See `Docs/Publication/BackpacksBelts20261025/retirement-manifest.json` for recovery.

星律当前入口：`keeper_fix.py` 生成 ModelR2 → `prepare_arcane_keeper_fix.py` → `save_arcane_keeper_fix.py` → `publish_arcane_keeper_fix.py`。使用已有互斥桥／后台包装保存；本段表示生产顺序，不授权自动重跑或验收。旧 IntegrationR1 回执仅用于追溯。
