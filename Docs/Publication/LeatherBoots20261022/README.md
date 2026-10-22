# 连续皮革长靴 TailoredV2：发布与本机恢复

本次公开长靴的制作脚本、装备搭配所需源码与外观配置、可选诊断工具，以及经验文档。游戏内物品仍是 `ue_leather_boots`（槽位 13），没有新建物品或修改属性、强化与库存规则。

上一版虽连接了鞋底，靴筒仍是独立封口的管状部分，脚踝出现相交断面。TailoredV2 将鞋底、沿条、鞋面、脚踝、靴筒、翻边、内衬连接成连续基础表面，保留原生 Jason 蒙皮，增加弧形裁片、活动褶、胡桃棕皮革与暗钢扣件。普通穿戴及法袍内穿版均已在本机保存。

## 提交范围

- `Tools/LeatherBootsTailored`：制作、PBR、导出、分批保存、独立距离 LOD、展示兼容、发布与按需检查工具。
- `Source/FPSGAME/Development/LeatherBoots*` 与 `MageOutfitWireAudit.cpp`：实际渲染权重导出和显式开启的长靴联机夹具。
- `FPSModularOutfitComponent`、`FPSOutfitStairVisibility`、`FPSOutfitSecondaryMotion` 及 `FPSMageRobeAuthoring` 的遮罩引脚函数：实际鞋型对应的裤装选取、上衣贴合回退、法袍内层覆盖及袖口惯性。未提交该 authoring 文件中另一项身体碰撞体改动。
- `Tools/BlueMageRobe/hem_*`：与 64 个布料采样点一致的内层位移与遮罩。保留原材质遮罩，避免另一只脚交叉时放开小腿约束。
- `modular_outfits.json`：长靴、野行上衣、蓝色法袍及 7 条现有裤子的外观配方。上衣依次采用实际裤网格匹配、物品匹配、内扎默认版；法袍对尚未单独制作内穿版的裤子有默认内层。这个回退不等同于未来任意模型都经过几何适配。
- `items.json`：仅长靴的 `desc`、`ue_icon`、`world_mesh`、`ue_equipment_icon_mesh`，保留其他字段。
- 依赖工具：`Tools/FieldRangerTop/run_asset.ps1`、`Tools/RangerLeatherPants/integration_{common,materials}.py`、`Tools/RangerCrouchFit/fit.py` 及 `author_tucked.py`；配置所指的 `Tools/PantsCompatibility/run.ps1` 与其采样、制作、保存、发布模块一并提交，供以后新增裤装生成精确配对。其他基础写入工具已在仓库中。

共享文件从当前 Git 索引制作候选，未用候选覆盖工作区。其他装备、数值、角色、界面及并行任务改动不在此提交内。

## 资产与依赖

当前 UE 根目录为 `/Game/Characters/ModularOutfit20260924/LeatherBootsUpgrade20261022/TailoredV2`：

| 用途 | 根目录下路径 |
| --- | --- |
| 普通穿戴 | `ue_leather_boots/Jason/SK_Jason_ue_leather_boots` |
| 法袍内穿 | `ue_leather_boots/Jason_RobeInner/SK_Jason_RobeInner_ue_leather_boots` |
| 仓库展示 | `Icons/SM_LeatherBoots_Display` |
| 世界掉落 | `Pickups/SM_LeatherBoots` |
| PBR 与法袍材质 | `Textures`、`Materials`、`RobeMaterials` |

图标纹理在 `/Game/ColdSteelData/Icons/LeatherBootsTailoredV2/ue_leather_boots`。旧物品实例的 `Item.Data` 可能保留历史路径，因此在本机原位更新了 BrownLeatherSet20261004 与 LeatherBootsUpgrade20261022 下的 4 个旧展示网格，并同步两个旧 PNG 路径；不靠重建实例改变其属性。具体路径和本机保存散列见 [evidence-summary.json](evidence-summary.json)。

按照仓库资产规则，UE 包、授权角色与扫描纹理、源模型、FBX、Blend、密集几何 JSON、姿态数据、存档、日志及 `trash` 都留本机。Git 拉取只恢复源代码和说明，不能直接恢复可运行的完整角色套装。恢复本机工程还需要：

1. `SourceAssets/LeatherBootsUpgrade20261022/TailoredV2` 当前制作目录及 `Content` 中上述资产。保留 `inputs.json`、`Authored`、`Textures`、`Exports`、`Review`、`Before` 和完成回执。
2. `SourceAssets/BrownLeatherSet20261004` 的原生角色输入和长靴参考图；`SourceAssets/HandEquipmentAppearance/Source/Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_*` 的合法本机扫描贴图。
3. 第一版目录中保留的 `Authored/ue_leather_boots/Jason.json`、`Textures/*.png`、`saved_assets.json`。现版仍读取它们作制作输入、对比和历史路径恢复，故未归档。
4. 当前角色与服装资产包：Jason 原生骨架、`modular_outfits.json` 中所列上衣／裤装／法袍版本，以及 `player_body.json` 指向的原生动画。不能把别的角色骨架或旧配方当成等价输入。
5. 裤装配对工具读取 `SourceAssets/RangerCrouchFit20261021/inputs.json` 指向的上衣源几何、皮裤 RealisticCutV3 的作者数据和 Integration20261022 已接入回执。若明确要求再次进行姿态／搭配检查，还需前者的姿态文件、`SourceAssets/PantsCompatibility20261022/inventory.json` 与关联几何。这些密集本机数据不公开。

工具使用本工作站路径：`D:/FPS3D/FPSGAME`、UE 5.8 和本机 Blender/Python 环境；迁机先调整根路径和工具路径。Python 制作依赖包括 NumPy、SciPy、Pillow，Blender 脚本还依赖 `bpy` / `mathutils`。UE Python 运行在引擎内。

## 制作与修复入口

以下是恢复流程说明，本次 Git 整理没有执行引擎、渲染或联机测试。

1. 现版使用已冻结的 `inputs.json`。`prepare.py` 是从第一版切换时的一次性快照，当前已经发布，不要再次运行它覆盖快照。
2. `author.py`、`bake.py` 生成几何和贴图；`export_render.py` 输出可编辑模型、FBX 及预览。预览／检查脚本仅在用户要求对应交付时运行。既有分批保存／发布脚本读取本次已经完成的制作检查回执；源几何改变后不能拿旧散列冒充新结果。
3. `Tools/FieldRangerTop/run_asset.ps1 -Script ../LeatherBootsTailored/save_batch.py -ReceiptName <新的名称>` 使用已有批次互斥。每批保存一个穿戴或展示资产，按完成回执续跑；遇到 PIE 保留现场，结束试玩后再保存，不另起编辑器覆盖。
4. `save_batch.py` 调用 `distance_lods.apply`，将长靴独立策略同时写入 LOD 设置和 source models。重新导入时同时核对策略版本与源模型散列，防止退回全精度距离档。
5. `repair_legacy_displays.py` 处理旧实例展示路径；`publish.py` 仅写长靴外观字段和法袍映射。两者作用不同。
6. `repair_skeleton_curve_metadata.py` 用于已定位的无界面启动崩溃：加载当前原生动画，让骨架累计缺失曲线元数据并保存骨架包。本次新增 `mask_geo`，没有改骨骼和参考姿态。该工具不是所有启动错误的通用修复；已排除的 retarget source 删除尝试已恢复。
7. `read_distance_lods.py` 明确读 `RENDER_DATA`，结合 `ULeatherBootsAuditLibrary` 导出实际权重；`run_wire.ps1` 是显式请求联机检查时的入口，使用独立测试存档。它不会由普通游戏路径或本次整理自动运行。

## 既有结果与边界

2026-10-22 在本机完整工程中的结果（本次仅整理已有回执）：

- 两套穿戴的真实渲染 LOD 三角形数均为 **214,916 / 96,712 / 38,684**；LOD0 不变。
- LOD1 / LOD2 各 30 个离线姿态，最大表面误差约 **0.0381 / 0.0791 cm**，被采样接缝差为 0。这不能推导游戏帧率或所有姿态无穿模。
- 后台 Editor 构建已完成；骨架曲线修复后，真实 UDP 监听主机、客机及同档重连 **14/14** 项通过，每个 peer 设置 60 ms 延迟、3% 丢包。包含权威库存、复制装备、所选网格、绑定和旧共享掉落物实例数据。
- 成功运行记录保留于 `TailoredV2/Audit/Wire/20261022-161039`；最终汇总为 `Audit/completion_review.json`。
- 没有本轮整理后的重新构建／测试，也没有公开切片的独立干净检出构建、专用服务器、三个同时在线玩家、跨机打包、GPU 计时或游戏画面验收。历史本机构建包含工作区的其他改动，不能宣称公开源切片已独立验证。

## 废案归档与恢复

[archive-plan.json](archive-plan.json) 记录 **206 个文件、471,118,480 字节**的原路径、目标路径、SHA256、原因和替代项；[archive-receipt.json](archive-receipt.json) 记录执行结果。已逐文件移动到 `trash/leather-boots-retired-20261022/`，移动后散列一致，没有删除文件或移动 Content 包。

归档范围为第一版不再使用的输出／脚本、被排除的诊断尝试、失败或阻塞的旧网络运行、一次性预备目录及被结构化回执替代的制作日志。仍在使用的输入、兼容路径、最终成功记录和恢复备份保留。

在项目根目录执行以下命令，可按清单恢复本机归档；缺失、改动或目标冲突会停止，不覆盖现场：

```powershell
& ./Tools/Publication/archive_leather_boots_20261022.ps1 -Operation restore
```

## 技能沉淀

个人技能目录为主源；本次将授权维护的两份主题参考同步到仓库，并为建模、调试、手臂／服装、性能、存档／复制五个技能添加索引。

- [连续长靴与渲染 LOD](../../../skills/asset-model-workflow/references/continuous-boots-and-render-lods.md)：连续拓扑、权重接缝、距离策略、真实渲染读回和旧实例外观。
- [无界面动画曲线迁移](../../../skills/ue5-debug-validation/references/uncooked-animation-curve-migration.md)：真实堆栈定位、骨架持久化与无效诊断回退。
