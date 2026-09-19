# 当前开发方向

用户于 2026-09-10 明确：后续 3D FPS 开发转向 UE5。本目录 `FPSGAME.uproject` 是当前工程（UE 5.8.2）；Godot 原型仅作迁移参考或按明确要求维护。

- 天气、雨效、云层、太阳及昼夜工作先读 `C:/Users/allan/.codex/skills/ue5-weather-workflow/SKILL.md`；诊断读相邻 `ue5-debug-validation/SKILL.md`。
- 使用实际 UE 运行证据验证，保留动画、UI、存档及并行修改；不把编译或空的编辑器 actor 列表当成完整运行验收。
- 本地工程尚不是独立 Git 仓库。对应远端为 `https://github.com/allang2208/3D-FPS.git`，已有仓库位于 `E:/3d/3-dfps`，按其 `WORKFLOW.md` 第 8 节在必要时隔离发布；不要合并不相关历史或覆盖他人暂存区。
- 本次任务确认淘汰的文件移到 `trash/<task>/`，记录原路径、去向、大小与 SHA-256。保留必要源文件、许可证、最终预览和可复现验证。不要按旧版本文件名批量判废。
- 发布代码/证据时列清本地宿主工程与资产依赖；缓存、构建产物、trash、未获再分发许可的 Fab 资源不入源码快照。普通非强推，推送后回读远端 SHA。
