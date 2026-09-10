# 背包与世界交互：归档及技能沉淀（2026-09-11）

按根目录 `WORKFLOW.md` 第 4、6、7、8 节整理本任务产生的临时文件，发布目录为 `D:/FPS3D/FPSGAME`，远端为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。

## 已归档

18 个文件、238953 字节移至本机 `trash/inventory-world-interaction-20260911/`，保留原 `Saved/` 子路径：

- 四个已完成用途且依赖旧 HEAD 的暂存脚本：`stage_inventory_drag.py`、`stage_world_interaction.py`、`stage_drop_hitch.py`、`stage_drop_review.py`。
- `WorldInteractionBefore` 中 6 个修复前源码快照。
- `DropHitchBefore` 中 8 个修复前源码快照。

逐文件的原路径、归档路径、字节数、SHA-256、归档原因及替代物见[归档清单](inventory-world-cleanup-20260911.json)。移动前验证源/目标均位于本任务目录范围，移动后回读散列一致，原位置已不存在。`trash` 按现有 `.gitignore` 留在本机，Git 发布清单与说明。

当前源码、验收脚本、存档、实际模型、编译产物及成功/失败运行日志保留；失败日志是复查证据。尤其保留 `20260911004706-1280.log` 的快捷栏间歇中断记录与后续诊断，不因之后复测通过而作废。并行开发的未提交源码和素材保持其原工作区状态。

## 技能更新

- [UE5 UI](../../skills/ue5-ui-umg-slate/SKILL.md)：新增 FPSGAME 背包输入参考，说明独立 viewport 弹窗的事件路径、统一外部关闭、TAB 焦点、拖放取消及真实输入/库存联合验证。
- [世界交互](../../skills/ue5-world-interaction/SKILL.md)：新增物理掉落参考，说明预览世界销毁导致 GC、按完整改造组合缓存与预热、预览角色隔离、重力/事务/读档、对准 E 与仓库保活，以及摄像机更新后的拾取审计。
- [C++ 玩法](../../skills/ue5-cpp-gameplay/SKILL.md)：补充 Unity 编译中的全局命名空间污染、反射参数重名与物理质量 setter 的排错经验。

对应个人技能位于 `C:/Users/allan/.codex/skills/`；三个入口及两份新增参考与仓库镜像逐字节一致。六个技能目录均通过 `skill-creator/scripts/quick_validate.py`，两端相对链接已核验。未将历史性能数字或未定位的偶发故障写成当前保证。

本轮为归档与技能文档更新；检查散列、镜像、技能格式、链接和提交差异，未重跑玩法验收。此前实测结果仍以[复查记录](drop-hitch-and-backpack-close-20260911.md)所列日期与日志为准。
