# 裸手表面 V8（2026-10-16）

记录：`Docs/Characters/bare-surface-v8-20261016.md`。

| 文件 | 用途 |
| --- | --- |
| `audit_mesh.py` / `locate_defects.py` / `fold_check.py` | 离线审计：退化面、开口、非流形、绕序翻折、法线、UV／纹素密度 |
| `generic_fix.py` | 不依赖对应关系的局部修复：微小边合并、翻折区重新三角化、法线替换 |
| `apply_offline.py` | 写入母版与 20 份 Authored（备份在 `Before/`） |
| `blend_fix.py` | Blender 后台修复可编辑源：`blender -b --factory-startup --python blend_fix.py -- <blend...>` |
| `snapshot_ue.py` | commandlet 只读快照：按配置和皮肤父材质引用找出网格，输出 `Snapshots/`、`inventory.json` |
| `plan_ue.py` | 审计快照并生成修复方案，结果写入 `ue_findings.json`、`ue_plans.json`；排除第三人称身体皮肤 |
| `install_fix.py` / `install_pilot.py` / `install_all.py` | 写回 UE 网格并读回到 `Final/`，回执在 `Installed/` |
| `check_final.py` | 读回结果与修复前对比，结果写入 `final_checks.json` |
| `skin_recipe.py` / `material_upgrade.py` / `read_materials.py` | 共享皮肤父材质升级与读回 |
| `run_ue.ps1` | commandlet 包装；UE 打开时拒绝执行 |
| `read_import_sources.py` | 读取 UE 网格的导入源，输出 `import_sources.json`、`import_source_files.json` |
| `fbx_bin.py` / `fbx_fix.py` | 无损 FBX 二进制读写，以及骨骼网格皮肤的就地修复（`--dry` 只出报告）；回执 `fbx_receipt.json` |
| `blend_fix.py --check` | 只检查不写，回执在 `BlendChecks/` |

结果：
- 126 份网格已保存（含 2 份 Super90 候选网格），读回无问题；
- 5 个共享父材质已升级；
- 已修复 37 份 FBX 和 70 个武器自有 Blend；
- 未运行游戏，视觉由用户确认。
