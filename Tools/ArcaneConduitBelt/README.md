# 星律导能腰带：精细模型 R1

依据 `SourceAssets/ArcaneConduitBelt20261025/ConceptR1/design-sheet.png` 制作。独立制作目录为 `SourceAssets/ArcaneConduitBelt20261025/ModelR1`；本阶段制作模型、原生绑定、PBR 与数值配方，不发布 UE 资产或物品目录。

## 制作与输出

- `prepare.py`：复制本工程已保存的男女 ST6 腰线与原生身体参考，冻结既有腰线采样、建模、权重及导出辅助方法。不会运行或覆盖其他腰带作者。
- `make_textures.py`：4K 靛蓝皮革，2K 收边、内衬、哑银、氧化银与旧黄铜。输出 BaseColor、OpenGL Normal、ORM、16 位 Height 与物理高度场 NPZ。
- `author.py`：分层双环星盘、真实环槽和穿带孔、独立刻度嵌线、凹嵌晶体及三点爪座、分段符文金属板、缝线、左髋中空符片匣与独立翻盖、右髋卷轴筒与双点固定环。
- `construction.py`、`native_geometry.py`、`surface_fields.py`：本任务冻结的基础方法，来源散列在 `ModelR1/Authored/source-provenance.json`。

输出位于 `ModelR1/Exports/`：

- `ArcaneConduitBelt_Jason_Editable.blend`、`ArcaneConduitBelt_Kaitlin_Editable.blend`：独立分件、修改器、打包贴图、原生骨架与默认隐藏的裤装参考。
- `SK_ArcaneConduitBelt_<身体>.fbx`、同名 `.glb`：完整细节蒙皮模型。
- `<身体>_NativeWeightedMesh.json`：UE 厘米坐标、原生骨骼及逐顶点权重、逐角 UV 和法线。
- `SM_ArcaneConduitBelt_Display.fbx`、同名 `.glb`：完整细节静态展示件，正面 -Y、上方 +Z。

皮革柔性腰围分别采样实际男女裤腰；晶体、扣具、金属板、匣与筒保持同样的物理尺寸，以各自锚点绑定。参考姿态适配范围是保存的 ST6 裤装；法袍和新增服装还需在接入时按实际外层包络派生，不把概念穿戴图当作已完成适配。

石英使用独立透射材质，符文使用低亮发光珐琅材质；GLB 保留相应材质扩展，UE 材质仍需正式接入时制作。没有自动减面或额外远景 LOD。实际几何统计由生产导出过程写入 `Authored/<身体>_production.json`，不代表帧率结论。

## 属性配方

见 `SourceAssets/ArcaneConduitBelt20261025/stats-proposal.json`。魔法冷却基础 -2.5%、每级 -0.5 个百分点，+15 为 -10%；法力消耗基础 -10%、每级 -1 个百分点，+15 为 -25%。腰带槽、3×2 格、零防御、+15 上限。符片匣与卷轴筒当前是外观附件，不增加物品格。

## 后台命令

```powershell
python Tools/ArcaneConduitBelt/prepare.py
python Tools/ArcaneConduitBelt/make_textures.py
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup -t 6 --python-exit-code 1 --python 'D:/FPS3D/FPSGAME/Tools/ArcaneConduitBelt/author.py' -- Jason Kaitlin
```

上述命令写入本批 R1；后续造型修订使用新版本目录保留交付母版。本阶段不启动 UE，不自动渲染、检查动画、测试服装组合或联机。

## 游戏接入状态（2026-10-25）

本页上方记录 ModelR1 的制作阶段。后续游戏接入已由 `Tools/CombatBeltsIntegration` 完成：男女穿戴、三级 LOD、PBR、正面物品图标、掉落网格、物品目录和 +15 强化属性已保存发布。Editor/Game 已后台构建。运行、服装动作组合及联机未测试；接入回执位于 `SourceAssets/CombatBeltsIntegration20261025/arcane`。

## 星律固定环修复（KeeperFixR2）

当前星律穿戴已切换到 KeeperFixR2，修复 3 个皮革固定环被重复变换到头顶的问题，男女全部 LOD、图标和掉落模型同步更新。源模型为 ModelR2；本页原 IntegrationR1 为历史记录。详情见 `Docs/Items/arcane-belt-keeper-fix-20261025.md`。未运行游戏/联机测试。

## Archived predecessor outputs

The pre-keeper-fix ModelR1 exports and old `CombatBeltsIntegration20261025/arcane` geometry/icon outputs are archived under `trash/backpacks-belts-retired-20261025/`. ModelR1 inputs, references and textures remain active dependencies. Current arcane geometry uses ModelR2; publish with the KeeperFixR2 wrappers. Historical receipts retain their original paths. See `Docs/Publication/BackpacksBelts20261025/retirement-manifest.json` for recovery.
