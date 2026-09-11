# 消耗品写实三视图与 5080 模型

生命药水、魔法药水、5.56 弹药盒、7.62 弹药盒。四款参考均按用户追加要求统一为写实材质；药瓶保留原有辨识轮廓，弹药盒保留绿/红配色。三视图为正面、右侧、背面，隐藏面属于依据现有图标进行的设计重建。

## 文件

每款 `*_three_views.png` 是最终写实参考图；`*_candidate_v01_00001_.glb` 是实际远程 RTX 5080 / TRELLIS.2 原始输出；`*_candidate_v02.glb` 是整理候选，`*_editable.blend` 是其可编辑文件。`*_refined_front/back/beauty.png` 是 Blender 实际模型渲染；`collection_preview.png` 是四款模型合照。V02 已于 2026-09-10 接入 UE 地面掉落物，接入记录见 `Docs/UI/consumable-world-models-20260910.md`。

| 物品 | 三视图 | 整理模型 | 可编辑文件 |
|---|---|---|---|
| 生命药水 | [PNG](hp_potion_three_views.png) | [GLB](hp_potion_candidate_v02.glb) | [Blend](hp_potion_editable.blend) |
| 魔法药水 | [PNG](mp_potion_three_views.png) | [GLB](mp_potion_candidate_v02.glb) | [Blend](mp_potion_editable.blend) |
| 5.56 弹药盒 | [PNG](ammo_556_three_views.png) | [GLB](ammo_556_candidate_v02.glb) | [Blend](ammo_556_editable.blend) |
| 7.62 弹药盒 | [PNG](ammo_762_three_views.png) | [GLB](ammo_762_candidate_v02.glb) | [Blend](ammo_762_editable.blend) |

## 实际生成与后处理边界

参考来源为当前 `Content/ColdSteelData/Icons/` 同名图标。三视图使用内置 imagegen 生成，提示词见 `prompts.json`。旧风格药水草稿已标记为 `*_stylized_draft.png`，不作最终输入。5.56 背视图经过一次遮挡关系修正。

已实测远程 `192.168.3.142` 为 RTX 5080 16GB。实际成功任务使用其现有 ComfyUI 8189 服务，经 SSH 本地 18189 转发：`microsoft/TRELLIS.2-4B`、512 管线、正/右/背三个独立输入、16 次形状采样、12 次纹理采样、2K 纹理、目标 20000 面。图片通过 ComfyUI ImageCrop 节点分开，不把整张三视图当作一个物体输入。工作流、回执及完成历史保存在各物品同名 JSON。

- 生命药水：`c4278a9a-2aa0-4bb4-9ec0-046f29e3b2c4`
- 魔法药水：`ae3f859c-03e9-493d-9a08-8b6b54f023a4`
- 5.56：`a196128e-95a4-49ab-903d-3c4c90726df7`
- 7.62：`1e27c905-f7d7-4664-9dcc-4bcbbfb8057e`

药水原始网格存在背景底板、反光误生几何以及玻璃发黑问题。V02 是参考生成轮廓和三视图重新构造的规则瓶体拓扑，并拆分为真实厚度玻璃、独立封闭药液、瓶塞和银色螺旋；不能称作未经处理的 5080 直接输出。可复现脚本为 `retopo_potions.py`，瓶高约 18 厘米。

弹药盒 V02 保留 5080 生成的主要网格与 2K 材质，补建正面纸板，将原始参考直接作为 UV 输入修正口径文字。脚本为 `refine_models.py`，未使用程序重绘参考图。盒内弹药轮廓仍有生成导致的软化，部分盒边/侧面材质仍需要近景精修；目前属于可审查的模型候选，不是已通过游戏近景验收的正式资产。

## 验证与运行记录

四次最终建模历史均为 `success`，GLB 已实际下载并通过 Blender 导入。网格面数、UV、材质和纹理尺寸见 `*_mesh_report.json` 与 `*_refined_mesh_report.json`；渲染脚本为 `render_models.py`、`render_collection.py`。

最初 8188 的旧风格测试任务在自动下载背景分割模型时等待，已发送针对该任务的中断请求；随后重启该服务的操作被自动审批策略拦截，未执行。当前成功任务使用独立的现有 8189 服务。另一次 RGB 预处理缺少 alpha 的失败工作流已保留为 `ammo_762_rgb_error_*`；最终流程使用独立视图直接建模。

生成阶段未更改物品定义、背包存档或原图标；随后已授权并完成地面物品模型接入。未公开提交未审查的素材二进制。

旧风格药水草图已归档到 `trash/non-weapon-items-20260911/SourceAssets/Consumables5080_20260910/`；取消回执保留作为诊断证据。归档清单见 `Docs/Art/non-weapon-items-archive-20260911.json`。
