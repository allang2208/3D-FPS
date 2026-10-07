# 苍龙附魔：V10 制作源

当前运行版本是 **V10**（2026-10-07 用户确认特效合格、斩击类判定延伸“成功”）：
- 龙爪：库中 Fab Dragon Claw 修复重绑 —— `ClawV10/author_fab_claw.py`、`ClawV10/install_fab_ue.py`；
- 能量条：屏幕空间 HUD —— `HudV10`。

合同、可复用做法和联机要点见 [苍龙现状与做法](../../skills/ue5-weapon-workflow/references/azure-dragon-pending.md)，逐版记录见 [V10 文档](../../Docs/Combat/enchant-azure-dragon-v10-20261006.md)，本轮整理见 [V10 整理发布](../../Docs/Combat/enchant-azure-dragon-v10-publication-20261007.md)。

## 目录

- `Original/Fisto.glb`、`fab-metadata.json`：用户选定的 CaptainHC [Fab Dragon Claw](https://www.fab.com/listings/2d436c6f-7d26-4a80-8469-884b97613e5a)，授权说明在 `Content/ThirdPartyNotices/AzureDragonClaw.txt`。
- `author_model.py` 生成 `AzureDragonClaw.blend` 与 `Export/T_AzureDragonNormal.png`；`finger_landmarks.py` 生成 `Export/finger-landmarks.json`。两者都是 Fab 爪制作的输入。
- `install_ue.py`：只导入共享法线图集 `T_AzureDragonNormal`，供 Fab 爪材质读取。
- `ClawV10/`：Fab 爪的作者、安装、HLSL 和构建入口，见其 README。
- `HudV10/`：能量条 HUD 的生成源、烘焙、材质 HLSL 和安装。
- `References/azure-dragon-energy-approved.png`：认可设计图。

## 恢复顺序

1. 在合法本机素材下按依赖顺序运行作者脚本：
   - Blender：`author_model.py`，然后 `ClawV10/author_fab_claw.py`；
   - Python：`finger_landmarks.py`（需在 `author_fab_claw.py` 之前）、`ClawV10/author_textures.py`、`ClawV10/author_scale_detail.py`、`HudV10/author_hud.py`。
2. 根目录 `run_install.ps1` 执行 `install_current_ue.py`，依次运行共享法线 → `ClawV10/install_textures_ue.py` → `HudV10/install_hud_ue.py` → `ClawV10/install_fab_ue.py`。有编辑器时走批次桥，否则用后台 commandlet。
3. 根目录 `run_build.ps1` 转到 `ClawV10/run_build.ps1`，执行后台原生构建。

## 废案与公开边界

- 2026-10-05：RigV2、EnergyV3／V6、ReferenceV7、CombatV4、DualClawV8 等归档在本机 `trash/azure-dragon-retired-20261005`。
- 2026-10-07：Coherent V9（作者源与 11 个 UE 包）、VisibilityV5、V9 共享爪材质及其 HLSL、V10.1 原创爪、余烬／旧爪痕材质、根目录 V9 转发脚本和旧安装日志，共 113 份（19 个 UE 包）归档在本机 `trash/azure-dragon-retired-20261007`。逐文件移动前后 SHA-256 相同，[清单](../../Docs/Publication/AzureDragon20261007/archive-manifest.json)记录原路径和替代物，可按原路径回迁。
- 公开 Git 只包含原创配方、HLSL、源码、说明和归档元数据。Fab 原模型及其派生网格／贴图、百炼生成源图、Blend／FBX、UE 包和机器回执都留在本机；源码仓库不是完整的可运行资产包。
