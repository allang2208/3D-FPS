# 普通僵尸制作源与预览

本目录是 2026-09-06 获准接入的僵尸样板可复现文件集。标准流程见 ../../../../skills/godot-monster-workflow/SKILL.md；案例来源和参数见该技能 references/zombie-case.md，游戏接入见 ../../../../docs/ordinary-zombie-integration.md。

- zombie-apose-reference.png / reference-prompt.txt：从原二维 idle 补正面 A 姿。
- zombie-raw.glb：生成网格；zombie-rigged.blend：可编辑蒙皮与四段动作；zombie-preview.glb：正式导出源。
- idle-preview.gif、walk-preview.gif、attack-preview.gif、death-preview.gif：实际模型离线渲染。Attack/Death 的 GIF 循环仅供展示。
- inspect_mesh.py、rig_and_animate.py、package_preview.py、check_export.py：网格检查、绑定和关键帧生成、打包及导出重导检查。
- migration-contract.json、export-report.json、rig-report.json、roundtrip-*-report.json：阶段与验证记录。

在此目录用 Blender 后台执行 rig_and_animate.py，再用支持 Pillow 的 Python 执行 package_preview.py；用 Blender 执行 check_export.py，附 -- --walk 或 -- --death 查看相应动作。脚本使用当前目录的 raw GLB，不需再次请求生成服务。工具版本为 Blender 5.1；安装位置按当前机器配置。

源角色来自 game-dev 普通僵尸 v2；生成方法为 image_gen A 姿准备 + 用户自有 TRELLIS.2 网格 + 编写骨骼关键帧。手指未逐指绑骨、头面为样板精度，背面为三维补全。本目录以 .gdignore 隔离编辑源，运行时使用 assets/models/ordinary_zombie/zombie_v01.glb。

完整本地制作档案位于 E:/无尽轮回/3d/3-dfps/tools/ai-gen/zombie-3d-v01-20260905，含旧版对照、渲染图与服务执行记录；本目录未发布服务日志。自动行为测试通过 22 项，主场景验证了追击与落地；未完成全程人工战斗试玩。
