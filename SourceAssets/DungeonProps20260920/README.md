> 2026-09-22 废案：本批 5080 生成物品已被用户整批否决；产物移至 `trash/dungeon-5080-rejected-20260922`，禁止作为已认可模型恢复。见 `Docs/Gameplay/dungeon-5080-retirement-20260922.md`。下文为历史记录。

# 地牢 P0 道具：女神像 / 恶魔像 / 冒险者遗物 / 骨堆 / 破损木箱（2026-09-20）

按 [通用游戏模型生成工作流](../../skills/asset-model-workflow/SKILL.md) 的 5080/TRELLIS.2 路线制作。为 [地牢迁移实施方案](../../Docs/Gameplay/dungeon-migration-plan-20260920.md) 与 [单房美术资产清单](../../Docs/Gameplay/dungeon-room-asset-list-20260920.md) 的 P0 清单提供候选模型。

## 范围与分流

本批只做 **雕塑/有机类道具**（事件道具与装饰），共 5 件：

| id | 名称 | 清单对应 | 用途 |
| --- | --- | --- | --- |
| `goddess_statue` | 古老女神像 | F2 | 事件①增益/治疗 |
| `demon_statue` | 恶魔雕像 | F3 | 事件⑤交易 |
| `supply_pile` | 冒险者遗物 | F4 | 事件③情报/补给 |
| `bone_pile` | 骨堆 | E4 | 装饰散件 |
| `broken_crate` | 破损木箱 | E2 | 装饰散件 |

**不进本批**：结构模块（墙/地板/天花板/楼梯/门框等 A/B/C 类）与其余道具。按工作流规则，精密结构件走 Vibe3D/本地 Blender 保尺寸与拼接面，不用 5080 生成网格。本批不做地牢整体、不做材质替换、不做 UE 接入。

## 来源

- 三视图参考由 5080 FLUX.2 Dev（`flux2_dev_fp8mixed.safetensors` + `mistral_3_small_flux2_fp4_mixed` 编码器）文生图生成，1536×1024，24 步，euler。
- `goddess_statue`、`demon_statue`、`supply_pile` 有原项目事件插画作设计参照（`Reference/Source/`，来自 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/scenes/dungeon-events/`）；`bone_pile`、`broken_crate` 参照原项目地牢道具贴图与清单描述，无插画。
- 全部提示词、种子在 `props.json`，逐件任务记录在各自目录。

## 目录结构

```
DungeonProps20260920/
├── props.json                  # 清单、提示词、种子
├── Scripts/reference.py        # FLUX.2 三视图参考（gen-refs / fetch-refs）
├── Scripts/mesh.py             # TRELLIS.2 多视图网格（prepare / submit / fetch）
├── Reference/Source/           # 原项目插画参照（女神/恶魔/遗物 + 骨道具贴图）
├── _view_*.jpg                 # 缩略读图副本（非正式产物）
└── <prop>/
    ├── three_views.png         # FLUX.2 三视图参考（正式参考）
    ├── ref_workflow.json       # 参考生成工作流
    ├── ref_receipt.json        # 提交回执
    ├── ref_history.json        # 执行历史
    ├── crops.json              # 三视图裁切框
    ├── upload.json             # 上传回执
    ├── mesh_workflow.json      # TRELLIS 工作流
    ├── mesh_receipt.json       # 提交回执
    ├── mesh_history.json       # 执行历史
    ├── raw_00001_.glb          # 原始几何（未纹理化大师版）
    └── textured_master_00001_.glb  # 带纹理母版
```

## 生成参数

TRELLIS.2-4B、三视图（front/left/back）、`1024_cascade`、结构分辨率 64、结构/形状/纹理 16/32/24 步、4K 贴图、50 万面母版导出目标、关闭 `fill_holes` 与 `keep_only_shell`。与工程既有案例（后握把、护手等）同一档位。

## 运行入口

```powershell
# 三视图参考
python Scripts/reference.py gen-refs
python Scripts/reference.py fetch-refs

# 网格
python Scripts/mesh.py prepare
python Scripts/mesh.py submit
python Scripts/mesh.py fetch
```

服务：`http://192.168.3.142:8188`（RTX 5080）。脚本不回退、不重抽种子；失败需显式处置。

## 交付状态

- 三视图参考：5/5 完成。
- TRELLIS.2 网格：已提交，见各 `mesh_receipt.json` 与 `mesh_history.json`。
- **未做**：几何检查、减面、UV、PBR 烘焙、UE 导入、碰撞、摆放接入、实机验收。生成 GLB 是候选母版，不等于可直接进游戏的资产。

## 已知边界

- FLUX.2 三视图的"不可见侧"是模型推断，不是精确还原；侧视图与背视图只用于 TRELLIS 的空间约束。
- TRELLIS 生成曲面在规则平面与精确棱线（如木箱板缝、方底座）上会偏软；若入选，规则几何部分按既有流程本地重建，不直接采用生成面。
- 未取得原项目事件插画的再分发授权，`Reference/Source/` 与本批产物留本机，不进公开仓库。