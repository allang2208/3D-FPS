# 手模与握持修复归档（2026-09-09）

本包保存当前本地 Godot 六枪手模优化的自有代码、修复补丁、生成器、测试和渲染证据。**这是隔离归档，不是远端完整枪械运行接入**；`.gdignore` 阻止缺少外部模型时自动导入这些脚本。本地游戏仍使用原 `scripts/` 与正式手模。

## 内容与复现

- `runtime/`：当前手模适配、握把/弹鼓 IK、ADS 收指、动画开始/取消状态及 M16 活动挂点实现。保留原 `res://scripts/` 依赖，供完整枪械工作区按补丁审查后使用，不要直接作为归档目录内可运行场景加载。
- `evidence/interruption-scoped-changes.diff`：动作所有权与挂点修复，Gun 仅含本任务片段，未收录其他任务的性能改动。
- `evidence/ads-finger-integration.diff`：收指层接入。
- `tests/`：本地完整工作区的专项回归。脚本中的输出目录来自当时的 Windows 环境；复现时改为自己的隔离输出目录，并提供各 `res://scenes/weapons/`、WeaponData、HUD、配件与音频依赖。
- `reproduction/`：合法取得手模、纹理与各枪源资产后，先 bake_source → export_hand_rigs → fit_hands_v6（按 HANDS_WEAPON 六次）→ assemble_hands_v3 → export_editable_hands → save_editable_all。检查每步输入、路径及当前工具依赖；v3 输出名称是历史命名，不是已淘汰输入。
- `previews/`：实际模型渲染。近景上排调整前、下排调整后；第一人称总览为各枪原装和侧斜握把+弹鼓。

## 本地验证与边界

2026-09-08：255 个持枪/ADS、326 个松手、240 个握把换弹用例和 18,000 次组合操作零失败；六枪实际 Gun 渲染和准星检查完成。先前的 115,920 个动作打断和 22,113 个 HUD 切换是前一阶段结果，不冒充收指改动后重跑。报告内绝对路径是本地证据位置，不是公开包依赖已齐全的保证。

发布前按 WORKFLOW 检查工作区导入、冒烟、combat/reload 和当前手部专项测试；执行结果记录于 `PUBLICATION.md`。不把远端未提供的授权模型伪装为可复现资源。

## 许可与未包含文件

免费手模为 NadevayNoski 的 CGTrader Royalty Free License (no AI)，不是 CC0。依据[CGTrader 许可说明](https://help.cgtrader.com/hc/en-us/articles/360015124437-Royalty-Free-License)，本包不发布可提取的原模型、改版 `.res`、GLB/Blender、烘焙贴图和下载压缩包。它们保留于原工作区，详见 CREDITS.md。用户若另有独立再分发许可，再按其许可范围发布；本次授权推送不改变第三方许可。

清理将 55 个顶层条目、190 个废案文件约 240.98 MiB 移到本地 `E:/3d/3-dfps/trash/free-hands-retired-20260909`；清单在 evidence。未删除，未移动当前 v6 源、六个 hands-*-v3.glb、prepared-v3、editable-v6、正式资源或其他任务文件。
