# 远界智能远征背包接入与夹层调整

后续用户反馈过宽及离背间隙后，模型与贴身配置已更新为 `SlimFitR2_20261024`（52×70 cm），见[细长比例与贴背修订](farreach-backpack-slim-fit-20261024.md)。下文保留首次接入记录及当时尺寸，容量合同仍有效。

用户于 2026-10-24 指定使用 `C:/Users/allan/Downloads/Meshy_AI_Titan_Pack_1024035624_texture.glb`。已在后台保存展示／穿戴包体、材质及 12 套背带，接入物品目录和男女角色配置，并导出正式正面 PNG。保存与本地接入回执为 `SourceAssets/FarreachBackpack20261024/MeshyFitR1/saved_assets.json`、`published.json`；没有执行游戏、动作、存档或联机测试。

## 容量合同

| 背包 | 主背包增加 | 独立夹层 | 自身占格 |
|---|---|---|---|
| 远界智能远征背包 `ue_farreach_backpack` | 4 行／72 格，装备后主包 18×8 | 12×6／72 格 | 4×4 |
| 开拓者战术背包 `ue_pathfinder_backpack` | 保持 3 行／54 格 | 由 12×6 调整为 10×6／60 格 | 保持 4×4 |

新背包容量依据用户修订，不再采用概念稿中的 14×6 夹层或 4×5 占格。

## 模型制作

- 原始 GLB 已复制到 `SourceAssets/FarreachBackpack20261024/Input/`，SHA-256 为 `d6484784095aff65a901e269ff5dd83e86e3e9ecb6b81869070ea7eae803841b`。
- 保留 151519 个原始顶点、193526 个三角面及颜色、金属粗糙度、法线贴图。按提供模型的原比例统一缩放为 60 cm 高；整体宽约 59.98 cm，空载深度约 50.49 cm（包括展开背带）。没有按概念图重新塑造外壳或非均匀压缩宽度。
- 用真实世界矩阵把顶点和法线烘到独立的规范显示源，外侧正面 −Y、顶部 +Z。显示源保留完整空载背包；穿戴源将空载肩腰带收整到贴背侧，再制作独立蒙皮背带。
- 共享高细节包体使用 Nanite；Jason／Kaitlin 各裸身与五件上衣，共 12 套贴身背带。肩高和包体倾角读取当前原生身体，不能直接复用开拓者的安装角。
- 输入复用已保存且包散列未变的身体／衣物捕获，包含各身体 22 个普通／靴型裤网格。新 ST6 裤型按其保存回执，从未变基底加上以单位变换追加的细节作者源恢复腰部表面，记录在 `BodyInputs/manifest.json`；没有改动其他任务的 ST6 资产。
- 背带材质使用独立深蓝灰织物实例，包体保留用户 GLB PBR。包体和缝接端沿已有有界惯性；图中电子面板与接口不自动产生额外游戏技能。

## 旧夹层迁移

沿用当前 `ColdSteelInventoryRules.cpp::MigrateBackpackLayout`：先按存档中的旧列数解读并校验格位，保留新网格仍放得下的原坐标，溢出物品依次放入新夹层空位、主背包、主仓库。只在完整候选布局有效时替换档案；无法容纳时保留原档。

本地读档及服务器接收客户端档案均已有共享迁移入口。此次不改 C++，不直接打开或改写玩家存档，也没有运行迁移验收。新容量在应用重启后按目录读取；旧实例在正常读档流程中更新容量字段。

## 接入链

`prepare_source.py` → `prepare_fit_inputs.py`（源变更时使用 `read_fit_r2.py` 实读）→ `author_r2.py` → `prepare_buffers.py` → `save_assets.py` → `publish.py` → `run_stage.ps1 -Stage export_icon`。

脚本位于 `Tools/FarreachBackpack/`，新资产目录为 `/Game/Characters/FarreachBackpack20261024/MeshyFitR1/`。`player_body.json` 通过字段事务分别接入男女角色的该物品；目录发布只新增远界定义并修改开拓者的三项夹层字段。Cook 根目录已登记。拾取使用新定义的 `world_mesh` 及现有物理根／库存事务，未改拾取代码。

正式 PNG 使用同一 UE 图标棚和显示源输出到 `Content/ColdSteelData/Icons/ue_farreach_backpack.png`。离线导出传入 `-NoTextureStreaming`，在没有游戏流送 tick 的 commandlet 中完整加载贴图；不改游戏流送配置。该步骤是图标制作，不是游戏验收；不创建真实玩家档案。

正式 PNG 已于 2026-10-24 12:37 导出并归档至 `MeshyFitR1/Icon/ue_catalog_front.png`，尺寸为 320×320，带透明背景。输出回执为 `Icon/exported.json`，生产日志 `export_icon-20261024-123710.log` 记录写出成功及 `failures=0`。

没有启动交互编辑器、没有 Git 提交或推送。源码、保存资产、本地接入和用户体验分别记录。
