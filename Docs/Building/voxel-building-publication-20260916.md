# 体素建造工作流发布 · 2026-09-16

本批发布 20 cm 体素建造这条线：建造工作流标准（放置规则、吸附与自由放置、金色轮廓、失败隔离）、放置构件（罗马柱／矮栏杆罗马柱）、大理石体素与活动调色板接入、承重数值复核，以及配套工具和技能沉淀。用户明确同意推送到 `https://github.com/allang2208/3D-FPS.git` 的 `main`。

## 提交

| 提交 | 内容 |
| --- | --- |
| `5716617` Add voxel build workflow, prefabs and build-failure isolation | `Source/FPSGAME/Building/`（含 `VoxelBuildPrefabActor.*`、`VoxelBuildWorldPrefab.cpp`、`VoxelJointStrength.h` 四个新文件）、`Source/FPSGAME/UI/ColdSteelUIStyle.h`（浮窗共用令牌）、`Tools/Building/` 探针与审计工具、`Docs/Building/voxel-*.md`、`Docs/UI/voxel-build-panel-plan-20260916.md`、`AGENTS.md` 路由行、`SourceAssets/RomanColumn20260915/` 作者脚本与案例 README，以及 6 个退役文件删除 |
| `51909c0` Sink voxel placement and hot-patch boundaries into UE5 skills | `skills/ue5-world-interaction`、`skills/ue5-debug-validation` 的新引用与症状表；个人技能同步 |
| 本次记录提交 | 本发布记录与归档清单 |

推送后 `git ls-remote origin refs/heads/main` 回读为 `51909c0ca033e76bcb1046126ef9d78fb519d6b7`，与本地 HEAD 一致；普通推送（非强制），推送前 `origin/main..HEAD` 为空。最终提交文件清单以 Git commit 为准。

## 验证与未验证

- 已做：本批代码在会话内用 `LiveCoding.CompileSync` 热补丁 3 次（均 `Live coding succeeded`），并在关闭编辑器后按用户要求做了一次全量编译——`Result: Succeeded`，15 个 action，其中包含 `VoxelBuildPalette.cpp`、`VoxelBuildComponent.cpp`、`VoxelBuildWorld.cpp`、`VoxelBuildWorldStructure.cpp`；`Binaries/Win64/UnrealEditor-FPSGAME.dll` 落盘时间 19:12:03。
- 只做了发布范围检查：远端与授权 URL、提交范围、暂存差异、`git diff --cached --check`、文件大小、敏感信息、公开资源边界、归档散列、技能与文档链接。
- **未验证**（按用户 2026-09-12 全局规则默认不主动测试）：没有进游戏点选放置、没有截图、没有重跑离线探针。轮廓清理、1 m 吊空墙面、建造失败只影响新增部分这三项行为，以及强度翻倍后的手感，均由用户实测判定。

## 本机内容依赖

- `Content/` 按 `.gitignore` 全部保持本机：活动调色板 `Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset`（大理石为 `bOverridePhysics` 条目）、`M_VoxelAimEdge`、`M_Voxel_PlacementPreview`、体素材质与构件网格都不随本批发布，恢复方式见 [资源恢复](../AssetSetup.md)。
- 初版调色板 `Content/Building/Voxels/DA_VoxelBuildPalette.uasset` 与父目录初版材质／网格按案例 README 第 229 行的结论保持原样，未移动。
- 建造模式灵敏度钩子（`fps.Building.LookSensitivity`，在 `AFPSGAMECharacter::LookSensitivityScale()` 内）位于 `Source/FPSGAME/FPSGAMECharacter.cpp`。该文件同一时间还有其他并行会话的武器／手臂改动，按 WORKFLOW §7「精确暂存、保留并行修改」**未随本批提交**，所以仓库里的建造模式仍是默认灵敏度；钩子实现记录在工作流文档 §3.4。
- 其余 `Source/`、`SourceAssets/`、`Docs/` 下的并行未提交修改（1010 条）全部保留在工作区，未夹带。

## 废案归档

20 个文件按 WORKFLOW §4 移入 `trash/RomanColumn20260915/`：14 个引擎／UBT 运行日志、5 个 UBT JSON 日志、1 组已被正式实现取代的面板模拟图。移动前后逐条核对 SHA-256，清单见 [归档清单](voxel-build-archive-20260916.json)（`trash/` 本身不提交）。

仍被文档或案例 README 引用的文件保持原位：`register_palette_prefabs.py`、`apply_stone_material_and_palette.py`、`wrap.log`、`rebuild_column_v1_style.py`、各 `build_*`／`fix_*`／`place_*`／`verify_*` 作者脚本，以及 `Tools/Building/` 下的探针与审计工具——依据是 §4「不要凭旧日期或候选名判断废案」。

## SKILL 沉淀

- [体素放置交互](../../skills/ue5-world-interaction/references/fpsgame-voxel-placement.md)：状态机、幽灵与高亮清理、实例化静态网格材质标记、每帧与节流的分工、吸附与自由放置、向上建造规则、症状对照表。
- [Live Coding 与全量编译边界](../../skills/ue5-debug-validation/references/live-coding-vs-full-build.md)：热补丁能带什么、带资产 USTRUCT 的坑、模块重载复位文件级 static、证据顺序。
- 两份技能都已同步到个人技能目录（复制后 SHA-256 一致）。数值规范继续在 [体素建造工作流](voxel-build-workflow.md) 维护，UI 令牌规范在冷钢 UI 正式规则中维护。
